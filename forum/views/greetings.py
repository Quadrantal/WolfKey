import random

GREETINGS = [
    "Welcome back, {name}!",
    "Hello there.",
    "Good morning, and in case I don’t see ya: good afternoon, good evening, and good night!",
    "{name} returns!",
    "Good to see you again, {name}!",
    "Hello, {name}! Ready to explore?",
    "Hey there, {name}! Let's dive in!",
    "Greetings, {name}! Let's get started!",
    "{name}, our servers missed you.",
    "Ah, welcome {name}!",

]

def get_random_greeting(name):
    """Returns a random greeting with the user's name."""
    return random.choice(GREETINGS).format(name=name)