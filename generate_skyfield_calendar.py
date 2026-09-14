from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha1
from itertools import combinations
from math import asin, cos, degrees
from pathlib import Path
from zoneinfo import ZoneInfo

from skyfield import almanac, eclipselib
from skyfield.api import Star, load, wgs84
from skyfield.framelib import ecliptic_frame

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

TIMEZONE = ZoneInfo("America/Los_Angeles")

# Approximate Kirkland city-center coordinates. City-level coordinates are more
# than sufficient for the events this calendar targets.
KIRKLAND_LAT = 47.6769
KIRKLAND_LON = -122.2060

LOOKBACK_DAYS = 31
LOOKAHEAD_DAYS = 730

MIN_PLANET_ALT_DEG = 10.0
MAX_SUN_ALT_FOR_PLANETS_DEG = -6.0  # civil twilight or darker
CONJUNCTION_THRESHOLD_DEG = 3.0
PLANET_GROUPING_MAX_SPAN_DEG = 90.0
SUPERMOON_DISTANCE_KM = 360_000.0
SUPERMOON_MAX_PERIGEE_OFFSET_HOURS = 24.0

SUN_RADIUS_KM = 695_700.0
MOON_RADIUS_KM = 1_737.4

OUTPUT_PATH = Path("docs/sky-events.ics")
EPHEMERIS_PATH = "de440s.bsp"

# Major showers only. Peak solar longitudes and approximate radiants are based
# on standard IMO shower tables; the program solves for the peak solar
# longitude each year with Skyfield rather than hard-coding a calendar date.
METEOR_SHOWERS = [
    {"name": "Quadrantids", "code": "QUA", "solar_lon": 283.16, "month": 1, "day": 3, "zhr": 80, "ra": 230.0, "dec": 49.5},
    {"name": "Lyrids", "code": "LYR", "solar_lon": 32.32, "month": 4, "day": 22, "zhr": 18, "ra": 271.0, "dec": 34.0},
    {"name": "Eta Aquariids", "code": "ETA", "solar_lon": 45.5, "month": 5, "day": 6, "zhr": 50, "ra": 338.0, "dec": -1.0},
    {"name": "Southern Delta Aquariids", "code": "SDA", "solar_lon": 128.0, "month": 7, "day": 31, "zhr": 25, "ra": 340.0, "dec": -16.0},
    {"name": "Perseids", "code": "PER", "solar_lon": 140.0, "month": 8, "day": 13, "zhr": 100, "ra": 48.0, "dec": 58.0},
    {"name": "Orionids", "code": "ORI", "solar_lon": 208.0, "month": 10, "day": 21, "zhr": 20, "ra": 95.0, "dec": 16.0},
    {"name": "Leonids", "code": "LEO", "solar_lon": 235.27, "month": 11, "day": 17, "zhr": 15, "ra": 153.0, "dec": 22.0},
    {"name": "Geminids", "code": "GEM", "solar_lon": 262.2, "month": 12, "day": 14, "zhr": 120, "ra": 112.0, "dec": 33.0},
    {"name": "Ursids", "code": "URS", "solar_lon": 270.7, "month": 12, "day": 22, "zhr": 10, "ra": 217.0, "dec": 76.0},
]

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

# -----------------------------------------------------------------------------
# Time range
# -----------------------------------------------------------------------------

NOW_UTC = datetime.now(timezone.utc)
RANGE_START = (NOW_UTC - timedelta(days=LOOKBACK_DAYS)).replace(hour=0, minute=0, second=0, microsecond=0)
RANGE_END = (NOW_UTC + timedelta(days=LOOKAHEAD_DAYS)).replace(hour=23, minute=59, second=59, microsecond=0)
CALC_START = RANGE_START - timedelta(days=45)
CALC_END = RANGE_END + timedelta(days=45)

# -----------------------------------------------------------------------------
# Skyfield setup
# -----------------------------------------------------------------------------

print("Loading ephemeris...")
ts = load.timescale()
eph = load(EPHEMERIS_PATH)

earth = eph["earth"]
moon = eph["moon"]
sun = eph["sun"]

PLANETS = {
    "Mercury": eph["mercury"],
    "Venus": eph["venus"],
    "Mars": eph["mars barycenter"],
    "Jupiter": eph["jupiter barycenter"],
    "Saturn": eph["saturn barycenter"],
}

