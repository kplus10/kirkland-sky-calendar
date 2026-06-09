from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import uuid

from skyfield.api import load, wgs84
from skyfield import almanac

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

START_YEAR = 2026
END_YEAR = 2028

TIMEZONE = ZoneInfo("America/Los_Angeles")

KIRKLAND = {
    "lat": 47.722817,
    "lon": -122.213383,
}

SUPERMOON_DISTANCE_KM = 360000
CONJUNCTION_THRESHOLD_DEG = 2.0

# -------------------------------------------------
# SKYFIELD SETUP
# -------------------------------------------------

print("Loading ephemeris...")

ts = load.timescale()
eph = load("de440s.bsp")

earth = eph["earth"]
moon = eph["moon"]
venus = eph["venus"]
jupiter = eph["jupiter barycenter"]

observer_location = wgs84.latlon(
    KIRKLAND["lat"],
    KIRKLAND["lon"]
)

observer = earth + observer_location

# -------------------------------------------------
# ICS HELPERS
# -------------------------------------------------

events = []


def add_event(title, start_dt, description):
    events.append({
        "title": title,
        "start": start_dt,
        "description": description,
    })


def format_utc(dt):
    return dt.astimezone(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def escape(text):
    return (
        text.replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace(";", "\\;")
        .replace("\n", "\\n")
    )


# -------------------------------------------------
# FULL MOONS
# -------------------------------------------------

FULL_MOON_NAMES = {
    1: "Wolf Moon",
    2: "Snow Moon",
    3: "Worm Moon",
    4: "Pink Moon",
    5: "Flower Moon",
    6: "Strawberry Moon",
    7: "Buck Moon",
    8: "Sturgeon Moon",
    9: "Corn Moon",
    10: "Hunter's Moon",
    11: "Beaver Moon",
    12: "Cold Moon",
}

print("Calculating moon phases...")

start = ts.utc(START_YEAR, 1, 1)
end = ts.utc(END_YEAR, 1, 1)

phase_function = almanac.moon_phases(eph)

times, phases = almanac.find_discrete(
    start,
    end,
    phase_function
)

full_moons = []

for t, phase in zip(times, phases):

    if phase != 2:
        continue

    dt = t.utc_datetime().replace(
        tzinfo=timezone.utc
    )

    full_moons.append((t, dt))

# -------------------------------------------------
# HARVEST MOON
# -------------------------------------------------

for year in range(START_YEAR, END_YEAR):

    autumn_equinox = datetime(
        year,
        9,
        22,
        tzinfo=timezone.utc
    )

    candidates = [
        x for x in full_moons
        if x[1].year == year
    ]

    harvest = min(
        candidates,
        key=lambda x:
        abs((x[1] - autumn_equinox).total_seconds())
    )

    harvest_time = harvest[1]

    add_event(
        "Harvest Moon 🌕",
        harvest_time,
        "Full moon closest to the autumn equinox."
    )

# -------------------------------------------------
# NAMED FULL MOONS + SUPERMOONS
# -------------------------------------------------

print("Generating moon events...")

for t, dt in full_moons:

    local_dt = dt.astimezone(TIMEZONE)

    moon_name = FULL_MOON_NAMES.get(
        local_dt.month,
        "Full Moon"
    )

    add_event(
        moon_name,
        dt,
        f"{moon_name} visible from Kirkland."
    )

    distance_km = (
        earth.at(t)
        .observe(moon)
        .distance()
        .km
    )

    if distance_km < SUPERMOON_DISTANCE_KM:

        add_event(
            f"Supermoon 🌕 ({moon_name})",
            dt,
            f"Moon distance: {distance_km:,.0f} km"
        )

# -------------------------------------------------
# VENUS + JUPITER CONJUNCTIONS
# -------------------------------------------------

print("Searching conjunctions...")

current = datetime(
    START_YEAR,
    1,
    1,
    tzinfo=timezone.utc
)

end_dt = datetime(
    END_YEAR,
    1,
    1,
    tzinfo=timezone.utc
)

previous_hit = None

while current < end_dt:

    t = ts.from_datetime(current)

    venus_ast = earth.at(t).observe(venus)
    jupiter_ast = earth.at(t).observe(jupiter)

    separation = (
        venus_ast.separation_from(
            jupiter_ast
        ).degrees
    )

    if separation < CONJUNCTION_THRESHOLD_DEG:

        venus_alt = (
            observer.at(t)
            .observe(venus)
            .apparent()
            .altaz()[0]
            .degrees
        )

        jupiter_alt = (
            observer.at(t)
            .observe(jupiter)
            .apparent()
            .altaz()[0]
            .degrees
        )

        visible = (
            venus_alt > 10 and
            jupiter_alt > 10
        )

        if visible:

            if (
                previous_hit is None
                or
                (current - previous_hit)
                > timedelta(days=10)
            ):

                add_event(
                    "Venus–Jupiter Conjunction 🪐",
                    current,
                    f"Separation ≈ {separation:.2f}°. "
                    f"Visible from Kirkland."
                )

                previous_hit = current

    current += timedelta(hours=6)

# -------------------------------------------------
# WRITE ICS
# -------------------------------------------------

print("Writing ICS...")

lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Kirkland Sky Calendar//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
]

dtstamp = datetime.utcnow().strftime(
    "%Y%m%dT%H%M%SZ"
)

for event in sorted(
    events,
    key=lambda e: e["start"]
):

    uid = (
        str(uuid.uuid4())
        + "@kirklandsky"
    )

    start = event["start"]

    end = start + timedelta(hours=1)

    lines.extend([
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{format_utc(start)}",
        f"DTEND:{format_utc(end)}",
        f"SUMMARY:{escape(event['title'])}",
        f"DESCRIPTION:{escape(event['description'])}",
        "LOCATION:Kirkland\\, WA",
        "STATUS:CONFIRMED",
        "END:VEVENT",
    ])

lines.append("END:VCALENDAR")

Path("docs").mkdir(exist_ok=True)

with open(
    "docs/sky-events.ics",
    "w",
    encoding="utf-8",
    newline="\r\n"
) as f:
    f.write("\r\n".join(lines))

print(
    f"Created docs/sky-events.ics "
    f"with {len(events)} events"
)