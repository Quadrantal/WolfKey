import datetime
import gspread
from django.conf import settings
from oauth2client.service_account import ServiceAccountCredentials
from forum.models import UserProfile, DailySchedule
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import httpx

# Initialize Google Sheets client
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(settings.GSHEET_CREDENTIALS, scope)
client = gspread.authorize(creds)

# Open the spreadsheet
sheet = client.open("Copy of 2024-2025 SS Block Order Calendar").sheet1

DEFAULT_BLOCK_TIMES = [
    "8:20-9:30",
    "9:35-10:45",
    "11:05-12:15",
    "13:05-14:15",
    "14:20-15:30"
]

def get_google_calendar_service():
    """
    Initialize the Google Calendar API service.
    """
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        settings.GSHEET_CREDENTIALS, 
        scopes=['https://www.googleapis.com/auth/calendar.readonly']
    )
    return build('calendar', 'v3', credentials=creds)

def get_alt_day_event(target_date):
    """
    Check Google Calendar for an "alt day" all-day event on the given date.
    :param target_date: The date to check (datetime.date object).
    :return: The event description if an "alt day" event exists, otherwise None.
    """
    try:
        service = get_google_calendar_service()
        calendar_id = 'nda09oameg390vndlulocmvt07u7c8h4@import.calendar.google.com'
        time_min = datetime.datetime.combine(target_date, datetime.time.min).isoformat() + 'Z'
        time_max = datetime.datetime.combine(target_date, datetime.time.max).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        for event in events_result.get('items', []):
            if event.get('summary', '').lower().startswith("alt day") and event.get('start', {}).get('date'):
                return event.get('description', None)
    except HttpError as error:
        print(f"An error occurred: {error}")
    return None

def extract_block_times_from_description(description):
    """
    Extract block times from the event description.
    :param description: The description of the "alt day" event.
    :return: A list of block times.
    """
    block_times = []
    lines = description.splitlines()
    for line in lines:
        if "-" in line and ":" in line:
            block_times.append(line.split("-")[0].strip())
    return block_times
def get_block_order_for_day(target_date):
    """
    Retrieve the block order for a specific date, using the saved DailySchedule if it exists.
    Date format must match sheet, e.g., "Tue, Sep 3".
    """
    # Convert target_date to a date object
    date_obj = datetime.datetime.strptime(target_date, "%a, %b %d").date()

    # Check if a DailySchedule already exists for the date
    existing_schedule = DailySchedule.objects.filter(date=date_obj).first()
    if existing_schedule:
        # Use the saved schedule
        return {
            'blocks': [
                existing_schedule.block_1,
                existing_schedule.block_2,
                existing_schedule.block_3,
                existing_schedule.block_4,
                existing_schedule.block_5,
            ],
            'times': [
                existing_schedule.block_1_time,
                existing_schedule.block_2_time,
                existing_schedule.block_3_time,
                existing_schedule.block_4_time,
                existing_schedule.block_5_time,
            ],
        }

    # If no saved schedule exists, proceed to fetch from external sources
    # Check for an "alt day" event in Google Calendar
    alt_day_description = get_alt_day_event(date_obj)

    if alt_day_description:
        # Extract block times from the alt day description
        block_times = extract_block_times_from_description(alt_day_description)
    else:
        # Use default block times
        block_times = DEFAULT_BLOCK_TIMES

    # Fetch the raw block order from Google Sheets
    date_column = sheet.col_values(4)[6:]  # Column D, starting from row 7
    rows = sheet.get_all_values()[6:]      # Skip header rows

    for i, date_str in enumerate(date_column):
        if date_str.strip() == target_date.strip():
            # Save the schedule to the database
            schedule, created = DailySchedule.objects.get_or_create(
                date=date_obj,
                defaults={
                    'block_1': rows[i][4] if rows[i][4] else None,
                    'block_1_time': block_times[0] if len(block_times) > 0 else None,
                    'block_2': rows[i][5] if rows[i][5] else None,
                    'block_2_time': block_times[1] if len(block_times) > 1 else None,
                    'block_3': rows[i][6] if rows[i][6] else None,
                    'block_3_time': block_times[2] if len(block_times) > 2 else None,
                    'block_4': rows[i][7] if rows[i][7] else None,
                    'block_4_time': block_times[3] if len(block_times) > 3 else None,
                    'block_5': rows[i][8] if rows[i][8] else None,
                    'block_5_time': block_times[4] if len(block_times) > 4 else None,
                }
            )
            return {
                'blocks': [schedule.block_1, schedule.block_2, schedule.block_3, schedule.block_4, schedule.block_5],
                'times': block_times,
            }

    return {
        'blocks': [None, None, None, None, None],
        'times': block_times,
    }

def interpret_block(block_code):
    if block_code in ("", None):
        return None
    code = block_code.strip().lower()
    if code == "assm":
        return "Assembly"
    if code == "tfr":
        return "Terry Fox Run"
    if code == "1ca":
        return "Academics"
    if code == "1cp":
        return "PEAKS"
    if code == "1cap":
        return "Advisory"
    return block_code

def process_schedule_for_user(user, raw_schedule):
    """
    Process the block order for a user and substitute blocks with their courses.
    :param user: User object
    :param raw_schedule: Dictionary containing 'blocks' and 'times'
    :return: List of processed blocks with times
    """
    profile = UserProfile.objects.get(user=user)
    processed_schedule = []

    block_mapping = {
        "1ca": "Academics",
        "1cp": "PEAKS",
        "1cap": "Advisory",
        "assm": "Assembly",
        "tfr": "Terry Fox Run"
    }

    if not any(raw_schedule['blocks']):
        return ["no school"]

    for block, time in zip(raw_schedule['blocks'], raw_schedule['times']):
        if not block:
            processed_schedule.append({"block": "No Block", "time": time})
        else:
            normalized = block.strip().lower()
            if normalized in block_mapping:
                processed_schedule.append({"block": block_mapping[normalized], "time": time})
            else:
                # Try fetching course based on block naming convention
                block_attr = f"block_{normalized.upper()}"
                course = getattr(profile, block_attr, None)
                processed_schedule.append({"block": course.name if course else f"{block}, Add your courses in profile to unlock this!", "time": time})

    return processed_schedule