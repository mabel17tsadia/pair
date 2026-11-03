import os
from datetime import date, datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, render_template, render_template_string, session, redirect, request, url_for, abort, flash
import data
from patterns import get_patterns, feeling_counts
from pace import format_minutes
from ai import explain_week, explain_for_doctor
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


# Template filter: minutes as "6 h 40 min"
@app.template_filter("hours")
def hours_filter(minutes):
    return format_minutes(minutes)


# Template filter: a list as plain words, like "sleep, steps and unlocks"
@app.template_filter("words")
def words_filter(items):
    return " and ".join([", ".join(items[:-1]), items[-1]]) if len(items) > 1 else "".join(items)


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


# A person's picture-step tasks from tasks.csv, in time order (opened from routine notes)
def tasks_for(person):
    return sorted(data.get_tasks(person["id"]), key=lambda t: t["time"] or "99:99")


# Paired devices. A real product would connect through each maker's official app or account.
# Here all device data is simulated from the CSV files; only the optional Google Health card
# is a real sign in (see google_health.py), and its data is not used for patterns yet.
GOOGLE_DEVICE = "Google Health (Fitbit, Pixel Watch)"


# A person's devices with their current pairing choices from the session (the CSV never changes)
def devices_for(person):
    choices = session.get("paired", {}).get(person["id"], {})
    devices = data.get_devices(person["id"])
    for d in devices:
        d["paired"] = choices.get(d["device"], d["paired"])
    return devices


# The devices above plus the Google Health card, paired when this browser is signed in to Google
def device_cards(person):
    google = {"device": GOOGLE_DEVICE, "kind": "wearable", "signals": ["sleep", "steps"],
              "connects_through": "Your Google account", "paired": google_health.is_connected()}
    return devices_for(person) + [google]


# Save one pairing choice for this person in the session
def set_paired(person, name, paired):
    choices = session.get("paired", {})
    choices.setdefault(person["id"], {})[name] = paired
    session["paired"] = choices
    # Devices changed, so the saved week and doctor summaries are out of date
    session.get("week", {}).pop(person["id"], None)
    session.get("doctor", {}).pop(person["id"], None)
    session.modified = True


# Run make() at most once per person per day and keep its answer in the session under "key",
# so Claude is not asked again on every visit (cleared when paired devices change)
def daily_cache(key, person, make):
    saved = session.get(key, {})
    today_text = date.today().isoformat()
    if saved.get(person["id"], {}).get("day") != today_text:
        saved[person["id"]] = {**make(), "day": today_text}
        session[key] = saved
    return saved[person["id"]]


# The AI (or rule based) week summary and gentle step for Today
def week_text(person, patterns):
    return daily_cache("week", person, lambda: explain_week(person, patterns))


# ===== Trust circle =====
# The four access levels: a short name and what that person sees, in plain words
LEVELS = {
    "checkins": ("Check ins", "Sees the mood check ins you choose to share."),
    "summary": ("Weekly summary", "Sees your week status and summary in words, no numbers."),
    "wellness": ("Wellness details", "Sees the summary plus your signal trends (for a coach or 360 wellness staff)."),
    "health": ("Health summary", "Sees the doctor visit summary only when you send it."),
}

# Each change in words with no numbers, for the Weekly summary level.
# Time away from home is left out on purpose: it is never shared.
SHARE_WORDS = {"sleep_min": "Sleeping less than usual", "steps": "Walking less than usual",
               "late_screen_min": "More time on the phone late at night",
               "unlocks": "Picking up the phone more often"}

# Units for the numbers in Wellness details (daily averages)
SHARE_UNITS = {"sleep_min": "min", "steps": "steps", "late_screen_min": "min", "unlocks": "unlocks"}


# A person's circle: people from circle.csv plus anyone added, with any level changes
# from the session (the CSV never changes)
def circle_for(person):
    added = session.get("circle_added", {}).get(person["id"], [])
    levels = session.get("circle_levels", {}).get(person["id"], {})
    members = [dict(m) for m in data.get_circle(person["id"]) + added]
    for m in members:
        m["access"] = levels.get(m["name"], m["access"])
    return members


# Exactly what one member would see at their level, as a list of short lines.
# Health summary sees nothing here (only a doctor visit summary the person sends).
# Check in notes and time away from home are never included.
def shared_view(access, patterns):
    if access == "health":
        return []
    if access == "checkins":
        return [f"{day_filter(c['date'])}: feeling {c['mood']}" for c in patterns["recent_checkins"]]
    lines = [f"Week: {patterns['status']}"]
    for c in patterns["changes"]:
        if c["signal"] not in SHARE_WORDS:
            continue
        words = SHARE_WORDS[c["signal"]]
        if access == "wellness":
            unit = SHARE_UNITS[c["signal"]]
            words += f" (usual {c['usual']:,} {unit}, last 5 days {c['recent']:,} {unit})"
        lines.append(words)
    return lines


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


# Today screen: greeting, "Your week", what Pair noticed, notes, one gentle step and two buttons;
# on laptops also the trust circle and last check in
@app.route("/today")
def today():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    pid = person["id"]
    # The demo "today" is the latest date in signals.csv, shown like "Wednesday 4 November"
    d = date.fromisoformat(data.get_today())
    checkins = [c for c in session.get("checkins", []) if c["person_id"] == pid]
    # The laundry picture steps, opened from the "No laundry" note (None if this person has none)
    laundry = next((i for i, t in enumerate(tasks_for(person)) if t["title"] == "Laundry"), None)
    patterns = get_patterns(pid, devices_for(person))
    return render_template("today.html", title="Today", person=person,
                           day=f"{d:%A} {d.day} {d:%B}", patterns=patterns,
                           week=week_text(person, patterns),
                           laundry_index=laundry, circle=circle_for(person),
                           last_checkin=checkins[-1] if checkins else None)


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


