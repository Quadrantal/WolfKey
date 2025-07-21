from django.core.management.base import BaseCommand
from forum.tasks import check_all_user_grades_sequential, check_single_user_grades

class Command(BaseCommand):
    help = 'Manually trigger grade checking for users'

    def add_arguments(self, parser):
        parser.add_argument('--user-email', type=str, help='Check grades for a specific user by email')

    def handle(self, *args, **options):
        user_email = options.get('user_email')

        if user_email:
            self.stdout.write(f'Checking grades for {user_email}...')
            task = check_single_user_grades.delay(user_email)
            self.stdout.write(self.style.SUCCESS(f'Task scheduled with ID: {task.id}'))
        else:
            self.stdout.write('Checking grades for all users sequentially...')
            result = check_all_user_grades_sequential()
            self.stdout.write(self.style.SUCCESS(f"Scheduled {result['scheduled_tasks']} grade checking tasks."))
