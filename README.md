# 🌌 Kirkland Sky Calendar

[![Update Astronomy Calendar](https://github.com/kplus10/kirkland-sky-calendar/actions/workflows/update-calendar.yml/badge.svg)](https://github.com/kplus10/kirkland-sky-calendar/actions/workflows/update-calendar.yml)

A location-aware astronomy calendar for **Kirkland, Washington**, generated with Python and [Skyfield](https://rhodesmill.org/skyfield/).

The project calculates astronomical events and publishes them as an `.ics` calendar feed that can be subscribed to from **Google Calendar, Apple Calendar, Outlook**, and other calendar applications.

The goal is to provide a practical calendar of interesting sky events rather than every possible astronomical event.

## 📅 Subscribe to the calendar

The generated calendar is published from the repository's `docs` directory through GitHub Pages.

Calendar feed:

```text
https://kplus10.github.io/kirkland-sky-calendar/sky-events.ics
```

### Google Calendar

On the desktop version of Google Calendar:

1. Open Google Calendar.
2. Find **Other calendars** in the left sidebar.
3. Click **+**.
4. Select **From URL**.
5. Paste:

```text
https://kplus10.github.io/kirkland-sky-calendar/sky-events.ics
```

6. Click **Add calendar**.

This is a subscription rather than a one-time import. When the `.ics` file changes, Google Calendar periodically refreshes the feed.

Google controls the refresh interval, so updates may not appear immediately.

---

# 🔭 Currently generated events

The primary generator is:

```text
generate_skyfield_calendar.py
```

It currently calculates events for **2026–2027**.

## 🌕 Named full moons

Full-moon times are calculated using Skyfield rather than entered manually.

The calendar assigns the traditional North American full-moon name according to the month in Kirkland:

| Month | Name |
|---|---|
| January | Wolf Moon |
| February | Snow Moon |
| March | Worm Moon |
| April | Pink Moon |
| May | Flower Moon |
| June | Strawberry Moon |
| July | Buck Moon |
| August | Sturgeon Moon |
| September | Corn Moon |
| October | Hunter's Moon |
| November | Beaver Moon |
| December | Cold Moon |

For example, the June full moon appears in the calendar as:

```text
Strawberry Moon
```

The astronomical instant of the full moon is calculated from the JPL ephemeris.

---

## 🌾 Harvest Moon

The project identifies a **Harvest Moon** as the full moon closest to the Northern Hemisphere autumn equinox.

Currently the code approximates the autumn equinox as:

```text
September 22
```

and selects the nearest calculated full moon.

The Harvest Moon may therefore also appear as its normal monthly named moon.

Future versions should calculate the actual equinox time with Skyfield instead of assuming September 22.

---

## 🌕 Supermoons

A full moon is currently classified as a supermoon when its calculated Earth–Moon distance is:

```text
< 360,000 km
```

When this happens, an additional event is generated such as:

```text
Supermoon 🌕 (Beaver Moon)
```

The description includes the calculated Moon distance.

### Important note

There is no single universally accepted astronomical definition of "supermoon."

The current `360,000 km` threshold is a simple practical definition and may differ from lists published by other astronomy organizations.

A future version may instead compare the full moon with lunar perigee and use a configurable percentage-of-perigee definition.

---

# 🪐 Venus–Jupiter conjunctions

The generator searches for close apparent encounters between **Venus and Jupiter**.

A conjunction candidate currently requires an angular separation of:

```text
< 2°
```

The search samples the planets every:

```text
6 hours
```

For each candidate, the program calculates the apparent altitude of Venus and Jupiter from Kirkland.

Both planets must currently be:

```text
> 10° above the horizon
```

for the event to be added.

A generated event looks similar to:

```text
Venus–Jupiter Conjunction 🪐
```

with a description such as:

```text
Separation ≈ 1.25°. Visible from Kirkland.
```

## Current visibility limitation

The present visibility check only verifies that both planets are above 10° altitude.

It does **not yet verify that the Sun is sufficiently below the horizon**.

That means a conjunction can technically pass the current filter while occurring during daylight.

Future versions should require appropriate twilight conditions, for example:

```text
Sun altitude < -6°
```

for civil twilight, or a stricter limit for dark-sky observations.

---

# 📍 Location

The calendar is configured for the Kirkland, Washington area:

```python
KIRKLAND = {
    "lat": 47.722817,
    "lon": -122.213383,
}
```

Timezone:

```text
America/Los_Angeles
```

Skyfield performs astronomical calculations in UTC internally. Calendar events are written with UTC timestamps, which calendar applications automatically display in the viewer's local timezone.

---

# 🛰 Astronomical data

The project uses the JPL:

```text
DE440s
```

planetary ephemeris.

The repository currently contains:

```text
de440s.bsp
```

This allows the GitHub Actions runner to perform the calculations without needing to download the ephemeris every time the workflow runs.

The ephemeris provides accurate positions for the Moon, planets, Earth, and other Solar System bodies over the supported time range.

Astronomical calculations are performed using:

[Skyfield](https://rhodesmill.org/skyfield/)

---

# 📂 Repository structure

```text
kirkland-sky-calendar/
│
├── .github/
│   └── workflows/
│       └── update-calendar.yml
│
├── docs/
│   └── sky-events.ics
│
├── de440s.bsp
│
├── generate_calendar.py
├── generate_skyfield_calendar.py
├── requirements.txt
└── README.md
```

### `generate_skyfield_calendar.py`

The primary calendar generator.

It currently calculates:

- named full moons
- Harvest Moons
- supermoons
- Venus–Jupiter conjunction candidates
- Kirkland-specific planet altitude

It then creates:

```text
docs/sky-events.ics
```

### `generate_calendar.py`

An earlier/simple generator containing manually specified events.

It is retained as a reference but is **not currently used by the GitHub Actions workflow**.

### `de440s.bsp`

JPL DE440s planetary ephemeris used by Skyfield.

### `docs/sky-events.ics`

The generated iCalendar feed.

This is the file served by GitHub Pages and subscribed to by calendar applications.

### `.github/workflows/update-calendar.yml`

GitHub Actions automation that installs the Python dependencies, runs the Skyfield generator, and commits an updated calendar when necessary.

---

# 🐍 Running locally

## Requirements

Python 3.12 is used by the GitHub Actions workflow.

Install the dependencies with:

```bash
pip install -r requirements.txt
```

Current dependencies include:

```text
skyfield
skyfield-data
numpy
pytz
```

Python's built-in `zoneinfo` module handles the Pacific timezone.

---

## Virtual environment

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

# ▶️ Generate the calendar manually

Run:

```bash
python generate_skyfield_calendar.py
```

Typical output should resemble:

```text
Loading ephemeris...
Calculating moon phases...
Generating moon events...
Searching conjunctions...
Writing ICS...
Created docs/sky-events.ics with XX events
```

The resulting file will be:

```text
docs/sky-events.ics
```

---

# 🤖 GitHub Actions automation

The workflow is located at:

```text
.github/workflows/update-calendar.yml
```

It can run in two ways.

## Manual run

The workflow includes:

```yaml
workflow_dispatch:
```

so it can be started manually.

Go to:

```text
GitHub
→ Actions
→ Update Astronomy Calendar
→ Run workflow
```

Select the `main` branch and click **Run workflow**.

This is useful after modifying the generator because it tests the exact environment that will be used for automatic updates.

---

## Scheduled run

The workflow currently contains:

```yaml
schedule:
  - cron: '0 6 1 * *'
```

This means it runs at:

```text
06:00 UTC on the first day of every month
```

The workflow:

1. Checks out the repository.
2. Starts Python 3.12.
3. Installs dependencies from `requirements.txt`.
4. Runs:

```bash
python generate_skyfield_calendar.py
```

5. Stages:

```text
docs/sky-events.ics
```

6. Commits and pushes the generated calendar.

The workflow has:

```yaml
permissions:
  contents: write
```

so the GitHub Actions token can update the generated calendar.

---

# 🌐 GitHub Pages

The generated calendar is intended to be published using GitHub Pages from:

```text
main / docs
```

GitHub Pages should therefore be configured as:

```text
Settings
→ Pages
→ Deploy from a branch
→ main
→ /docs
```

The resulting feed is:

```text
https://kplus10.github.io/kirkland-sky-calendar/sky-events.ics
```

---

# ⚙️ Configuration

Most behavior can currently be changed near the top of `generate_skyfield_calendar.py`.

## Calendar years

```python
START_YEAR = 2026
END_YEAR = 2028
```

`END_YEAR` is exclusive, so this generates events through the end of 2027.

## Supermoon distance

```python
SUPERMOON_DISTANCE_KM = 360000
```

## Conjunction threshold

```python
CONJUNCTION_THRESHOLD_DEG = 2.0
```

Reducing this value produces fewer but more visually dramatic conjunctions.

For example:

```python
CONJUNCTION_THRESHOLD_DEG = 1.0
```

would only include conjunctions closer than one degree.

---

# ⚠️ Current limitations

This project is under active development.

### Fixed calendar range

Although the workflow runs monthly, the Python generator currently has a fixed:

```python
START_YEAR = 2026
END_YEAR = 2028
```

range.

It does not yet automatically create a rolling calendar based on the current date.

A future version should dynamically generate approximately the next 24 months.

### Random calendar event IDs

Events currently use randomly generated UUIDs.

This means an event receives a different iCalendar `UID` every time the file is regenerated.

For long-term subscribed calendars, deterministic UIDs would be preferable so Google Calendar and other clients can reliably recognize an existing event when the feed is updated.

A future version should derive the UID from values such as:

```text
event type + astronomical date
```

### Conjunction timing

Venus–Jupiter separation is currently sampled every six hours.

This is sufficient to discover close encounters but does not necessarily identify the exact moment of minimum separation.

A future implementation should first find candidate intervals and then numerically minimize angular separation to determine the exact conjunction time.

### Daylight filtering

Planet altitude is checked, but solar altitude currently is not.

Therefore "`Visible from Kirkland`" should presently be interpreted as "`above the Kirkland horizon`" rather than a guarantee that the event occurs in a dark sky.

### Full Moon names

Traditional Moon names are currently assigned according to the local calendar month.

This works for the normal case but does not yet correctly distinguish unusual cases such as two full moons occurring during one calendar month.

### Blue Moons

Blue Moons are not currently detected.

### Blood Moons

Total lunar eclipses/"Blood Moons" are not currently calculated.

### Meteor showers

Meteor showers are not currently included by the Skyfield generator.

The older `generate_calendar.py` contains manually entered Perseid and Geminid examples, but the automated Skyfield generator currently does not add them.

Meteor shower peaks generally need a maintained data table or another authoritative source because Skyfield itself does not provide a meteor-shower catalog.

### Planet parades

Multi-planet viewing opportunities are not yet detected.

---

# 🚀 Planned features

The long-term goal is for this calendar to highlight astronomy events that are genuinely worthwhile from the Seattle/Kirkland area.

Planned additions include:

- 🌑 total and partial lunar eclipses
- 🩸 Blood Moons
- ☀️ solar eclipses visible from Washington
- 🌠 Perseid, Geminid, Quadrantid, Lyrid and other major meteor showers
- 🪐 conjunctions between additional bright planets
- 🪐 three-or-more-planet groupings/"planet parades"
- 🔴 Mars opposition
- 🟠 Jupiter opposition
- 🪐 Saturn opposition
- ✨ Venus greatest elongation
- 🔵 Blue Moons
- 🌕 improved supermoon/perigee calculation
- ☀️ actual equinox calculation for the Harvest Moon
- 🌅 twilight-aware visibility calculations
- 🌙 Moonlight interference ratings for meteor showers
- 🔭 recommended Kirkland viewing windows instead of only astronomical event times
- ☄️ notable bright comets when reliable orbital data is available
- 🌌 a rolling 24-month calendar rather than fixed years

---

# 🎯 Intended event filtering

The finished calendar is intended to prioritize events that are useful to a casual observer rather than fill the calendar with minor astronomical events.

Examples of high-interest events include:

```text
🩸 Total lunar eclipse / Blood Moon
🌕 Supermoon
🌠 Perseid meteor shower
🌠 Geminid meteor shower
🪐 Venus–Jupiter close conjunction
🪐 Major multi-planet grouping
☄️ Bright naked-eye comet
☀️ Solar eclipse visible from Washington
```

The goal is ultimately to answer:

> **"Is there something interesting in the sky from Kirkland tonight or soon that is worth going outside to see?"**

---

# 🔬 Accuracy

Planetary and lunar positions are calculated using Skyfield and the JPL DE440s ephemeris.

However, the classification and visibility rules used by this project—such as the definition of a supermoon, minimum planet altitude, and conjunction threshold—are project-specific choices rather than official astronomical definitions.

Weather is also not currently considered.

An event marked visible means the astronomical geometry passes the program's visibility tests. Actual viewing from Kirkland still depends on:

- cloud cover
- haze
- terrain
- buildings and trees
- local light pollution

---

# 🛠 Troubleshooting

## `can't open file generate_skyfield_calendar.py`

Confirm the filename is spelled:

```text
generate_skyfield_calendar.py
```

and that the workflow uses exactly the same spelling.

## Skyfield ephemeris errors

Confirm this file exists in the repository root:

```text
de440s.bsp
```

The generator currently loads it using:

```python
eph = load("de440s.bsp")
```

## Calendar does not update immediately

Google Calendar controls how often subscribed `.ics` feeds are refreshed.

A successful GitHub Actions run can update the published file before Google Calendar chooses to fetch the new copy.

Check the GitHub Pages `.ics` URL directly to confirm that the feed itself has updated.

## Workflow cannot push changes

Verify the workflow includes:

```yaml
permissions:
  contents: write
```

and check the repository's GitHub Actions workflow permissions if pushes are rejected.

---

# 🧭 Project status

The core pipeline is operational:

```text
Skyfield calculations
        ↓
generate_skyfield_calendar.py
        ↓
docs/sky-events.ics
        ↓
GitHub Actions
        ↓
GitHub Pages
        ↓
Google Calendar subscription
```

The next development focus is improving the astronomy calculations and visibility filtering so the feed becomes a comprehensive **Kirkland Sky Highlights Calendar** rather than simply a Moon-phase calendar.
