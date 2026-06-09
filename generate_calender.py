from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import uuid

TIMEZONE = "America/Los_Angeles"

events = [
    {
        "title": "Perseid Meteor Shower Peak 🌠",
        "start": datetime(2026, 8, 12, 23, 0, tzinfo=ZoneInfo(TIMEZONE)),
        "end": datetime(2026, 8, 13, 6, 0, tzinfo=ZoneInfo(TIMEZONE)),
        "description": "Best viewing after midnight from Kirkland WA.",
    },
    {
        "title": "Geminid Meteor Shower Peak 🌠🔥",
        "start": datetime(2026, 12, 13, 20, 0, tzinfo=ZoneInfo(TIMEZONE)),
        "end": datetime(2026, 12, 14, 8, 0, tzinfo=ZoneInfo(TIMEZONE)),
        "description": "One of the strongest annual meteor showers.",
    },
    {
        "title": "Strawberry Moon 🌕",
        "start": datetime(2026, 6, 30, 20, 0, tzinfo=ZoneInfo(TIMEZONE)),
        "end": datetime(2026, 6, 30, 22, 0, tzinfo=ZoneInfo(TIMEZONE)),
        "description": "Traditional June full moon.",
    },
]

def format_utc(dt):
    return dt.astimezone(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")


def escape(text):
    return (
        text.replace("\\", "\\\\")
            .replace(",", "\\,")
            .replace(";", "\\;")
            .replace("\n", "\\n")
    )
lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Kirkland Sky Calendar//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
]

generated = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

for e in events:

    uid = str(uuid.uuid4()) + "@kirklandsky"

    lines.extend([
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{generated}",
        f"DTSTART:{format_utc(e['start'])}",
        f"DTEND:{format_utc(e['end'])}",
        f"SUMMARY:{escape(e['title'])}",
        f"DESCRIPTION:{escape(e['description'])}",
        "LOCATION:Kirkland\\, WA",
        "STATUS:CONFIRMED",
        "END:VEVENT",
    ])

lines.append("END:VCALENDAR")

Path("docs").mkdir(exist_ok=True)

with open("docs/sky-events.ics", "w", encoding="utf-8", newline="\r\n") as f:
    f.write("\r\n".join(lines))