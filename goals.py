from datetime import date, timedelta
import data

# "This week" is the last 7 days up to the demo "today"
WEEK_DAYS = 7
SLEEP_CLOSE_MIN = 30   # sleep within 30 minutes of usual counts as "close to my usual"
LATE_SCREEN_MAX = 30   # under 30 minutes of late screen time counts as "phone down before midnight"


# A person's weekly goals with progress, target and done (True or False).
# "done_names" are manual goals the person tapped Done on or routines they finished,
# "extra_checkins" are check ins saved today on top of checkins.csv, and "added_goals" are names of
# goals the person added on My climb (all kept in the session by app.py).
def get_goals(person_id, done_names=(), extra_checkins=0, added_goals=()):
    today = date.fromisoformat(data.get_today())
    start = (today - timedelta(days=WEEK_DAYS - 1)).isoformat()
    rows = data.get_signals(person_id)
    week = [r for r in rows if r["date"] >= start]
    before = [r for r in rows if r["date"] < start] or rows

    # The person's usual steps and sleep: their average before this week (0 for a new person)
    usual_steps = sum(r["steps"] for r in before) / len(before) if before else 0
    usual_sleep = sum(r["sleep_min"] for r in before) / len(before) if before else 0

    # How far each kind of goal has got this week
    progress = {
        "steps_usual": sum(r["steps"] >= usual_steps for r in week),
        "laundry": int(sum(r["laundry_runs"] or 0 for r in week)),
        "late_screen_under_30": sum(r["late_screen_min"] < LATE_SCREEN_MAX for r in week),
        "sleep_usual": sum(abs(r["sleep_min"] - usual_sleep) <= SLEEP_CLOSE_MIN for r in week),
        "checkins": sum(c["date"] >= start for c in data.get_checkins(person_id)) + extra_checkins,
    }

    # Goals from goals.csv, plus goals the person added (each is done by tapping Done once)
    added = [{"goal": name, "kind": "manual", "rule": "done", "target": 1, "added_by": "me"} for name in added_goals]
    goals = []
    for g in data.get_goals(person_id) + added:
        target = int(g["target"])
        done_count = 1 if g["rule"] in ["done", "routine"] and g["goal"] in done_names else progress.get(g["rule"], 0)
        goals.append({**g, "target": target, "progress": min(done_count, target), "done": done_count >= target})
    return goals


# Days left in this calendar week (Monday to Sunday), for the encouraging message
def days_left():
    return 6 - date.fromisoformat(data.get_today()).weekday()


# "Week of 2 November": the Monday of the demo week, used to name summit badges
def week_name():
    today = date.fromisoformat(data.get_today())
    monday = today - timedelta(days=today.weekday())
    return f"Week of {monday.day} {monday:%B}"