observer_location = wgs84.latlon(KIRKLAND_LAT, KIRKLAND_LON)
observer = earth + observer_location

T0 = ts.from_datetime(CALC_START)
T1 = ts.from_datetime(CALC_END)

# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------

events: list[dict] = []


def local_text(dt: datetime) -> str:
    return dt.astimezone(TIMEZONE).strftime("%a %b %d, %Y at %I:%M %p %Z")


def format_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def escape_ics(text: str) -> str:
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def fold_ics_line(line: str) -> str:
    """Fold an iCalendar content line at 75 UTF-8 octets."""
    parts: list[str] = []
    current = ""
    limit = 75
    for ch in line:
        if len((current + ch).encode("utf-8")) > limit:
            parts.append(current)
            current = ch
            limit = 74  # continuation line has a leading space
        else:
            current += ch
    parts.append(current)
    return "\r\n ".join(parts)


def stable_uid(key: str) -> str:
    digest = sha1(key.encode("utf-8")).hexdigest()[:24]
    return f"{digest}@kirklandsky"


def add_event(
    title: str,
    start_dt: datetime,
    description: str,
    uid_key: str,
    duration: timedelta = timedelta(hours=1),
    category: str = "Astronomy",
    priority: int = 5,
) -> None:
    if start_dt < RANGE_START or start_dt > RANGE_END:
        return
    events.append(
        {
            "title": title,
            "start": start_dt.astimezone(timezone.utc),
            "end": (start_dt + duration).astimezone(timezone.utc),
            "description": description,
            "uid": stable_uid(uid_key),
            "category": category,
            "priority": priority,
        }
    )


def sf_time(dt: datetime):
    return ts.from_datetime(dt.astimezone(timezone.utc))


def body_altitude_deg(target, dt: datetime) -> float:
    t = sf_time(dt)
    return observer.at(t).observe(target).apparent().altaz()[0].degrees


def sun_altitude_deg(dt: datetime) -> float:
    return body_altitude_deg(sun, dt)


def ecliptic_longitude_deg(target, dt: datetime) -> float:
    t = sf_time(dt)
    apparent = earth.at(t).observe(target).apparent()
    _, lon, _ = apparent.frame_latlon(ecliptic_frame)
    return lon.degrees % 360.0


def signed_angle_diff_deg(a: float, b: float) -> float:
    return ((a - b + 180.0) % 360.0) - 180.0


def angle_diff_deg(a: float, b: float) -> float:
    return abs(signed_angle_diff_deg(a, b))


def separation_deg(target_a, target_b, dt: datetime, topocentric: bool = False) -> float:
    t = sf_time(dt)
    base = observer.at(t) if topocentric else earth.at(t)
    a = base.observe(target_a).apparent()
    b = base.observe(target_b).apparent()
    return a.separation_from(b).degrees


def refine_extremum(
    center: datetime,
    half_span: timedelta,
    value_fn,
    find_min: bool = True,
    iterations: int = 28,
) -> tuple[datetime, float]:
    left = center - half_span
    right = center + half_span
    for _ in range(iterations):
        third = (right - left) / 3
        m1 = left + third
        m2 = right - third
        v1 = value_fn(m1)
        v2 = value_fn(m2)
        if (v1 < v2) == find_min:
            right = m2
        else:
            left = m1
    best = left + (right - left) / 2
    return best, value_fn(best)


def moon_illumination_percent(dt: datetime) -> float:
    phase = almanac.moon_phase(eph, sf_time(dt)).radians
    return 50.0 * (1.0 - cos(phase))


def minimum_circular_span_deg(longitudes: list[float]) -> float:
    if len(longitudes) < 2:
        return 0.0
    vals = sorted(v % 360.0 for v in longitudes)
    gaps = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)]
    gaps.append((vals[0] + 360.0) - vals[-1])
    return 360.0 - max(gaps)