# Trust circle: each person's name, relationship and access level, with a "Change" option,
# a ready-made message to copy, and a form to add someone
@app.route("/circle")
def circle():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    return render_template("circle.html", title="Circle", circle=circle_for(person), levels=LEVELS)


# Change one member's access level (saved in the session)
@app.route("/circle/level", methods=["POST"])
def circle_level():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    name, access = request.form.get("name"), request.form.get("access")
    if access in LEVELS and any(m["name"] == name for m in circle_for(person)):
        all_levels = session.get("circle_levels", {})
        all_levels.setdefault(person["id"], {})[name] = access
        session["circle_levels"] = all_levels
        flash(f"{name} now has {LEVELS[access][0]}.")
    return redirect(url_for("circle"))


# Add someone I trust: name, relationship and level (saved in the session)
@app.route("/circle/add", methods=["POST"])
def circle_add():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    name = request.form.get("name", "").strip()[:40]
    relationship = request.form.get("relationship", "").strip()[:40]
    access = request.form.get("access")
    if not name or not relationship or access not in LEVELS:
        flash("Please add a name, a relationship and a level.")
    elif any(m["name"] == name for m in circle_for(person)):
        flash(f"{name} is already in your circle.")
    else:
        added = session.get("circle_added", {})
        added.setdefault(person["id"], []).append({"name": name, "relationship": relationship, "access": access})
        session["circle_added"] = added
        flash(f"{name} added to your circle.")
    return redirect(url_for("circle"))


# Share with my circle: a preview of exactly what each member would see, with a checkbox each
# (all unticked). "Send" only shows a confirmation; nothing is really sent in the prototype.
@app.route("/share", methods=["GET", "POST"])
def share():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    members = circle_for(person)
    if request.method == "POST":
        names = [m["name"] for m in members
                 if m["name"] in request.form.getlist("share") and m["access"] != "health"]
        if names:
            flash(f"Prototype: nothing was really sent. In the real app, {words_filter(names)} would now see their view.")
        else:
            flash("No one was ticked, so nothing was shared.")
        return redirect(url_for("today"))
    patterns = get_patterns(person["id"], devices_for(person))
    return render_template("share.html", title="Share with my circle", levels=LEVELS,
                           members=[{**m, "view": shared_view(m["access"], patterns)} for m in members])


# Prepare for a doctor visit: a one page summary of the last 14 days that the person reviews,
# then prints or sends to a Health summary member. Questions they type are kept in the session.
@app.route("/doctor", methods=["GET", "POST"])
def doctor():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    pid = person["id"]
    if request.method == "POST":
        questions = session.get("doctor_questions", {})
        questions[pid] = request.form.get("questions", "").strip()[:1000]
        session["doctor_questions"] = questions
        flash("Your questions are saved.")
        return redirect(url_for("doctor"))

    # The last 14 days, counting back from the demo "today"
    end = date.fromisoformat(data.get_today())
    start = end - timedelta(days=13)
    checkins = [c for c in data.get_checkins(pid) if c["date"] >= start.isoformat()]
    devices = devices_for(person)
    patterns = get_patterns(pid, devices)
    return render_template("doctor.html", title="Prepare for a doctor visit", person=person,
                           period=f"{start.day} {start:%B} to {end.day} {end:%B %Y}",
                           patterns=patterns, counts=feeling_counts(checkins),
                           summary=daily_cache("doctor", person, lambda: explain_for_doctor(person, patterns, checkins)),
                           questions=session.get("doctor_questions", {}).get(pid, ""),
                           sources=[d["device"] for d in devices if d["paired"]] + ["My own check ins"],
                           contacts=[m["name"] for m in circle_for(person) if m["access"] == "health"])


# Send to my health contact: only ticked Health summary members; a confirmation only,
# nothing is really sent in the prototype
@app.route("/doctor/send", methods=["POST"])
def doctor_send():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    names = [m["name"] for m in circle_for(person)
             if m["access"] == "health" and m["name"] in request.form.getlist("send")]
    if names:
        flash(f"Prototype: nothing was really sent. In the real app, {words_filter(names)} would get this summary.")
    else:
        flash("No one was ticked, so nothing was sent.")
    return redirect(url_for("doctor"))


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
                           google_connected=google_health.is_connected())


# Paired devices: the person's devices in two groups, Paired and Available to pair
@app.route("/devices")
def devices():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    cards = device_cards(person)
    return render_template("devices.html", title="Paired devices", google_name=GOOGLE_DEVICE,
                           paired=[d for d in cards if d["paired"]],
                           available=[d for d in cards if not d["paired"]])


# Consent page for pairing one device: what Pair reads, never reads, and who can see it.
# "Pair" saves the choice (or, for Google Health, goes to the Google sign in).
@app.route("/devices/pair/<name>", methods=["GET", "POST"])
def pair_device(name):
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    device = next((d for d in device_cards(person) if d["device"] == name), None)
    if not device:
        abort(404)
    if request.method == "POST":
        if name == GOOGLE_DEVICE:
            session["google_from_devices"] = True
            return redirect(url_for("google.login"))
        set_paired(person, name, True)
        flash(f"{name} is paired.")
        return redirect(url_for("devices"))
    return render_template("pair.html", title=f"Pair {name}", device=device)


# Stop pairing one device (Google Health uses its own Disconnect button instead)
@app.route("/devices/stop/<name>", methods=["POST"])
def stop_pairing(name):
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    if any(d["device"] == name for d in devices_for(person)):
        set_paired(person, name, False)
        flash(f"Stopped pairing {name}. Pair no longer reads it.")
    return redirect(url_for("devices"))


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
