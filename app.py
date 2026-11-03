import os
from datetime import date, datetime
from dotenv import load_dotenv
from flask import Flask, render_template, render_template_string, session, redirect, request, url_for, abort, flash
import data
from patterns import get_patterns
from pace import get_pace, format_minutes
from ai import suggest_task, write_alert
import google_health

# Load settings like SECRET_KEY from the .env file
load_dotenv()

# Create the Flask app; the secret key lets it remember each user's theme
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Google sign-in routes (/google/login, /callback, /disconnect, /test) live in google_health.py
app.register_blueprint(google_health.google)

# The themes a user can pick from
THEMES = ["calm", "colorful", "bright", "dark"]

# The five feelings on the Check in page
FEELINGS = ["Calm", "Okay", "Tired", "Worried", "Overwhelmed"]

# The three load levels a task can have
LOADS = ["Light", "Medium", "Heavy"]

# Gentle alert messages already written, so Today doesn't call Claude on every visit
ALERT_CACHE = {}

# Data sources in the hidden Demo controls
SOURCES = {"sample": "Sample data", "google": "Google Health"}


# Give every template the theme list and the user's settings
# (calm theme, sample data and greeting banner on, if nothing picked yet)
@app.context_processor
def add_settings():
    return {"themes": THEMES,
            "theme": session.get("theme", "calm"),
            "data_source": session.get("data_source", "sample"),
            "show_banner": session.get("banner", True)}


# "Good morning", "Good afternoon" or "Good evening", from the computer's clock
def greeting():
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


# Morning, Afternoon or Evening for a time like "13:30" (no time counts as Morning)
def part_of_day(time):
    if not time or time < "12:00":
        return "Morning"
    if time < "17:00":
        return "Afternoon"
    return "Evening"


# Template filter: minutes as "6 h 40 min"
@app.template_filter("hours")
def hours_filter(minutes):
    return format_minutes(minutes)


# Template filter: "2026-10-28" as "Wed 28"
@app.template_filter("day")
def day_filter(text):
    d = date.fromisoformat(text)
    return f"{d:%a} {d.day}"