def best_viewing_time(
    center: datetime,
    targets: list,
    window_hours: int = 24,
    step_minutes: int = 20,
    pair: tuple | None = None,
    pair_limit_deg: float | None = None,
) -> tuple[datetime, list[float], float] | None:
    best = None
    best_score = -1e9
    steps = int((window_hours * 2 * 60) / step_minutes) + 1
    start = center - timedelta(hours=window_hours)

    for i in range(steps):
        dt = start + timedelta(minutes=i * step_minutes)
        s_alt = sun_altitude_deg(dt)
        if s_alt > MAX_SUN_ALT_FOR_PLANETS_DEG:
            continue

        alts = [body_altitude_deg(target, dt) for target in targets]
        if min(alts) < MIN_PLANET_ALT_DEG:
            continue

        if pair is not None and pair_limit_deg is not None:
            if separation_deg(pair[0], pair[1], dt) > pair_limit_deg:
                continue

        # Favor altitude first; fully dark skies get a modest bonus.
        darkness_bonus = min(12.0, max(0.0, -s_alt - 6.0))
        score = min(alts) * 2.0 + sum(alts) / len(alts) + darkness_bonus
        if score > best_score:
            best_score = score
            best = (dt, alts, s_alt)

    return best


# -----------------------------------------------------------------------------
# Moon phases, actual equinoxes, Harvest Moon, Blue Moons, Supermoons
# -----------------------------------------------------------------------------

print("Calculating Moon phases and seasonal markers...")
phase_times, phase_codes = almanac.find_discrete(T0, T1, almanac.moon_phases(eph))
full_moons: list[tuple[object, datetime]] = []
new_moons: list[tuple[object, datetime]] = []
for t, code in zip(phase_times, phase_codes):
    dt = t.utc_datetime().astimezone(timezone.utc)
    if int(code) == 2:
        full_moons.append((t, dt))
    elif int(code) == 0:
        new_moons.append((t, dt))

season_times, season_codes = almanac.find_discrete(T0, T1, almanac.seasons(eph))
seasons = [(t.utc_datetime().astimezone(timezone.utc), int(code)) for t, code in zip(season_times, season_codes)]

# Harvest Moons: full moon nearest each actual Autumnal Equinox.
harvest_full_ids: set[int] = set()
for season_dt, code in seasons:
    if code != 2:
        continue
    if not full_moons:
        continue
    idx = min(range(len(full_moons)), key=lambda i: abs((full_moons[i][1] - season_dt).total_seconds()))
    harvest_full_ids.add(idx)

# Seasonal Blue Moon: third full moon in an astronomical season containing four.
seasonal_blue_ids: set[int] = set()
for (season_start, _), (season_end, _) in zip(seasons, seasons[1:]):
    indexes = [i for i, (_, dt) in enumerate(full_moons) if season_start <= dt < season_end]
    if len(indexes) == 4:
        seasonal_blue_ids.add(indexes[2])

# Monthly Blue Moon: second full moon in the same local calendar month.
month_groups: dict[tuple[int, int], list[int]] = defaultdict(list)
for i, (_, dt) in enumerate(full_moons):
    local = dt.astimezone(TIMEZONE)
    month_groups[(local.year, local.month)].append(i)
monthly_blue_ids = {indexes[1] for indexes in month_groups.values() if len(indexes) >= 2}


def moon_distance_km(dt: datetime) -> float:
    return earth.at(sf_time(dt)).observe(moon).distance().km


def nearest_perigee(full_dt: datetime) -> tuple[datetime, float]:
    # Find the nearest distance minimum within +/- 3 days, then refine it.
    samples: list[tuple[datetime, float]] = []
    start = full_dt - timedelta(days=3)
    for i in range(49):
        dt = start + timedelta(hours=3 * i)
        samples.append((dt, moon_distance_km(dt)))
    coarse_dt, _ = min(samples, key=lambda x: x[1])
    return refine_extremum(coarse_dt, timedelta(hours=4), moon_distance_km, find_min=True)


