from collections import Counter
from datetime import date
import pandas as pd
import data

# ===== Thresholds: when a difference between "recent" and "usual" counts as a change =====
RECENT_DAYS = 5            # the last 5 days are "recent"; all earlier days are "usual"
MIN_DAYS = 10              # fewer days than this: still learning the person's usual
SLEEP_DROP_MIN = 45        # sleeping 45+ minutes less
STEPS_DROP_PCT = 25        # 25%+ fewer steps
LATE_SCREEN_RISE_MIN = 30  # 30+ more minutes on the phone late at night
UNLOCKS_RISE_PCT = 25      # picking up the phone 25%+ more often
TIME_OUT_DROP_PCT = 30     # 30%+ less time away from home
STEPS_UP_PCT = 15          # 15%+ more steps earns a positive note
LAUNDRY_GAP_DAYS = 10      # no laundry for 10+ days earns a routine note


# Minutes as "6 h 40 min" (or "8 h" when there are no extra minutes)
def format_minutes(minutes):
    hours, mins = divmod(round(minutes), 60)
    return f"{hours} h {mins} min" if mins else f"{hours} h"


# Minutes as kind, rounded words: "1 hour", "2 hours" or "40 minutes"
def about(minutes):
    if minutes >= 60:
        hours = round(minutes / 60)
        return f"{hours} hour" + ("s" if hours > 1 else "")
    return f"{round(minutes)} minutes"


# Compare a person's recent days with their usual days and describe what changed.
# "devices" are the person's current pairing choices; if not given, the CSV is used.
def get_patterns(person_id, devices=None):
    rows = data.get_signals(person_id)
    result = {"status": "Still learning your usual", "change_count": 0, "changes": [],
              "positive_notes": [], "routine_notes": [],
              "recent_checkins": data.get_checkins(person_id)[-3:]}
    if len(rows) < MIN_DAYS:
        return result

    # Averages for the usual days and the recent days
    df = pd.DataFrame(rows)
    usual = df.iloc[:-RECENT_DAYS].mean(numeric_only=True)
    recent = df.iloc[-RECENT_DAYS:].mean(numeric_only=True)
    pct = lambda col: (recent[col] - usual[col]) / usual[col] * 100

    # Signals the person's paired devices provide (only these are checked).
    # "time out of home" only comes from the "Time away from home" device.
    devices = devices if devices is not None else data.get_devices(person_id)
    signals = {s for d in devices if d["paired"] for s in d["signals"]}

    # Add one change with its plain words, usual value and recent value
    def change(col, words):
        result["changes"].append({"signal": col, "words": words,
                                  "usual": round(usual[col]), "recent": round(recent[col])})

    # The five changes we look for
    if "sleep" in signals and usual["sleep_min"] - recent["sleep_min"] >= SLEEP_DROP_MIN:
        change("sleep_min", f"Sleeping about {about(usual['sleep_min'] - recent['sleep_min'])} less than usual")
    if "steps" in signals and -pct("steps") >= STEPS_DROP_PCT:
        change("steps", f"Walking about {round(-pct('steps'))}% fewer steps than usual")
    if "late screen time" in signals and recent["late_screen_min"] - usual["late_screen_min"] >= LATE_SCREEN_RISE_MIN:
        change("late_screen_min", f"On the phone late at night about "
                                  f"{about(recent['late_screen_min'] - usual['late_screen_min'])} more than usual")
    if "unlocks" in signals and pct("unlocks") >= UNLOCKS_RISE_PCT:
        change("unlocks", f"Picking up the phone about {round(pct('unlocks'))}% more often than usual")
    if "time out of home" in signals and -pct("time_out_min") >= TIME_OUT_DROP_PCT:
        change("time_out_min", f"Spending about {round(-pct('time_out_min'))}% less time away from home than usual")

    # Status from the number of changes
    count = len(result["changes"])
    result["change_count"] = count
    result["status"] = "Steady week" if count <= 1 else "A few changes" if count == 2 else "Several changes"

    # Positive note: more steps than usual
    if "steps" in signals and pct("steps") >= STEPS_UP_PCT:
        result["positive_notes"].append("You moved more than usual this week.")

    # Routine note: days since the last laundry, if a paired washer has run at least once
    if "laundry runs" in signals:
        laundry_days = [r["date"] for r in rows if r["laundry_runs"] == 1]
        if laundry_days:
            gap = (date.fromisoformat(data.get_today()) - date.fromisoformat(laundry_days[-1])).days
            if gap >= LAUNDRY_GAP_DAYS:
                result["routine_notes"].append(f"No laundry in {gap} days")
    return result


# The signals shown on the Patterns page: column -> (name, the device signal that provides it,
# and whether the number is minutes or a count). Laundry is left out: it is a routine note instead.
SIGNALS = {
    "sleep_min": ("Sleep", "sleep", "minutes"),
    "steps": ("Steps", "steps", "count"),
    "late_screen_min": ("Phone time late at night", "late screen time", "minutes"),
    "unlocks": ("Phone pickups", "unlocks", "count"),
    "time_out_min": ("Time away from home", "time out of home", "minutes"),
}


# Each signal from a paired device for the Patterns page: its daily values, usual and recent
# averages, and one plain sentence ("Sleep: about 1 hour less than usual over the last 5 days")
def get_trends(person_id, devices=None):
    rows = data.get_signals(person_id)
    if len(rows) < MIN_DAYS:
        return []
    devices = devices if devices is not None else data.get_devices(person_id)
    paired = {s for d in devices if d["paired"] for s in d["signals"]}
    patterns = get_patterns(person_id, devices)
    noticed = {c["signal"] for c in patterns["changes"]}
    trends = []
    for col, (name, source, kind) in SIGNALS.items():
        if source not in paired:
            continue
        values = [r[col] for r in rows]
        usual = sum(values[:-RECENT_DAYS]) / (len(values) - RECENT_DAYS)
        recent = sum(values[-RECENT_DAYS:]) / RECENT_DAYS
        diff, pct = recent - usual, (recent - usual) / usual * 100
        # Describe the difference only if it counted as a change (or as moving more than usual)
        if col in noticed or (col == "steps" and pct >= STEPS_UP_PCT):
            amount = about(abs(diff)) if kind == "minutes" else f"{round(abs(pct))}%"
            more = "more" if diff > 0 else "fewer" if kind == "count" else "less"
            sentence = f"{name}: about {amount} {more} than usual over the last 5 days"
        else:
            sentence = f"{name}: close to your usual"
        trends.append({"signal": col, "name": name, "dates": [r["date"] for r in rows],
                       "values": values, "usual": usual, "recent": recent, "sentence": sentence})
    return trends


# How often each mood and each body feeling came up in some check ins, most common first,
# for example {"moods": [("Worried", 2)], "body": [("Tired", 4), ("Headache", 2)]} ("none" is left out)
def feeling_counts(checkins):
    moods = Counter(c["mood"].capitalize() for c in checkins if c["mood"])
    body = Counter(b.capitalize() for c in checkins for b in c["body"] if b != "none")
    return {"moods": moods.most_common(), "body": body.most_common()}