# Turn heart rate readings into points for a simple SVG line chart (600 x 240).
# Values run from y=200 (lowest) up to y=20 (highest); time runs from x=50 to x=570.
def heart_chart(heart, usual):
    bpms = [h["bpm"] for h in heart]
    low, high = min(bpms + [usual]) - 5, max(bpms + [usual]) + 5
    to_y = lambda bpm: round(200 - (bpm - low) / (high - low) * 180)
    step = 520 / (len(bpms) - 1)
    points = " ".join(f"{round(50 + i * step)},{to_y(b)}" for i, b in enumerate(bpms))
    return {"points": points, "usual": usual, "usual_y": to_y(usual), "low": low, "high": high,
            "min": min(bpms), "max": max(bpms), "average": round(sum(bpms) / len(bpms)),
            "first": heart[0]["time"][-5:], "middle": heart[len(heart) // 2]["time"][-5:],
            "last": heart[-1]["time"][-5:]}


# The person picked on the home page, or None if nobody is picked yet.
# For now it also adds two values the old pace rule, heart chart and Body page need:
# usual sleep (average sleep_min in signals.csv) and a fixed usual heart rate of 68.
# Both go away when patterns.py replaces the pace rule.
def current_person():
    person = data.get_person(session.get("person_id"))
    if person:
        sleep = [s["sleep_min"] for s in data.get_signals(person["id"])]
        person["usual_sleep_min"] = round(sum(sleep) / len(sleep)) if sleep else 0
        person["usual_resting_hr"] = 68
    return person


# Today's tasks for a person: the demo tasks plus any they added, minus any moved
# to tomorrow, in time order
def tasks_for(person):
    added = [t for t in session.get("added_tasks", []) if t["person_id"] == person["id"]]
    moved = session.get("moved", [])
    tasks = [t for t in data.get_tasks(person["id"]) + added if [person["id"], t["title"]] not in moved]
    return sorted(tasks, key=lambda t: t["time"] or "99:99")


# Daily rows (date, sleep_min, steps), heart readings and a short note about the source.
# Uses only Google Health days when Demo controls say so and Google returned at least one day;
# otherwise only sample data (never a mix). Heart rate always comes from the sample data.
def body_data(person):
    heart = data.get_heart(person["id"])
    if session.get("data_source") == "google":
        days = google_health.recent_days()
        if days:
            return days, heart, "From Google Health"
    return data.get_daily(person["id"]), heart, "Showing sample data"


# Home page: choose which demo person to use
@app.route("/")
def choose():
    return render_template("choose.html", title="Choose a demo person", people=data.get_people())


# Save the chosen person in the session, then open Today
@app.route("/choose/<person_id>")
def choose_person(person_id):
    if data.get_person(person_id):
        session["person_id"] = person_id
        return redirect(url_for("today"))
    return redirect(url_for("choose"))


# Today screen: pace, alert, inbox and plan on phones; on laptops also a dashboard
# column with body, circle and last check in
@app.route("/today")
def today():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    pid = person["id"]
    daily, heart, source_note = body_data(person)
    # The demo "today" is the newest date in the data, shown like "Wednesday 28 October"
    d = date.fromisoformat(daily[-1]["date"])
    pace = get_pace(person, daily, heart)
    tasks = tasks_for(person)
    checkins = [c for c in session.get("checkins", []) if c["person_id"] == pid]

    # Gentle alert: on a Gentle day, warn about the first Heavy task (unless "Keep my plan" was picked)
    alert = None
    heavy = next((t for t in tasks if t["load"] == "Heavy"), None)
    if pace["level"] == "Gentle" and heavy and pid not in session.get("alert_kept", []):
        key = (pid, heavy["title"])
        if key not in ALERT_CACHE:
            ALERT_CACHE[key] = write_alert(person, heavy)
        alert = {"task": heavy, "message": ALERT_CACHE[key]}

    return render_template("today.html", title="Today", person=person,
                           day=f"{d:%A} {d.day} {d:%B}", greeting=greeting(),
                           pace=pace, alert=alert, source_note=source_note,
                           tasks=tasks,
                           chart=heart_chart(heart, person["usual_resting_hr"]),
                           last_day=daily[-1],
                           circle=data.get_circle(pid),
                           last_checkin=checkins[-1] if checkins else None)


# Gentle alert choices: lighter task first, move to tomorrow, keep my plan, message someone
@app.route("/alert", methods=["POST"])
def alert_choice():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    choice = request.form.get("choice")
    title = request.form.get("title", "")
    tasks = tasks_for(person)

    # Lighter task first: open the steps of the first Light task
    if choice == "lighter":
        light = next((i for i, t in enumerate(tasks) if t["load"] == "Light"), None)
        if light is not None:
            flash(f"Starting with a lighter task: {tasks[light]['title']}.")
            return redirect(url_for("task_steps", index=light))
        flash("There is no lighter task today.")
    # Move to tomorrow: hide the task from today's plan (demo only, saved in the session)
    elif choice == "move":
        session["moved"] = session.get("moved", []) + [[person["id"], title]]
        flash(f"{title} moved to tomorrow.")
    # Keep my plan: hide the alert for this person
    elif choice == "keep":
        session["alert_kept"] = session.get("alert_kept", []) + [person["id"]]
        flash("Okay, keeping your plan. Go gently.")
    # Message someone I trust: open the Circle page
    elif choice == "message":
        flash("Choose someone in your Circle to message.")
        return redirect(url_for("circle"))
    return redirect(url_for("today"))


# Task steps screen: one task's steps, shown one at a time by static/js/steps.js
@app.route("/task/<int:index>")
def task_steps(index):
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    tasks = tasks_for(person)
    if index >= len(tasks):
        abort(404)
    return render_template("task.html", title=tasks[index]["title"],
                           task=tasks[index], person=person)


# Add a task: type a task, get a suggested load and steps, change them, then save
@app.route("/add", methods=["GET", "POST"])
def add_task():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    task_title = request.form.get("title", "").strip()[:80]
    action = request.form.get("action")

    # Save: keep the edited task in the session (demo only, keeps the last 10) and go to Today
    if action == "save" and task_title and request.form.get("load") in LOADS:
        steps = [s.strip()[:80] for s in request.form.getlist("steps") if s.strip()]
        added = session.get("added_tasks", [])
        added.append({"person_id": person["id"], "title": task_title,
                      "time": request.form.get("time", ""),
                      "part_of_day": part_of_day(request.form.get("time", "")),
                      "load": request.form["load"], "source": "manual",
                      "steps": steps or [task_title]})
        session["added_tasks"] = added[-10:]
        flash("Task added to your plan.")
        return redirect(url_for("today"))

    # Suggest: ask the AI (or the keyword backup) for a load level and steps
    suggestion = suggest_task(task_title) if action == "suggest" and task_title else None
    return render_template("add.html", title="Add a task", task_title=task_title,
                           suggestion=suggestion, loads=LOADS)


# Check in screen: pick a feeling, add an optional note, then Save (or Skip)
@app.route("/checkin", methods=["GET", "POST"])
def checkin():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    checkins = session.get("checkins", [])

    # Save: add the check in to the session (demo only, keeps the last 20) and go to Today
    if request.method == "POST" and request.form.get("feeling") in FEELINGS:
        checkins.append({"person_id": person["id"],
                         "time": datetime.now().strftime("%H:%M"),
                         "feeling": request.form["feeling"],
                         "note": request.form.get("note", "").strip()[:200]})
        session["checkins"] = checkins[-20:]
        flash("Check in saved. Thank you.")
        return redirect(url_for("today"))

    # Show the form, plus this person's earlier check ins
    mine = [c for c in checkins if c["person_id"] == person["id"]]
    return render_template("checkin.html", title="Check in", feelings=FEELINGS, checkins=mine)


# Patterns: placeholder for now; later shows when several of the person's patterns change together
@app.route("/patterns")
def patterns():
    if not current_person():
        return redirect(url_for("choose"))
    return render_template("patterns.html", title="Patterns")


# Trust circle: people this person can reach out to, each with a ready-made message to copy
@app.route("/circle")
def circle():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    return render_template("circle.html", title="Circle", circle=data.get_circle(person["id"]))


# Me: the person, what drains and calms them, and links to My body today and Settings
@app.route("/me")
def me():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    return render_template("me.html", title="Me", person=person)


# My body today: heart rate line chart, plus sleep and steps for the last 7 days
@app.route("/body")
def body():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    daily, heart, source_note = body_data(person)
    week = daily[-7:]
    # Bar lengths are relative to the biggest day (at least 1, so we never divide by 0)
    return render_template("body.html", title="My body today", person=person,
                           chart=heart_chart(heart, person["usual_resting_hr"]),
                           daily=week, source_note=source_note,
                           max_sleep=max(d["sleep_min"] for d in week) or 1,
                           max_steps=max(d["steps"] for d in week) or 1)


# Settings: theme choice, plus hidden Demo controls for the data source
@app.route("/settings", methods=["GET", "POST"])
def settings():
    # Demo controls: save the chosen data source
    if request.method == "POST" and request.form.get("source") in SOURCES:
        session["data_source"] = request.form["source"]
        flash(f"Data source set to {SOURCES[request.form['source']]}.")
        return redirect(url_for("settings"))
    return render_template("settings.html", title="Settings", sources=SOURCES,
                           google_connected=session.get("google_key") in google_health.TOKENS)


# Temporary check (Stage P3): the patterns result for every demo person, in plain text
@app.route("/debug")
def debug_patterns():
    lines = []
    for p in data.get_people():
        result = get_patterns(p["id"])
        lines.append(f"{p['id']} {p['first_name']}: {result['status']} ({result['change_count']} changes)")
        lines += [f"  - {c['words']} (usual {c['usual']}, recent {c['recent']})" for c in result["changes"]]
        lines += [f"  + {n}" for n in result["positive_notes"] + result["routine_notes"]]
        lines += [f"  check in {c['date']}: {c['mood']}" for c in result["recent_checkins"]]
    return render_template_string("<pre>{{ text }}</pre>", text="\n".join(lines))


# Temporary check (Stage P2): how many rows each data function returns for one person
@app.route("/debug/<person_id>")
def debug(person_id):
    counts = {"get_people": len(data.get_people()),
              "get_person": 1 if data.get_person(person_id) else 0,
              "get_signals": len(data.get_signals(person_id)),
              "get_devices": len(data.get_devices(person_id)),
              "get_checkins": len(data.get_checkins(person_id)),
              "get_circle": len(data.get_circle(person_id))}
    lines = [f"{name}: {count} rows" for name, count in counts.items()]
    return "<br>".join(lines + [f"get_today: {data.get_today()}"])


# Me page setting: turn the greeting banner on Today on or off
@app.route("/banner", methods=["POST"])
def toggle_banner():
    session["banner"] = not session.get("banner", True)
    flash("Greeting banner turned " + ("on." if session["banner"] else "off."))
    return redirect(url_for("me"))


# Save the chosen theme, then go back to the page the user was on
@app.route("/theme/<name>")
def set_theme(name):
    if name in THEMES:
        session["theme"] = name
    return redirect(request.referrer or url_for("today"))


# Start the app in debug mode when this file is run directly
if __name__ == "__main__":
    app.run(debug=True)