print("Generating named Moon events...")
for i, (t, full_dt) in enumerate(full_moons):
    if full_dt < RANGE_START or full_dt > RANGE_END:
        continue

    local = full_dt.astimezone(TIMEZONE)
    base_name = FULL_MOON_NAMES[local.month]
    monthly_blue = i in monthly_blue_ids
    seasonal_blue = i in seasonal_blue_ids
    harvest = i in harvest_full_ids

    full_distance = earth.at(t).observe(moon).distance().km
    perigee_dt, perigee_distance = nearest_perigee(full_dt)
    perigee_offset_h = abs((full_dt - perigee_dt).total_seconds()) / 3600.0
    is_super = (
        full_distance <= SUPERMOON_DISTANCE_KM
        and perigee_offset_h <= SUPERMOON_MAX_PERIGEE_OFFSET_HOURS
    )

    if monthly_blue:
        label = "Blue Moon"
    elif seasonal_blue:
        label = "Seasonal Blue Moon"
    elif harvest:
        label = "Harvest Moon"
    else:
        label = base_name

    if is_super and monthly_blue:
        title = "Super Blue Moon 🌕"
    elif is_super and harvest:
        title = "Super Harvest Moon 🌾🌕"
    elif is_super:
        title = f"Supermoon 🌕 — {label}"
    elif harvest:
        title = f"Harvest Moon 🌾🌕 ({base_name})"
    elif monthly_blue:
        title = f"Blue Moon 🔵🌕 ({base_name})"
    elif seasonal_blue:
        title = f"Seasonal Blue Moon 🔵🌕 ({base_name})"
    else:
        title = f"{base_name} 🌕"

    moon_alt = body_altitude_deg(moon, full_dt)
    notes = [
        f"Exact full phase: {local_text(full_dt)}.",
        f"Earth-Moon distance at full phase: {full_distance:,.0f} km.",
        f"Moon altitude from Kirkland at the exact full phase: {moon_alt:.1f}°.",
    ]
    if harvest:
        notes.append("This is the full moon closest to the actual Autumnal Equinox calculated by Skyfield.")
    if monthly_blue:
        notes.append("Monthly Blue Moon definition: the second full moon in one local calendar month.")
    if seasonal_blue:
        notes.append("Seasonal Blue Moon definition: the third full moon in an astronomical season containing four full moons.")
    if is_super:
        notes.append(
            f"Project supermoon rule: full-moon distance ≤ {SUPERMOON_DISTANCE_KM:,.0f} km and within "
            f"{SUPERMOON_MAX_PERIGEE_OFFSET_HOURS:.0f} h of perigee. Nearest perigee: {local_text(perigee_dt)} "
            f"at about {perigee_distance:,.0f} km."
        )

    add_event(
        title,
        full_dt,
        "\n".join(notes),
        f"fullmoon-{local.year}-{local.month:02d}-{local.day:02d}",
        category="Moon",
        priority=4 if (is_super or monthly_blue or harvest) else 6,
    )

# -----------------------------------------------------------------------------
# Lunar eclipses / Blood Moons, filtered for Kirkland visibility
# -----------------------------------------------------------------------------

print("Calculating lunar eclipses...")
eclipse_times, eclipse_types, eclipse_details = eclipselib.lunar_eclipses(T0, T1, eph)
for idx, (t, eclipse_code) in enumerate(zip(eclipse_times, eclipse_types)):
    eclipse_code = int(eclipse_code)
    eclipse_name = eclipselib.LUNAR_ECLIPSES[eclipse_code]
    if eclipse_name == "Penumbral":
        continue  # intentionally keep the calendar to visually meaningful events

    maximum_dt = t.utc_datetime().astimezone(timezone.utc)
    if maximum_dt < CALC_START or maximum_dt > CALC_END:
        continue

    visible_samples = []
    for offset_min in range(-180, 181, 15):
        dt = maximum_dt + timedelta(minutes=offset_min)
        m_alt = body_altitude_deg(moon, dt)
        s_alt = sun_altitude_deg(dt)
        if m_alt > 0.0 and s_alt < 0.0:
            visible_samples.append((abs(offset_min), dt, m_alt, s_alt))

    if not visible_samples:
        continue

    _, event_dt, event_moon_alt, _ = min(visible_samples, key=lambda x: x[0])
    max_alt = body_altitude_deg(moon, maximum_dt)
    maximum_visible = max_alt > 0.0 and sun_altitude_deg(maximum_dt) < 0.0
    magnitude = eclipse_details.get("umbral_magnitude", [None] * len(eclipse_times))[idx]

    if eclipse_name == "Total":
        title = "Blood Moon 🩸🌕 — Total Lunar Eclipse"
        priority = 1
    else:
        title = "Partial Lunar Eclipse 🌗"
        priority = 2

    visibility_note = (
        "Maximum eclipse is above the Kirkland horizon."
        if maximum_visible
        else "The eclipse is visible from Kirkland, but the global maximum is below the local horizon; only part of the eclipse window is visible."
    )
    description = (
        f"{eclipse_name} lunar eclipse visible from Kirkland.\n"
        f"Global maximum: {local_text(maximum_dt)}.\n"
        f"Moon altitude at global maximum: {max_alt:.1f}°.\n"
        f"{visibility_note}\n"
        f"Umbral magnitude: {float(magnitude):.3f}."
    )
    local_max = maximum_dt.astimezone(TIMEZONE)
    add_event(
        title,
        event_dt,
        description,
        f"lunar-eclipse-{eclipse_name.lower()}-{local_max.date().isoformat()}",
        duration=timedelta(hours=3),
        category="Eclipse",
        priority=priority,
    )

