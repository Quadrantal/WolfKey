import random
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+

GREETINGS = [
    "Welcome back, {name}!",
    "Hello there.",
    "{timed_greeting}",
    "{name} returns!",
    "Good to see you again, {name}!",
    "Hello, {name}! Ready to explore?",
    "Hey there, {name}! Let's dive in!",
    "Greetings, {name}! Let's get started!",
    "{name}, our servers missed you.",
    "Ah, welcome {name}!",
]

def get_timed_greeting(user_timezone="UTC"):
    """Returns a contextual greeting based on the user's timezone."""
    try:
        now = datetime.now(ZoneInfo(user_timezone))
    except Exception:
        now = datetime.now(datetime.timezone.utc)  # fallback to UTC if timezone is invalid
    hour = now.hour
    if hour < 12:
        return "Good morning, and in case I don't see ya: good afternoon, good evening, and good night!"
    elif hour < 17:
        return "Good afternoon, and in case I don't see ya: good evening, and good night!"
    elif hour < 21:
        return "Good evening, and in case I don't see ya: good night!"
    else:
        return "Good night!"

def get_random_greeting(name, user_timezone="UTC"):
    """Returns a random greeting with the user's name and dynamic time-sensitive phrasing."""
    greeting = random.choice(GREETINGS)
    return greeting.format(name=name, timed_greeting=get_timed_greeting(user_timezone))
