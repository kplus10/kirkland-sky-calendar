from ics import Calendar, Event
from datetime import datetime
import pytz
from pathlib import Path

TZ = pytz.timezone("America/Los_Angeles")

cal = Calendar()

events = [
    {
        "title": "Perseid Meteor Shower Peak",
        "date": datetime(2026, 8, 12, 23, 0),
        "description": "Best viewing after midnight from Kirkland."
    },
    {
        "title": "Geminid Meteor Shower Peak",
        "date": datetime(2026, 12, 13, 20, 0),
        "description": "One of the strongest annual meteor showers."
    },
    {
        "title": "Strawberry Moon",
        "date": datetime(2026, 6, 30, 20, 0),
        "description": "Traditional June full moon."
    },
]

for item in events:
    event = Event()
    event.name = item["title"]
    event.begin = TZ.localize(item["date"])
    event.description = item["description"]
    event.location = "Kirkland, WA"
    cal.events.add(event)

Path("docs").mkdir(exist_ok=True)

with open("docs/sky-events.ics", "w") as f:
    f.writelines(cal)