# -----------------------------------------------------------------------------
# Local solar eclipses, calculated from topocentric Sun/Moon overlap
# -----------------------------------------------------------------------------

print("Checking solar eclipses visible from Kirkland...")


def solar_geometry(dt: datetime) -> tuple[float, float, float, float]:
    t = sf_time(dt)
    obs = observer.at(t)
    sun_app = obs.observe(sun).apparent()
    moon_app = obs.observe(moon).apparent()
    sep = sun_app.separation_from(moon_app).degrees
    sun_radius = degrees(asin(SUN_RADIUS_KM / sun_app.distance().km))
    moon_radius = degrees(asin(MOON_RADIUS_KM / moon_app.distance().km))
    sun_alt = sun_app.altaz()[0].degrees
    return sep, sun_radius, moon_radius, sun_alt


for _, new_dt in new_moons:
    candidates = []
    start = new_dt - timedelta(hours=4)
    for i in range(97):  # 8 hours, every 5 minutes
        dt = start + timedelta(minutes=5 * i)
        sep, sr, mr, s_alt = solar_geometry(dt)
        if s_alt > -0.8333 and sep < sr + mr:
            candidates.append((sep, dt, sr, mr, s_alt))

    if not candidates:
        continue

    _, coarse_dt, _, _, _ = min(candidates, key=lambda x: x[0])
    refined_dt, _ = refine_extremum(
        coarse_dt,
        timedelta(minutes=10),
        lambda d: solar_geometry(d)[0],
        find_min=True,
        iterations=24,
    )
    sep, sr, mr, s_alt = solar_geometry(refined_dt)
    if s_alt <= -0.8333 or sep >= sr + mr:
        # Horizon can clip the numerical minimum; keep the best actually visible sample.
        sep, refined_dt, sr, mr, s_alt = min(candidates, key=lambda x: x[0])

    if sep + sr <= mr:
        eclipse_kind = "Total"
        title = "Total Solar Eclipse ☀️🌑"
        priority = 1
    elif sep + mr <= sr:
        eclipse_kind = "Annular"
        title = "Annular Solar Eclipse ☀️🌑"
        priority = 1
    else:
        eclipse_kind = "Partial"
        title = "Partial Solar Eclipse ☀️🌑"
        priority = 2

    description = (
        f"{eclipse_kind} solar eclipse geometry visible from Kirkland.\n"
        f"Best local overlap: {local_text(refined_dt)}.\n"
        f"Sun altitude: {s_alt:.1f}°.\n"
        f"Sun-Moon center separation: {sep:.3f}°.\n"
        "Classification is computed from apparent topocentric disk overlap at Kirkland; contact times are not yet included."
    )
    local = refined_dt.astimezone(TIMEZONE)
    add_event(
        title,
        refined_dt,
        description,
        f"solar-eclipse-{local.date().isoformat()}",
        duration=timedelta(hours=2),
        category="Eclipse",
        priority=priority,
    )

# -----------------------------------------------------------------------------
# Pairwise conjunctions of bright planets, with twilight-aware local filtering
# -----------------------------------------------------------------------------

