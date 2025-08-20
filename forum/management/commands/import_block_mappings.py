from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from forum.models import Course, Block
from forum.services.course_services import course_search
import json
import re
import os
from django.conf import settings
from django.contrib.staticfiles import finders


class Command(BaseCommand):
    help = (
        'Import Course -> Block relationships from a plaintext file. '
        'Each non-empty line should be: "Course Name: 1B,1C, ..."'
    )

    def add_arguments(self, parser):
        parser.add_argument('filepath', nargs='?', default=None, help='Path to the plaintext file to import (optional)')
        parser.add_argument('--dry-run', action='store_true', help='Parse and report actions but do not modify the DB')
        parser.add_argument('--create-blocks', action='store_true', help='Create Block records if missing')
        parser.add_argument('--force', action='store_true', help='Apply mappings even if multiple course matches exist (uses first match)')

    def handle(self, *args, **options):
        path = options['filepath']

        # If no filepath provided, try to find the default file in staticfiles
        if not path:
            found = finders.find('forum/Untitled.txt')
            if found:
                path = found
            else:
                # Fallback to repository-relative path using BASE_DIR
                path = os.path.join(settings.BASE_DIR, 'forum', 'static', 'forum', 'Untitled.txt')
        dry_run = options['dry_run']
        create_blocks = options['create_blocks']
        force = options['force']

        try:
            with open(path, 'r', encoding='utf-8') as f:
                raw_lines = f.readlines()
        except OSError as e:
            raise CommandError(f'Could not open file: {e}')

        # Basic RTF-stripping: remove braces and backslash control words if present.
        # Prefer to provide a plaintext file, but this helps when the input is a quick RTF dump.
        def sanitize_line(line: str) -> str:
            # Remove common RTF characters and excessive whitespace
            line = re.sub(r'[{}\\].*?\b', '', line)
            return line.strip()

        mappings = []  # list of tuples (course_name, [block_codes])

        for raw in raw_lines:
            line = raw.strip()
            if not line:
                continue
            # Try naive RTF cleanup if the file contains RTF header
            if line.startswith('{\\rtf') or line.startswith('{'):
                # fallback: skip rtf metadata lines
                # but allow content lines further down
                if line.lower().startswith('{\\rtf'):
                    continue
            # If the line contains braces or backslashes it's likely still RTF; do a sanitize
            if '{' in line or '\\' in line:
                line = sanitize_line(line)
                if not line:
                    continue

            # Expect format: Course Name: B1, B2, B3
            if ':' not in line:
                # If no colon, try splitting on tab or multiple spaces
                parts = re.split(r'\t+|\s{2,}', line, maxsplit=1)
            else:
                parts = line.split(':', 1)

            if len(parts) < 2:
                self.stdout.write(self.style.WARNING(f"Skipping unrecognized line: {line}"))
                continue

            course_name = parts[0].strip()
            block_part = parts[1].strip()

            # split block codes by comma, semicolon or whitespace
            raw_tokens = re.split(r'[;,]|\s+', block_part)

            # Normalize tokens: uppercase, strip surrounding non-alphanumerics
            # and remove trailing backslashes or other stray chars produced by RTF
            norm_tokens = []
            for tok in raw_tokens:
                t = tok.strip().upper()
                if not t:
                    continue
                # remove non-alphanumeric characters from start/end
                t = re.sub(r'^[^A-Z0-9]+|[^A-Z0-9]+$', '', t)
                if t:
                    norm_tokens.append(t)

            # Keep only tokens that look like canonical block codes (e.g., 1A, 2D)
            block_codes = [b for b in norm_tokens if re.match(r'^[0-9][A-Z]$', b)]

            if not block_codes:
                self.stdout.write(self.style.WARNING(f'No block codes found for "{course_name}" — skipping'))
                continue

            mappings.append((course_name, block_codes))

        if not mappings:
            raise CommandError('No valid mappings parsed from file')

        report = []
        created_blocks = set()
        applied_count = 0
        skipped_count = 0

        if dry_run:
            self.stdout.write(self.style.NOTICE('Dry run: no DB changes will be made'))

        # Remove existing course<->block mappings before applying new ones.
        # Use the through table for an efficient bulk delete.
        through_model = Course.blocks.through
        existing_rel_count = through_model.objects.count()
        if existing_rel_count:
            if dry_run:
                self.stdout.write(self.style.WARNING(
                    f'Dry run: would remove {existing_rel_count} existing course<->block mappings'
                ))
            else:
                try:
                    with transaction.atomic():
                        through_model.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS(
                        f'Removed {existing_rel_count} existing course<->block mappings'
                    ))
                except Exception as e:
                    raise CommandError(f'Failed to clear existing mappings: {e}')

        for course_name, block_codes in mappings:
            # 1) Try exact match first (case-insensitive)
            matches = list(Course.objects.filter(name__iexact=course_name))

            # 2) If no exact match, try the service search (trigram/prefix) which
            #    may return close matches for human-entered names. We call
            #    course_search with a mock request object exposing GET['q'].
            if not matches:

                mock_request = type('MockRequest', (), {'GET': {'q': course_name}})()
                try:
                    response = course_search(mock_request)
                    # course_search returns a JsonResponse with a JSON list
                    data = json.loads(response.content)
                    # data is a list of dicts with 'id' and 'name' keys
                    if data:
                        # take up to 3 suggestions from search as potential matches
                        suggested_ids = [d['id'] for d in data[:3]]
                        matches = list(Course.objects.filter(id__in=suggested_ids))
                except Exception as e:
                    print(e)
                    matches = []

            # 3) Fallback to icontains if still no matches
            if not matches:
                matches = list(Course.objects.filter(name__icontains=course_name))

            if not matches:
                report.append((course_name, block_codes, 'COURSE_NOT_FOUND'))
                skipped_count += 1
                continue

            if len(matches) > 1 and not force:
                report.append((course_name, block_codes, f'MULTIPLE_COURSES ({len(matches)})'))
                skipped_count += 1
                continue

            course_obj = matches[0]

            # Ensure blocks exist
            block_objs = []
            for code in block_codes:
                block_obj = Block.objects.filter(code__iexact=code).first()
                if not block_obj:
                    if create_blocks and not dry_run:
                        block_obj = Block.objects.create(code=code)
                        created_blocks.add(code)
                    else:
                        report.append((course_name, block_codes, f'BLOCK_NOT_FOUND ({code})'))
                        block_obj = None
                if block_obj:
                    block_objs.append(block_obj)

            if not block_objs:
                skipped_count += 1
                continue

            if dry_run:
                report.append((course_name, [b.code for b in block_objs], 'WILL_ADD (dry-run)'))
            else:
                try:
                    with transaction.atomic():
                        for b in block_objs:
                            course_obj.blocks.add(b)
                    report.append((course_name, [b.code for b in block_objs], 'ADDED'))
                    applied_count += 1
                except Exception as e:
                    report.append((course_name, block_codes, f'ERROR: {e}'))
                    skipped_count += 1

        # Summary
        self.stdout.write('\nImport summary:')
        for item in report:
            name, blocks, status = item
            self.stdout.write(f' - {name!r} -> {blocks} : {status}')

        self.stdout.write('\nTotals:')
        self.stdout.write(f' Applied: {applied_count}')
        self.stdout.write(f' Skipped: {skipped_count}')
        if created_blocks:
            self.stdout.write(f' Created blocks: {sorted(created_blocks)}')

        if dry_run:
            self.stdout.write(self.style.NOTICE('Dry run completed — no changes were made. Rerun without --dry-run to apply.'))
