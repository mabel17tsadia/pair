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