print("Searching bright-planet conjunctions...")
planet_items = list(PLANETS.items())
for (name_a, body_a), (name_b, body_b) in combinations(planet_items, 2):
    samples: list[tuple[datetime, float]] = []
    dt = CALC_START
    while dt <= CALC_END:
        samples.append((dt, separation_deg(body_a, body_b, dt)))
        dt += timedelta(hours=12)

    for i in range(1, len(samples) - 1):
        prev_v = samples[i - 1][1]
        center_dt, center_v = samples[i]
        next_v = samples[i + 1][1]
        if center_v > prev_v or center_v > next_v:
            continue
        if center_v > CONJUNCTION_THRESHOLD_DEG + 1.5:
            continue

        exact_dt, exact_sep = refine_extremum(
            center_dt,
            timedelta(hours=12),
            lambda d: separation_deg(body_a, body_b, d),
            find_min=True,
        )
        if exact_sep > CONJUNCTION_THRESHOLD_DEG:
            continue

        best = best_viewing_time(
            exact_dt,
            [body_a, body_b],
            window_hours=24,
            pair=(body_a, body_b),
            pair_limit_deg=min(CONJUNCTION_THRESHOLD_DEG + 1.0, exact_sep + 1.25),
        )
        if best is None:
            continue

        best_dt, alts, s_alt = best
        best_sep = separation_deg(body_a, body_b, best_dt)
        close_label = "Very Close " if exact_sep < 1.0 else ""
        title = f"{close_label}{name_a}–{name_b} Conjunction 🪐"
        description = (
            f"Closest apparent separation: {exact_sep:.2f}° at {local_text(exact_dt)}.\n"
            f"Recommended Kirkland viewing time: {local_text(best_dt)}.\n"
            f"Separation then: {best_sep:.2f}°. Altitudes: {name_a} {alts[0]:.0f}°, {name_b} {alts[1]:.0f}°.\n"
            f"Sun altitude: {s_alt:.0f}° (civil twilight or darker is required)."
        )
        local_exact = exact_dt.astimezone(TIMEZONE)
        add_event(
            title,
            best_dt,
            description,
            f"conjunction-{name_a.lower()}-{name_b.lower()}-{local_exact.date().isoformat()}",
            duration=timedelta(hours=1),
            category="Planets",
            priority=1 if exact_sep < 1.0 else 3,
        )

# -----------------------------------------------------------------------------
# Outer-planet oppositions
# -----------------------------------------------------------------------------

print("Calculating planetary oppositions...")
for name in ("Mars", "Jupiter", "Saturn"):
    body = PLANETS[name]
    f = almanac.oppositions_conjunctions(eph, body)
    times, codes = almanac.find_discrete(T0, T1, f)
    for t, code in zip(times, codes):
        if int(code) != 1:
            continue
        exact_dt = t.utc_datetime().astimezone(timezone.utc)
        best = best_viewing_time(exact_dt, [body], window_hours=18)
        if best is None:
            continue
        best_dt, alts, s_alt = best
        description = (
            f"{name} is at opposition, generally its best observing period of the year.\n"
            f"Exact opposition: {local_text(exact_dt)}.\n"
            f"Recommended Kirkland viewing time: {local_text(best_dt)}; altitude about {alts[0]:.0f}°.\n"
            f"Sun altitude then: {s_alt:.0f}°."
        )
        local = exact_dt.astimezone(TIMEZONE)
        add_event(
            f"{name} at Opposition 🔭",
            best_dt,
            description,
            f"opposition-{name.lower()}-{local.date().isoformat()}",
            duration=timedelta(hours=2),
            category="Planets",
            priority=3,
        )

# -----------------------------------------------------------------------------
# Venus greatest elongations
# -----------------------------------------------------------------------------

print("Calculating Venus greatest elongations...")
venus = PLANETS["Venus"]
venus_samples: list[tuple[datetime, float]] = []
dt = CALC_START
while dt <= CALC_END:
    venus_samples.append((dt, separation_deg(venus, sun, dt)))
    dt += timedelta(hours=12)

for i in range(1, len(venus_samples) - 1):
    if not (venus_samples[i][1] >= venus_samples[i - 1][1] and venus_samples[i][1] >= venus_samples[i + 1][1]):
        continue
    if venus_samples[i][1] < 35.0:
        continue
    exact_dt, elongation = refine_extremum(
        venus_samples[i][0],
        timedelta(hours=18),
        lambda d: separation_deg(venus, sun, d),
        find_min=False,
    )
    diff = signed_angle_diff_deg(ecliptic_longitude_deg(venus, exact_dt), ecliptic_longitude_deg(sun, exact_dt))
    direction = "Eastern" if diff > 0 else "Western"
    viewing_label = "evening" if direction == "Eastern" else "morning"
    best = best_viewing_time(exact_dt, [venus], window_hours=48)
    if best is None:
        continue
    best_dt, alts, s_alt = best
    description = (
        f"Venus reaches greatest {direction.lower()} elongation, about {elongation:.1f}° from the Sun.\n"
        f"This favors {viewing_label} visibility. Exact elongation: {local_text(exact_dt)}.\n"
        f"Recommended Kirkland viewing time: {local_text(best_dt)}; Venus altitude about {alts[0]:.0f}°."
    )
    local = exact_dt.astimezone(TIMEZONE)
    add_event(
        f"Venus Greatest {direction} Elongation ✨",
        best_dt,
        description,
        f"venus-elongation-{direction.lower()}-{local.date().isoformat()}",
        category="Planets",
        priority=3,
    )

# -----------------------------------------------------------------------------
# Multi-planet groupings (3+ bright planets within a 90° ecliptic span)
# -----------------------------------------------------------------------------

print("Searching multi-planet groupings...")
daily_group_candidates: list[dict] = []
local_start_date = RANGE_START.astimezone(TIMEZONE).date()
local_end_date = RANGE_END.astimezone(TIMEZONE).date()
current_date = local_start_date
while current_date <= local_end_date:
    best_for_day = None
    # Sample useful morning/evening hours; daylight is rejected below.
    sample_hours = [4, 5, 6, 7, 17, 18, 19, 20, 21, 22, 23]
    for hour in sample_hours:
        local_dt = datetime.combine(current_date, time(hour=hour), tzinfo=TIMEZONE)
        dt = local_dt.astimezone(timezone.utc)
        s_alt = sun_altitude_deg(dt)
        if s_alt > MAX_SUN_ALT_FOR_PLANETS_DEG:
            continue

        visible = []
        for name, body in PLANETS.items():
            alt = body_altitude_deg(body, dt)
            if alt >= MIN_PLANET_ALT_DEG:
                lon = ecliptic_longitude_deg(body, dt)
                visible.append((name, body, alt, lon))

        if len(visible) < 3:
            continue
        span = minimum_circular_span_deg([v[3] for v in visible])
        if span > PLANET_GROUPING_MAX_SPAN_DEG:
            continue
        score = len(visible) * 1000.0 - span * 4.0 + min(v[2] for v in visible)
        candidate = {
            "date": current_date,
            "dt": dt,
            "visible": visible,
            "span": span,
            "score": score,
            "sun_alt": s_alt,
        }
        if best_for_day is None or score > best_for_day["score"]:
            best_for_day = candidate

    if best_for_day is not None:
        daily_group_candidates.append(best_for_day)
    current_date += timedelta(days=1)

# Collapse consecutive days into a single highlight event.
groups: list[list[dict]] = []
for candidate in daily_group_candidates:
    if not groups or (candidate["date"] - groups[-1][-1]["date"]).days > 2:
        groups.append([candidate])
    else:
        groups[-1].append(candidate)

for group in groups:
    best = max(group, key=lambda c: c["score"])
    names = [v[0] for v in best["visible"]]
    count = len(names)
    if count >= 4:
        title = f"Major {count}-Planet Grouping 🪐"
        priority = 2
    else:
        title = "3-Planet Grouping 🪐"
        priority = 3
    description = (
        f"{', '.join(names)} are simultaneously above {MIN_PLANET_ALT_DEG:.0f}° from Kirkland and grouped within about {best['span']:.0f}° along the ecliptic.\n"
        f"Recommended viewing time: {local_text(best['dt'])}.\n"
        "Approximate altitudes: " + ", ".join(f"{v[0]} {v[2]:.0f}°" for v in best["visible"]) + "."
    )
    add_event(
        title,
        best["dt"],
        description,
        f"planet-grouping-{'-'.join(n.lower() for n in names)}-{best['date'].isoformat()}",
        duration=timedelta(hours=1),
        category="Planets",
        priority=priority,
    )

# -----------------------------------------------------------------------------
# Major meteor showers using solar longitude + local radiant/Moon conditions
# -----------------------------------------------------------------------------

print("Calculating major meteor showers...")


def sun_solar_longitude_deg(dt: datetime) -> float:
    return ecliptic_longitude_deg(sun, dt)


def solve_solar_longitude(year: int, shower: dict) -> datetime:
    approx_local = datetime(year, shower["month"], shower["day"], 12, tzinfo=TIMEZONE)
    approx_utc = approx_local.astimezone(timezone.utc)
    target = shower["solar_lon"]
    return refine_extremum(
        approx_utc,
        timedelta(days=3),
        lambda d: angle_diff_deg(sun_solar_longitude_deg(d), target),
        find_min=True,
        iterations=32,
    )[0]


def best_meteor_viewing(peak_dt: datetime, shower: dict):
    radiant = Star(ra_hours=shower["ra"] / 15.0, dec_degrees=shower["dec"])
    best = None
    best_score = -1e9
    start = peak_dt - timedelta(hours=18)
    for i in range(109):  # 36 hours at 20-minute cadence
        dt = start + timedelta(minutes=20 * i)
        s_alt = sun_altitude_deg(dt)
        if s_alt > -12.0:  # prefer nautical twilight or darker
            continue
        radiant_alt = body_altitude_deg(radiant, dt)
        if radiant_alt < 15.0:
            continue
        moon_alt = body_altitude_deg(moon, dt)
        illum = moon_illumination_percent(dt)
        moon_penalty = 0.0 if moon_alt < 0 else illum * 0.45
        peak_penalty = abs((dt - peak_dt).total_seconds()) / 3600.0 * 0.7
        score = radiant_alt - moon_penalty - peak_penalty
        if score > best_score:
            best_score = score
            best = (dt, radiant_alt, moon_alt, illum, s_alt)
    return best


years = range(RANGE_START.astimezone(TIMEZONE).year - 1, RANGE_END.astimezone(TIMEZONE).year + 2)
for year in years:
    for shower in METEOR_SHOWERS:
        peak_dt = solve_solar_longitude(year, shower)
        if peak_dt < CALC_START or peak_dt > CALC_END:
            continue
        best = best_meteor_viewing(peak_dt, shower)
        if best is None:
            continue
        best_dt, radiant_alt, moon_alt, illum, s_alt = best
        moon_quality = "excellent" if moon_alt < 0 else ("good" if illum < 30 else "challenging")
        description = (
            f"Expected {shower['name']} maximum near solar longitude λ☉={shower['solar_lon']:.2f}°, calculated for {local_text(peak_dt)}.\n"
            f"Typical zenithal hourly rate (ideal dark sky): about {shower['zhr']}.\n"
            f"Recommended Kirkland viewing window begins around {local_text(best_dt)}. Radiant altitude about {radiant_alt:.0f}°.\n"
            f"Moon illumination about {illum:.0f}%, Moon altitude {moon_alt:.0f}°; lunar conditions rated {moon_quality}.\n"
            "Actual observed rates depend strongly on cloud cover, light pollution, radiant altitude, and local sky transparency."
        )
        local_peak = peak_dt.astimezone(TIMEZONE)
        add_event(
            f"{shower['name']} Meteor Shower 🌠",
            best_dt - timedelta(hours=1),
            description,
            f"meteor-{shower['code'].lower()}-{local_peak.year}",
            duration=timedelta(hours=3),
            category="Meteor Shower",
            priority=1 if shower["zhr"] >= 80 else 3,
        )

# -----------------------------------------------------------------------------
# Write standards-friendly ICS
# -----------------------------------------------------------------------------

print("Writing ICS...")
# Remove accidental duplicate UIDs, keeping the earliest event if two detectors
# converge on the same logical event.
unique_events = {}
for event in sorted(events, key=lambda e: e["start"]):
    unique_events.setdefault(event["uid"], event)
events = list(unique_events.values())

stamp = format_utc(NOW_UTC)
lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Kirkland Sky Calendar//Skyfield//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:Kirkland Sky Highlights",
    "X-WR-CALDESC:Location-aware astronomy highlights for Kirkland, Washington",
    "X-WR-TIMEZONE:America/Los_Angeles",
]

for event in sorted(events, key=lambda e: e["start"]):
    lines.extend(
        [
            "BEGIN:VEVENT",
            f"UID:{event['uid']}",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{format_utc(event['start'])}",
            f"DTEND:{format_utc(event['end'])}",
            f"SUMMARY:{escape_ics(event['title'])}",
            f"DESCRIPTION:{escape_ics(event['description'])}",
            "LOCATION:Kirkland\\, WA",
            f"CATEGORIES:{escape_ics(event['category'])}",
            f"PRIORITY:{event['priority']}",
            "TRANSP:TRANSPARENT",
            "STATUS:CONFIRMED",
            "END:VEVENT",
        ]
    )

lines.append("END:VCALENDAR")
OUTPUT_PATH.parent.mkdir(exist_ok=True)
with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as f:
    f.write("\r\n".join(fold_ics_line(line) for line in lines) + "\r\n")

print(f"Created {OUTPUT_PATH} with {len(events)} events")
print(f"Calendar range: {RANGE_START.date()} through {RANGE_END.date()}")
