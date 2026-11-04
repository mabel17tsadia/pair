import os
from datetime import date, datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, render_template, session, redirect, request, url_for, abort, flash
import data
from demo_data import load_demo_data, plan_activities
from patterns import get_patterns, get_trends, feeling_counts, format_minutes, RECENT_DAYS
from goals import get_goals, days_left, week_name
from vitals import get_body_signals
from ai import (explain_week, explain_for_doctor, respond_to_checkin, suggest_questions, suggest_steps,
                suggest_professionals, is_urgent)
from visits import VISITS, things_to_tell
import google_health

# Load settings from the .env file on a laptop. On Render there is no .env file: SECRET_KEY,
# ANTHROPIC_API_KEY and the optional Google keys are set as environment variables instead.
load_dotenv()

# Create the Flask app; the secret key signs the session cookie that remembers each person's choices.
# Without it nothing can be remembered, so stop with a clear message instead of failing later.
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("SECRET_KEY is missing. Add it to .env on your laptop, or as an environment variable on Render.")

# Google sign-in routes (/google/login, /callback, /disconnect, /test) live in google_health.py
app.register_blueprint(google_health.google)

# The themes a user can pick from
THEMES = ["ocean", "garden", "twilight"]
# Keep saved theme choices from older browser sessions working
OLD_THEMES = {"calm": "ocean", "bright": "garden", "dark": "twilight"}

# These role choices change only which navigation links the demo shows.
DEMO_ROLES = {"member": "Pair member", "coach": "Coach or educator",
              "healthcare": "Healthcare professional", "trusted": "Trusted person",
              "admin": "Organization administrator"}
ROLE_NAVIGATION = {
    "member": [
        ("Home", "today", "sun", ["today"]),
        ("My Plan", "plan", "calendar", ["plan"]),
        ("Check In", "checkin", "check", ["checkin"]),
        ("Health", "health", "heart", ["health", "health_packets", "health_packet",
                                            "health_next_steps", "patterns", "body", "devices",
                                            "pair_device", "stop_pairing", "visit_start", "visit_page",
                                            "visit_suggest", "visit_add_question", "visit_entry",
                                            "visit_send", "visit_not_sure"]),
        ("My Circle", "circle", "people", ["circle"]),
        ("Me", "me", "user", ["me", "settings", "climb",
                                "climb_done", "climb_add", "routines", "routine_steps", "routine_edit"]),
    ],
    "coach": [
        ("Overview", "coach", "wave", ["coach"]), ("Learners", None, "people", []),
        ("Activity Library", None, "book", []), ("Coach Settings", None, "gear", []),
    ],
    "healthcare": [
        ("Packets", None, "clipboard", []), ("Packet Detail", None, "clipboard", []),
        ("Preferences", None, "gear", []), ("Next Steps", None, "flag", []),
        ("Professional Settings", None, "gear", []),
    ],
    "trusted": [
        ("Shared with Me", None, "heart", []), ("Accomplishments", None, "flag", []),
        ("Support Requests", None, "people", []), ("Settings", None, "gear", []),
    ],
    "admin": [
        ("Accounts", None, "people", []), ("Verify Roles", None, "check", []),
        ("Invitations", None, "clipboard", []), ("Org Settings", None, "home", []),
        ("Access Logs", None, "wave", []), ("Templates", None, "book", []),
    ],
}
HEALTH_ENDPOINTS = {
    "health", "health_packets", "health_packet", "health_next_steps", "patterns", "body",
    "devices", "pair_device", "stop_pairing", "visit_start", "visit_page", "visit_suggest",
    "visit_add_question", "visit_entry", "visit_send", "visit_not_sure",
}

# The five moods on the Check in page, each with its emoji (the one place for the whole app;
# templates use it through the mood_emoji macro)
MOODS = {"Calm": "😌", "Okay": "🙂", "Tired": "😴", "Worried": "😟",
         "Overwhelmed": "😣", "Another Feeling": "🤔"}
app.jinja_env.globals["MOODS"] = MOODS
CHECKIN_HELP = [
    {"value": "quiet_break", "label": "Quiet Break", "icon": "🌿"},
    {"value": "smaller_step", "label": "Smaller Step", "icon": "🪜"},
    {"value": "message_someone", "label": "Message Someone", "icon": "💬"},
    {"value": "read_aloud", "label": "Read Aloud", "icon": "🔊"},
    {"value": "reduce_screen", "label": "Reduce Screen Content", "icon": "📱"},
    {"value": "nothing_now", "label": "Nothing Right Now", "icon": "🌱"},
]
CHECKIN_DISPLAY = [("pictures_words", "Pictures and Words"), ("words_only", "Words Only"),
                   ("pictures_first", "Pictures First")]

# The id of a person who signed up at /start (kept in the session only, never in a file)
NEW_ID = "new"

# Phone signals offered when signing up: (device signal, name, one plain sentence, on at the start)
SIGNUP_SIGNALS = [
    ("sleep", "Sleep", "Roughly how long you sleep, from when your phone rests at night.", True),
    ("steps", "Movement", "How many steps you take each day.", True),
    ("late screen time", "Late screen time", "How many minutes you spend on your phone late at night.", True),
    ("unlocks", "Unlocks", "How often you pick up your phone.", True),
    ("time out of home", "Time away from home", "Only the minutes you are away from home. Never a map.", False),
]

# How flags and the summit are celebrated on My climb. Big (silent confetti) is the default; on a
# device that asks for less motion, confetti.js never moves, so Big then looks like Calm.
CELEBRATIONS = {"big": "Big", "calm": "Calm", "off": "Off"}

# Two earlier summit badges for Theo, so the demo badge collection is not empty
SAMPLE_BADGES = {"p3": ["Summit · Week of 19 October", "Summit · Week of 26 October"]}

# Data sources in the hidden Demo controls
SOURCES = {"sample": "Sample data", "google": "Google Health"}


# Give every template the theme list and the user's settings
# (Ocean theme, sample data and Big celebrations, if nothing picked yet). "celebrations_chosen" is
# True once the person saved a Celebrations setting themselves; their choice is always kept.
@app.context_processor
def add_settings():
    theme = OLD_THEMES.get(session.get("theme"), session.get("theme", "ocean"))
    demo_role = session.get("demo_role", "member")
    if demo_role not in DEMO_ROLES:
        demo_role = "member"
    return {"themes": THEMES,
            # Old saved theme names are mapped to their closest new theme
            "theme": theme if theme in THEMES else "ocean",
            "demo_role": demo_role, "demo_roles": DEMO_ROLES,
            "role_navigation": ROLE_NAVIGATION[demo_role],
            "in_health_section": request.endpoint in HEALTH_ENDPOINTS,
            "data_source": session.get("data_source", "sample"),
            "celebrations": session.get("celebrations", "big"),
            "celebrations_chosen": "celebrations" in session}


# Template filter: minutes as "6 h 40 min"
@app.template_filter("hours")
def hours_filter(minutes):
    return format_minutes(minutes)


# Template filter: a list as plain words, like "sleep, steps and unlocks"
@app.template_filter("words")
def words_filter(items):
    return " and ".join([", ".join(items[:-1]), items[-1]]) if len(items) > 1 else "".join(items)


# Template filter: "2026-10-28" as "28 October" (used where the month matters, e.g. chart labels)
@app.template_filter("long_day")
def long_day_filter(text):
    d = date.fromisoformat(text)
    return f"{d.day} {d:%B}"


# Template filter: "2026-10-28" as "Wed 28"
@app.template_filter("day")
def day_filter(text):
    d = date.fromisoformat(text)
    return f"{d:%a} {d.day}"


# Points for one Patterns line chart (600 x 200): values run from y=170 (lowest) up to y=20
# (highest) and days from x=50 to x=580. Also the usual band (usual average plus or minus 10%)
# and where the highlighted last 5 days start.
def trend_chart(values, usual):
    low, high = min(values + [usual * 0.9]), max(values + [usual * 1.1])
    to_y = lambda v: round(170 - (v - low) / ((high - low) or 1) * 150)
    step = 530 / (len(values) - 1)
    xs = [round(50 + i * step) for i in range(len(values))]
    return {"points": " ".join(f"{x},{to_y(v)}" for x, v in zip(xs, values)),
            "band_top": to_y(usual * 1.1), "band_bottom": to_y(usual * 0.9),
            "recent_x": round(xs[-RECENT_DAYS] - step / 2),
            "recent_dots": [(x, to_y(v)) for x, v in zip(xs[-RECENT_DAYS:], values[-RECENT_DAYS:])]}


# The person picked on the home page (a demo person, or someone who signed up), or None.
def current_person():
    pid = session.get("person_id")
    person = dict(session["new_person"]) if pid == NEW_ID and session.get("new_person") else data.get_person(pid)
    if person:
        # Drains and calms the person edited on Me (kept in the session)
        person.update(saved("profile", person["id"], {}))
    return person


# Data-source details explain each demo source's connection type, purpose, and use.
SOURCE_DETAILS = {
    "My phone": ("Operating-system health service", "Show sleep, activity, and screen-use patterns."),
    "Time away from home": ("Operating-system health service", "Notice changes in time away while keeping exact places private."),
    "Smart washing machine": ("API integration", "Notice changes in laundry routines."),
    "Mattress sleep sensor": ("Bluetooth device", "Add an optional sleep signal."),
    "Smart ring": ("Bluetooth device", "Add optional sleep and heart-rate signals."),
    "Glucose monitor (CGM)": ("Bluetooth device", "Show readings from an optional health source."),
    "Smart watch": ("Bluetooth device", "Add optional sleep, activity, or heart-rate signals."),
}


# Paired devices. A real product would connect through each maker's official app or account.
# Here all device data is simulated from the CSV files; only the optional Google Health card
# is a real sign in (see google_health.py), and its data is not used for patterns yet.
GOOGLE_DEVICE = "Google Health (Fitbit, Pixel Watch)"


# A person's devices with their current pairing choices from the session (the CSV never changes)
def devices_for(person):
    choices = session.get("paired", {}).get(person["id"], {})
    devices = [dict(d) for d in person.get("devices") or data.get_devices(person["id"])]
    for d in devices:
        d["paired"] = choices.get(d["device"], d["paired"])
    return devices


# The devices above plus the Google Health card, paired when this browser is signed in to Google
def device_cards(person):
    google = {"device": GOOGLE_DEVICE, "kind": "wearable", "signals": ["sleep", "steps"],
              "connects_through": "Your Google account", "paired": google_health.is_connected()}
    cards = devices_for(person) + [google]
    for source in cards:
        source["connection_type"], source["purpose"] = SOURCE_DETAILS.get(
            source["device"], ("API integration", "Add optional sleep and activity signals."))
        if source["device"] == GOOGLE_DEVICE:
            source["connection_type"] = "API integration"
        source["status"] = "Connected" if source["paired"] else "Not connected"
        source["used_in"] = "Health Patterns, Check In, and appointment preparation when relevant"
    return cards


# Save one pairing choice for this person in the session
def set_paired(person, name, paired):
    choices = session.get("paired", {})
    choices.setdefault(person["id"], {})[name] = paired
    session["paired"] = choices
    # Devices changed, so the saved week and doctor summaries are out of date
    session.get("week", {}).pop(person["id"], None)
    session.get("doctor", {}).pop(person["id"], None)
    session.modified = True


# One person's value saved in the session under "key" (or "default" if nothing is saved yet)
def saved(key, pid, default):
    return session.get(key, {}).get(pid, default)


# Save one person's value in the session under "key"
def save(key, pid, value):
    values = session.get(key, {})
    values[pid] = value
    session[key] = values


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


# ===== My climb =====
# Flag positions on the climb mountain (400 x 300, peak at 200,30): goals go from the bottom
# (first) to the summit (last), zig-zagging up the slope, and the dotted path joins them
def climb_flags(goals):
    flags = []
    for i, g in enumerate(goals):
        y = 255 - i * 210 / max(len(goals) - 1, 1)
        half_width = (y - 30) / 250 * 180
        x = 200 if i == len(goals) - 1 else 200 + (-1 if i % 2 == 0 else 1) * half_width * 0.45
        flags.append({**g, "x": round(x), "y": round(y)})
    return flags


# This week's climb for a person: goals with progress (reached goals first, so the climb fills
# from the bottom), flag positions, the dotted path, and how many flags are reached
def climb_for(person):
    done = session.get("goals_done", {}).get(person["id"], [])
    today_checkins = sum(c["person_id"] == person["id"] for c in session.get("checkins", []))
    added = saved("goals_added", person["id"], [])
    goals = sorted(get_goals(person["id"], done, today_checkins, added), key=lambda g: not g["done"])
    flags = climb_flags(goals)
    reached = sum(g["done"] for g in goals)
    return {"flags": flags, "reached": reached, "total": len(goals),
            "summit": bool(goals) and reached == len(goals),
            "path": " ".join(["200,280"] + [f"{f['x']},{f['y']}" for f in flags]),
            "marker": flags[reached - 1] if reached else None}


# Short cheers for each new flag, picked in turn so the message changes a little each time
FLAG_CHEERS = ["Flag reached!", "Nice work!", "One step higher!"]


# The message when a new flag is reached (not the summit), for example "Nice work! 2 of 5. Keep climbing."
def flag_message(climb):
    cheer = FLAG_CHEERS[climb["reached"] % len(FLAG_CHEERS)]
    return f"{cheer} {climb['reached']} of {climb['total']}. Keep climbing."


# One encouraging line for the climb (never "failed" or "missed")
def climb_message(climb):
    left = climb["total"] - climb["reached"]
    if not climb["total"]:
        return "Add your first goal to start your climb."
    if climb["summit"]:
        return "You reached the summit this week!"
    if climb["reached"] * 2 >= climb["total"]:
        return f"Nice climbing. {left} more flag{'s' if left != 1 else ''} to the summit."
    days = days_left()
    if days:
        return f"Every step counts. You have {days} day{'s' if days != 1 else ''} left."
    return "Every step counts. A new week starts tomorrow."


# ===== Trust circle =====
# The five levels, in dropdown order: a short name and what that person sees, in plain words.
# Someone new starts at "Just in my circle", which shows them nothing.
LEVELS = {
    "none": ("Just in my circle", "Sees nothing."),
    "celebrations": ("Cheers me on", "Sees my celebrations and badges only."),
    "summary": ("Weekly summary", "Sees my week status and summary in words, no numbers, plus celebrations."),
    "wellness": ("Wellness details", "Sees the summary, signal trends and celebrations (for a coach or 360 wellness staff)."),
    "health": ("Health summary", "Sees the doctor visit summary only when I send it."),
}

# Each change in words with no numbers, for the Weekly summary level.
# Time away from home is left out on purpose: it is never shared.
SHARE_WORDS = {"sleep_min": "Sleeping less than usual", "steps": "Walking less than usual",
               "late_screen_min": "More time on the phone late at night",
               "unlocks": "Picking up the phone more often"}

# Units for the numbers in Wellness details (daily averages)
SHARE_UNITS = {"sleep_min": "min", "steps": "steps", "late_screen_min": "min", "unlocks": "unlocks"}


# A person's circle. After the first change it is kept whole in the session (the CSV never changes).
def circle_for(person):
    return [dict(m) for m in saved("circle", person["id"], None) or data.get_circle(person["id"])]


# A person's routines. After the first edit they are kept whole in the session (the CSV never changes).
def routines_for(person):
    return [dict(r) for r in saved("routines", person["id"], None) or data.get_routines(person["id"])]


# Celebrations a circle member may see: the summit this week (if reached) and the badges
def celebrations_for(person):
    climb = climb_for(person)
    lines = ["Reached the summit this week"] if climb["summit"] else []
    badges = SAMPLE_BADGES.get(person["id"], []) + saved("badges", person["id"], [])
    return lines + [f"Badge: {b}" for b in badges]


# Exactly what one member would see at their level, as a list of short lines.
# "Just in my circle" and Health summary see nothing here (Health summary only gets a doctor
# visit summary the person sends). Check in notes and time away from home are never included.
def shared_view(access, patterns, celebrations):
    if access in ["none", "health"]:
        return []
    if access == "celebrations":
        return celebrations
    lines = [f"Week: {patterns['status']}"]
    for c in patterns["changes"]:
        if c["signal"] not in SHARE_WORDS:
            continue
        words = SHARE_WORDS[c["signal"]]
        if access == "wellness":
            unit = SHARE_UNITS[c["signal"]]
            words += f" (usual {c['usual']:,} {unit}, last 5 days {c['recent']:,} {unit})"
        lines.append(words)
    return lines + celebrations


# Home page: choose which demo person to use
@app.route("/")
def choose():
    new_person = [session["new_person"]] if session.get("new_person") else []
    return render_template("choose.html", title="Choose a demo person", people=data.get_people() + new_person)


# Save the chosen person in the session, then open Today
@app.route("/choose/<person_id>")
def choose_person(person_id):
    if data.get_person(person_id) or (person_id == NEW_ID and session.get("new_person")):
        session["person_id"] = person_id
        return redirect(url_for("today"))
    return redirect(url_for("choose"))


# Change only the demo navigation preview; this does not authenticate anyone or grant permissions.
@app.route("/demo/role", methods=["POST"])
def set_demo_role():
    role = request.form.get("role")
    if role in DEMO_ROLES:
        session["demo_role"] = role
        flash(f"Navigation preview: {DEMO_ROLES[role]}. No access permissions changed.")
    next_page = request.form.get("next", "")
    if (not next_page.startswith("/") or next_page.startswith("//") or
            "\\" in next_page or any(char in next_page for char in "\r\n")):
        next_page = url_for("today")
    return redirect(next_page)


# "New to Pair? Get started": always begin at step 1, so every step has its own address
@app.route("/start")
def start_begin():
    return redirect(url_for("start", step=1))


# Sign up (four short screens, then a finish screen):
# 1 Welcome and consent, 2 name and theme, 3 pair your phone, 4 someone you trust (optional), 5 finish.
# GET shows a step; POST (steps 1 to 4 only) saves it and goes to the next step.
# Answers are kept in session["signup"] until step 4, then the new person is made (session only).
@app.route("/start/<int:step>", methods=["GET", "POST"])
def start(step):
    signup = session.get("signup", {})

    # Steps out of order (or a missing name, for example after cookies were cleared) go back to step 1
    if step not in range(1, 6) or (step >= 3 and not signup.get("first_name")):
        return redirect(url_for("start", step=1))

    if request.method == "POST":
        if step == 1:
            signup = {}
        elif step == 2:
            signup["first_name"] = request.form.get("first_name", "").strip()[:30]
            if request.form.get("theme") in THEMES:
                session["theme"] = request.form["theme"]
            if not signup["first_name"]:
                flash("Please write what Pair should call you.")
                session["signup"] = signup
                return redirect(url_for("start", step=2))
        elif step == 3:
            chosen = [] if "skip" in request.form else request.form.getlist("signals")
            signup["signals"] = [signal for signal, _, _, _ in SIGNUP_SIGNALS if signal in chosen]
        elif step == 4:
            name = request.form.get("name", "").strip()[:40]
            access = request.form.get("access") if request.form.get("access") in LEVELS else "none"
            trusted = None if "skip" in request.form or not name else {"name": name, "relationship": "", "access": access, "routines": False}
            create_new_person(signup, trusted)
        elif step == 5:
            # The finish screen has no form; it only links to Today
            return redirect(url_for("today"))
        session["signup"] = signup
        return redirect(url_for("start", step=step + 1))

    return render_template("start.html", title="Get started", step=step, signup=signup,
                           signals=SIGNUP_SIGNALS, levels=LEVELS)


# Make the new person from the sign up answers and pick them. Everything stays in the session;
# anything saved for an earlier new person is cleared first.
def create_new_person(signup, trusted):
    for key in list(session.keys()):
        if isinstance(session[key], dict):
            session[key].pop(NEW_ID, None)
    session["checkins"] = [c for c in session.get("checkins", []) if c["person_id"] != NEW_ID]
    phone = [signal for signal in signup.get("signals", []) if signal != "time out of home"]
    session["new_person"] = {
        "id": NEW_ID, "first_name": signup["first_name"], "last_name": "", "drains": [], "calms": [],
        "devices": [
            {"device": "My phone", "kind": "phone", "connects_through": "Phone sensors and screen time",
             "signals": phone or ["sleep", "steps", "late screen time", "unlocks"], "paired": bool(phone)},
            {"device": "Time away from home", "kind": "phone", "connects_through": "Phone location, shown only as minutes",
             "signals": ["time out of home"], "paired": "time out of home" in signup.get("signals", [])},
        ]}
    save("circle", NEW_ID, [trusted] if trusted else [])
    session["person_id"] = NEW_ID
    session.modified = True


# Full terms: a simple placeholder page for the prototype
@app.route("/terms")
def terms():
    return render_template("terms.html", title="Full terms")


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
    # The Laundry routine, opened from the "No laundry" note (None if this person has none)
    laundry = next((i for i, r in enumerate(routines_for(person)) if r["routine"] == "Laundry"), None)
    patterns = get_patterns(pid, devices_for(person))
    return render_template("today.html", title="Today", person=person, climb=climb_for(person),
                           day=f"{d:%A} {d.day} {d:%B}", patterns=patterns,
                           week=week_text(person, patterns),
                           body_signals=get_body_signals(pid, devices_for(person)),
                           laundry_index=laundry, circle=circle_for(person),
                           last_checkin=checkins[-1] if checkins else None)


# My Plan: show the Jordan demo activities and accepted Health follow-ups through the shared data provider.
@app.route("/my-plan")
def plan():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    records = load_demo_data()
    is_demo_member = f"{person['first_name']} {person['last_name']}".strip() == records["member"]["name"]
    time_filter = request.args.get("time", "today")
    source_filter = request.args.get("source", "all")
    activities = plan_activities(records, data.get_today(), time_filter, source_filter,
                                 session.get("activity_progress", {})) if is_demo_member else []
    return render_template("plan.html", title="My Plan", person=person, activities=activities,
                           time_filter=time_filter if time_filter in ["today", "tomorrow", "this_week", "later"] else "today",
                           source_filter=source_filter if source_filter in ["all", "member", "coach", "health"] else "all",
                           has_demo_records=is_demo_member)


# Return Health fixture records only when the active demo member owns the fixture profile.
def health_demo_records(person):
    """Return only Health records linked to the current sample member's stable app ID."""
    records = load_demo_data()
    return records if person["id"] == records["member"]["application_person_id"] else None


# Health overview: summarize appointments, follow-ups, patterns and connected sources.
@app.route("/health")
def health():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    records = health_demo_records(person)
    if not records:
        return render_template("health.html", title="Health", person=person,
                               has_demo_records=False)
    packets = records["appointment_packets"]
    for packet in packets:
        appointment = datetime.fromisoformat(packet["appointment_on"])
        packet["date_label"] = (f"{appointment:%A}, {appointment:%B} {appointment.day} · "
                                f"{appointment:%I:%M %p}".replace(" 0", " "))
    upcoming = next((packet for packet in packets if packet["status"] == "upcoming"), None)
    return render_template("health.html", title="Health", person=person,
                           upcoming=upcoming, next_steps=records["health_follow_ups"][:2],
                           packet_count=len(packets), patterns=get_patterns(person["id"], devices_for(person)),
                           connected_count=sum(device["paired"] for device in devices_for(person)),
                           has_demo_records=True)


# List the member's reviewed appointment packet records without exposing other members' packets.
@app.route("/health/packets")
def health_packets():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    records = health_demo_records(person)
    return render_template("health_packets.html", title="My Shared Packets", person=person,
                           packets=records["appointment_packets"] if records else [],
                           has_demo_records=bool(records))


# Show one packet only after confirming its member owner and member-reviewed demo state.
@app.route("/health/packets/<packet_id>")
def health_packet(packet_id):
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    records = health_demo_records(person)
    packet = next((item for item in records["appointment_packets"]
                   if item["id"] == packet_id and item["member_id"] == records["member"]["id"]
                   and item["review_status"] in ["member_reviewed_demo_only", "completed_demo_only"]), None) if records else None
    if not packet:
        abort(404)
    recipient = next((item["name"] for item in records["professionals"]
                      if item["id"] == packet["recipient_id"]), "Healthcare professional")
    return render_template("health_packet.html", title="Packet details", packet=packet,
                           recipient=recipient, person=person)


# Show all healthcare follow-up statuses in the Health section.
@app.route("/health/next-steps")
def health_next_steps():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    records = health_demo_records(person)
    return render_template("health_next_steps.html", title="Next Steps", person=person,
                           follow_ups=records["health_follow_ups"] if records else [],
                           has_demo_records=bool(records))


# Activity detail: keep step navigation, presentation choices, and feedback in this demo session.
@app.route("/activity/<activity_id>", methods=["GET", "POST"])
def activity_detail(activity_id):
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    records = load_demo_data()
    if f"{person['first_name']} {person['last_name']}".strip() != records["member"]["name"]:
        abort(404)
    activity = next((item for item in records["activities"] if item["id"] == activity_id), None)
    if not activity:
        abort(404)

    activity_ui = dict(session.get("activity_ui", {}))
    state = dict(activity_ui.get(activity_id, {}))
    try:
        step_number = int(request.values.get("step", state.get("current_step", 1)))
    except ValueError:
        step_number = 1
    step_number = min(max(step_number, 1), len(activity["steps"]))
    progress = dict(session.get("activity_progress", {}))
    activity_progress = dict(progress.get(activity_id, {}))

    if activity_progress.get("status") != "completed":
        activity_progress.update(status="in_progress", next_action=f"Continue with step {step_number}")
    if request.method == "POST":
        action = request.form.get("action", "")
        modes = dict(state.get("step_modes", {}))
        examples = dict(state.get("examples", {}))
        feedback = dict(state.get("feedback", {}))
        step_key = str(step_number)
        if action == "fewer":
            modes[step_key] = "short"
        elif action == "different":
            modes[step_key] = "different"
        elif action == "original":
            modes[step_key] = "original"
        elif action == "example":
            examples[step_key] = not examples.get(step_key, False)
        elif action == "pictures":
            state["pictures"] = not state.get("pictures", True)
        elif action.startswith("feedback:"):
            choice = action.partition(":")[2]
            if choice in ["Easy", "Okay", "Difficult"]:
                feedback[step_key] = choice
                flash(f"Thanks for sharing that this step felt {choice.lower()}.")
        elif action == "break":
            flash("Your place is saved. Take the time you need.")
        elif action == "help":
            flash("Your step is saved. You can open My Circle if you would like support.")
        elif action == "back":
            step_number = max(1, step_number - 1)
        elif action == "next" and step_number < len(activity["steps"]):
            step_number += 1
        elif action == "next":
            activity_progress.update(status="completed", next_action="No next step")
            flash(f"You finished {activity['title']}.")
            progress[activity_id] = activity_progress
            session["activity_progress"] = progress
            today = date.fromisoformat(data.get_today())
            due = date.fromisoformat(activity["due_on"])
            time_filter = ("today" if due == today else "tomorrow" if due == today + timedelta(days=1)
                           else "this_week" if due <= today + timedelta(days=6 - today.weekday()) else "later")
            return redirect(url_for("plan", time=time_filter, source="all"))

        if activity_progress.get("status") != "completed":
            activity_progress["next_action"] = f"Continue with step {step_number}"
        state.update(step_modes=modes, examples=examples, feedback=feedback, current_step=step_number)
        activity_ui[activity_id] = state
        progress[activity_id] = {**activity_progress, "step": step_number}
        session["activity_ui"] = activity_ui
        session["activity_progress"] = progress
        return redirect(url_for("activity_detail", activity_id=activity_id, step=step_number))

    activity_ui[activity_id] = {**state, "current_step": step_number}
    session["activity_ui"] = activity_ui
    progress[activity_id] = {**activity_progress, "step": step_number}
    session["activity_progress"] = progress
    current_step = activity["steps"][step_number - 1]
    mode = state.get("step_modes", {}).get(str(step_number), "original")
    instruction = current_step["instruction"]
    if mode == "short":
        instruction = current_step["short_instruction"]
    elif mode == "different":
        instruction = current_step["different_explanation"]
    return render_template("activity.html", title=activity["title"], activity=activity,
                           step=current_step, step_number=step_number, mode=mode,
                           instruction=instruction, state=state,
                           pictures=state.get("pictures", True))


# Check in screen: pick a mood and add an optional note, then Save (or Skip). After saving, a
# response card compares the mood with what patterns and body signals show (or, if the note has
# emergency words, shows 911 and 988 instead).
@app.route("/checkin", methods=["GET", "POST"])
def checkin():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    pid = person["id"]
    checkins = session.get("checkins", [])
    displays = dict(session.get("checkin_display", {}))
    display = displays.get(pid, "pictures_words")

    if request.method == "POST" and request.form.get("action") == "display":
        choice = request.form.get("display")
        if choice in dict(CHECKIN_DISPLAY):
            displays[pid] = choice
            session["checkin_display"] = displays
            flash("Check-in display preference saved.")
        return redirect(url_for("checkin"))

    # Save: add the check in to the session (demo only, keeps the last 20; it counts toward the
    # weekly Check in goal), work out the response, then show it on this page
    if request.method == "POST" and request.form.get("feeling") in MOODS:
        feeling, note = request.form["feeling"], request.form.get("note", "").strip()[:200]
        help_choice = request.form.get("help_choice", "")
        if help_choice not in {choice["value"] for choice in CHECKIN_HELP}:
            help_choice = ""
        checkins.append({"person_id": pid, "date": data.get_today(),
                         "time": datetime.now().strftime("%H:%M"), "feeling": feeling,
                         "help_choice": help_choice, "note": note})
        session["checkins"] = checkins[-20:]
        devices = devices_for(person)
        response = respond_to_checkin(person, feeling, get_patterns(pid, devices), get_body_signals(pid, devices), note)
        selected_help = next((item for item in CHECKIN_HELP if item["value"] == help_choice), None)
        save("checkin_response", pid, {**response, "mood": feeling,
                                        "help_choice": selected_help})
        return redirect(url_for("checkin"))

    # Show the response once (if there is one), otherwise the form, plus earlier check ins
    response = session.get("checkin_response", {}).pop(pid, None)
    session.modified = True
    mine = [c for c in checkins if c["person_id"] == pid]
    help_by_key = {item["value"]: item for item in CHECKIN_HELP}
    return render_template("checkin.html", title="Check in", feelings=MOODS,
                           help_choices=CHECKIN_HELP, help_by_key=help_by_key,
                           display_options=CHECKIN_DISPLAY, display=display,
                           response=response, checkins=mine)


# Patterns: a 21 day line chart for each signal from a paired device, with the usual range
# shaded, the last 5 days highlighted and one plain sentence above it
@app.route("/patterns")
def patterns():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    trends = get_trends(person["id"], devices_for(person))
    return render_template("patterns.html", title="Health Patterns",
                           trends=[{**t, "chart": trend_chart(t["values"], t["usual"])} for t in trends])


# Coach view (demo): residents who gave someone in their circle the Wellness details level, with
# their week status, number of changes and weekly summary in words (the same view the Weekly
# summary level gets). Time away from home, check in notes and the doctor summary are never shown.
@app.route("/coach")
def coach():
    residents = []
    for p in data.get_people():
        if any(m["access"] == "wellness" for m in circle_for(p)):
            patterns = get_patterns(p["id"], devices_for(p))
            residents.append({"first_name": p["first_name"], "status": patterns["status"],
                              "summary": shared_view("summary", patterns, [])[1:],
                              "celebrations": celebrations_for(p)})
    return render_template("coach.html", title="Coach view", residents=residents)


# Trust circle: one clean list (initials, name, relationship, level chip). Tapping a row opens an
# edit panel; a form at the bottom adds someone new.
@app.route("/circle")
def circle():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    return render_template("circle.html", title="Circle", circle=circle_for(person), levels=LEVELS)


# Save one member's level, relationship and "Can add routines" (the whole circle goes in the session)
@app.route("/circle/save", methods=["POST"])
def circle_save():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    members = circle_for(person)
    member = next((m for m in members if m["name"] == request.form.get("name")), None)
    if member and request.form.get("access") in LEVELS:
        member.update(access=request.form["access"], routines="routines" in request.form,
                      relationship=request.form.get("relationship", "").strip()[:40])
        save("circle", person["id"], members)
        flash(f"Saved. {member['name']}: {LEVELS[member['access']][0]}.")
    return redirect(url_for("circle"))


# Remove one member from the circle
@app.route("/circle/remove", methods=["POST"])
def circle_remove():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    name = request.form.get("name")
    save("circle", person["id"], [m for m in circle_for(person) if m["name"] != name])
    flash(f"{name} removed from your circle.")
    return redirect(url_for("circle"))


# Add someone I trust: only the name is needed; relationship and level are optional
# (a new person starts at "Just in my circle")
@app.route("/circle/add", methods=["POST"])
def circle_add():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    members = circle_for(person)
    name = request.form.get("name", "").strip()[:40]
    access = request.form.get("access") if request.form.get("access") in LEVELS else "none"
    if not name:
        flash("Please add a name.")
    elif any(m["name"] == name for m in members):
        flash(f"{name} is already in your circle.")
    else:
        members.append({"name": name, "relationship": request.form.get("relationship", "").strip()[:40],
                        "access": access, "routines": False})
        save("circle", person["id"], members)
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
                 if m["name"] in request.form.getlist("share") and m["access"] not in ["none", "health"]]
        if names:
            flash(f"Prototype: nothing was really sent. In the real app, {words_filter(names)} would now see their view.")
        else:
            flash("No one was ticked, so nothing was shared.")
        return redirect(url_for("today"))
    patterns = get_patterns(person["id"], devices_for(person))
    celebrations = celebrations_for(person)
    return render_template("share.html", title="Share with my circle", levels=LEVELS,
                           members=[{**m, "view": shared_view(m["access"], patterns, celebrations)} for m in members])


# The old address /doctor opens the Visit companion
@app.route("/doctor")
def doctor():
    return redirect(url_for("visit_start"))


# Get ready for an appointment, step 1: "Who are you seeing?" as large choice cards
@app.route("/visit")
def visit_start():
    if not current_person():
        return redirect(url_for("choose"))
    return render_template("visit_start.html", title="Get ready for an appointment", visits=VISITS)


# The 14 days a visit summary covers (counting back from the demo "today") and the check ins in them
def visit_period(pid):
    end = date.fromisoformat(data.get_today())
    start = end - timedelta(days=13)
    return start, end, [c for c in data.get_checkins(pid) if c["date"] >= start.isoformat()]


# Step 2: the one page summary for this kind of appointment, which the person reviews, then prints
# or sends to a Health summary member. Questions they type are kept in the session.
@app.route("/visit/<visit>", methods=["GET", "POST"])
def visit_page(visit):
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    if visit not in VISITS:
        abort(404)
    pid = person["id"]
    if request.method == "POST":
        save("visit_questions", pid, request.form.get("questions", "").strip()[:1000])
        flash("Your questions are saved.")
        return redirect(url_for("visit_page", visit=visit))

    start, end, checkins = visit_period(pid)
    devices = devices_for(person)
    patterns, body = get_patterns(pid, devices), get_body_signals(pid, devices)
    suggestions = saved("visit_suggestions", pid, None)
    return render_template("visit.html", title="Get ready for an appointment", person=person,
                           visit=visit, visit_label=VISITS[visit]["label"],
                           period=f"{start.day} {start:%B} to {end.day} {end:%B %Y}",
                           patterns=patterns, counts=feeling_counts(checkins),
                           summary=daily_cache("doctor", person, lambda: explain_for_doctor(person, patterns, checkins)),
                           questions=saved("visit_questions", pid, ""),
                           suggestions=suggestions if suggestions and suggestions["visit"] == visit else None,
                           tell=things_to_tell(visit, patterns, body, devices),
                           entries=saved("visit_entries", pid, []),
                           sources=[d["device"] for d in devices if d["paired"]] + ["My own check ins"],
                           contacts=[m["name"] for m in circle_for(person) if m["access"] == "health"])


# Suggest questions for this kind of appointment (AI, or 3 general questions for the visit type)
@app.route("/visit/<visit>/suggest", methods=["POST"])
def visit_suggest(visit):
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    if visit not in VISITS:
        abort(404)
    pid = person["id"]
    _, _, checkins = visit_period(pid)
    devices = devices_for(person)
    result = suggest_questions(person, visit, get_patterns(pid, devices), get_body_signals(pid, devices),
                               feeling_counts(checkins)["moods"])
    save("visit_suggestions", pid, {**result, "visit": visit})
    return redirect(url_for("visit_page", visit=visit))


# Add one suggested question to "Questions I want to ask" (each on its own line, still editable)
@app.route("/visit/<visit>/add-question", methods=["POST"])
def visit_add_question(visit):
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    question = request.form.get("question", "").strip()[:200]
    current = saved("visit_questions", person["id"], "")
    if question and question not in current:
        save("visit_questions", person["id"], (current + "\n" + question).strip()[:1000])
        flash("Question added.")
    return redirect(url_for("visit_page", visit=visit if visit in VISITS else "other"))


# Entered by me: add something from another app or from memory (a label and a value), or remove
# one; at most 10. Kept apart from device readings, which can never be edited.
@app.route("/visit/<visit>/entry", methods=["POST"])
def visit_entry(visit):
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    entries = saved("visit_entries", person["id"], [])
    label = request.form.get("label", "").strip()[:40]
    value = request.form.get("value", "").strip()[:40]
    remove = request.form.get("remove", "")
    if remove.isdigit() and int(remove) < len(entries):
        entries.pop(int(remove))
    elif label and value and len(entries) < 10:
        entries.append({"label": label, "value": value})
    else:
        flash("Please add both a label and a value.")
    save("visit_entries", person["id"], entries)
    return redirect(url_for("visit_page", visit=visit if visit in VISITS else "other"))


# Send to my health contact: only ticked Health summary members; a confirmation only,
# nothing is really sent in the prototype
@app.route("/visit/<visit>/send", methods=["POST"])
def visit_send(visit):
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    names = [m["name"] for m in circle_for(person)
             if m["access"] == "health" and m["name"] in request.form.getlist("send")]
    if names:
        flash(f"Prototype: nothing was really sent. In the real app, {words_filter(names)} would get this summary.")
    else:
        flash("No one was ticked, so nothing was sent.")
    return redirect(url_for("visit_page", visit=visit if visit in VISITS else "other"))


# Not sure who to see? The person types how they have been feeling. Emergency words are checked
# first by rules (then only 911 and 988 are shown); otherwise 1 to 3 kinds of professional.
@app.route("/visit/not-sure", methods=["GET", "POST"])
def visit_not_sure():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    text = request.form.get("feelings", "").strip()[:500]
    urgent, result = False, None
    if request.method == "POST" and text:
        if is_urgent(text):
            urgent = True
        else:
            devices = devices_for(person)
            result = suggest_professionals(person, text, get_patterns(person["id"], devices),
                                           get_body_signals(person["id"], devices))
    return render_template("visit_not_sure.html", title="Not sure who to see?", text=text,
                           urgent=urgent, result=result, visits=VISITS)


# My climb this week: the mountain with one flag per goal, the goal list, the message and My badges.
# A small celebration when more flags are reached than at the last visit (after Done, a finished
# routine or a check in); the first time the summit is reached this week, a badge is added and the
# full celebration plays instead. With only one goal, that goal is the summit.
@app.route("/climb")
def climb():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    pid = person["id"]
    climb = climb_for(person)
    all_badges = session.get("badges", {})
    badge = f"Summit · {week_name()}"
    new_badge = climb["summit"] and badge not in all_badges.get(pid, [])
    if new_badge:
        all_badges[pid] = all_badges.get(pid, []) + [badge]
        session["badges"] = all_badges
    new_flag = climb["reached"] > saved("climb_seen", pid, climb["reached"]) and not climb["summit"]
    save("climb_seen", pid, climb["reached"])
    routine_index = {r["routine"]: i for i, r in enumerate(routines_for(person))}
    return render_template("climb.html", title="My climb this week", climb=climb, routine_index=routine_index,
                           message=flag_message(climb) if new_flag else climb_message(climb),
                           new_badge=new_badge, new_flag=new_flag,
                           badges=SAMPLE_BADGES.get(pid, []) + all_badges.get(pid, []))


# Done button for a manual "done" goal (saved in the session for this person)
@app.route("/climb/done", methods=["POST"])
def climb_done():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    name = request.form.get("goal")
    added = saved("goals_added", person["id"], [])
    if name in added or any(g["goal"] == name and g["rule"] == "done" for g in data.get_goals(person["id"])):
        all_done = session.get("goals_done", {})
        all_done[person["id"]] = list(set(all_done.get(person["id"], []) + [name]))
        session["goals_done"] = all_done
    return redirect(url_for("climb"))


# Add a goal on My climb: only a name; it is reached by tapping Done (at most 8 added goals)
@app.route("/climb/add", methods=["POST"])
def climb_add():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    name = request.form.get("goal", "").strip()[:40]
    added = saved("goals_added", person["id"], [])
    if name and name not in added and len(added) < 8:
        save("goals_added", person["id"], added + [name])
        flash(f"Goal added: {name}.")
    return redirect(url_for("climb"))


# My routines: each routine with who added it; tapping one opens its picture steps
@app.route("/routines")
def routines():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    return render_template("routines.html", title="My routines", routines=routines_for(person))


# Picture steps for one routine, shown one at a time by static/js/steps.js. Finishing the last
# step posts to routine_finish.
@app.route("/routines/<int:index>")
def routine_steps(index):
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    routines = routines_for(person)
    if index >= len(routines):
        abort(404)
    routine = routines[index]
    if not routine["steps"]:
        flash("This routine has no steps yet. Add the steps you use.")
        return redirect(url_for("routine_edit", index=index))
    return render_template("steps.html", title=routine["routine"], person=person, routine=routine, index=index)


# Finishing a routine marks the weekly goal with the same name as done, then shows My climb
# (which celebrates if that was the last flag). Without a matching goal, go back to My routines.
@app.route("/routines/<int:index>/finish", methods=["POST"])
def routine_finish(index):
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    routines = routines_for(person)
    if index >= len(routines):
        abort(404)
    name = routines[index]["routine"]
    flash(f"You finished {name}. Nice work.")
    if any(g["goal"] == name and g["rule"] == "routine" for g in data.get_goals(person["id"])):
        save("goals_done", person["id"], list(set(saved("goals_done", person["id"], []) + [name])))
        return redirect(url_for("climb"))
    return redirect(url_for("routines"))


# Edit steps: add, remove or move steps up and down, suggest steps with AI, and choose who added
# the routine. Nothing is saved until Save. "Added by" only lists the person ("me") and circle
# members marked "Can add routines". In a real product a trusted person would edit the routine
# from their own login; this demo lets the person pick who added it.
@app.route("/routines/<int:index>/edit", methods=["GET", "POST"])
def routine_edit(index):
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    routines = routines_for(person)
    if index >= len(routines):
        abort(404)
    routine = routines[index]
    helpers = ["me"] + [m["name"] for m in circle_for(person) if m["routines"]]
    steps, added_by, message, source = routine["steps"], routine["added_by"], None, None

    if request.method == "POST":
        steps = [s.strip()[:80] for s in request.form.getlist("steps")][:12]
        added_by = request.form.get("added_by")
        what, _, number = request.form.get("action", "").partition(":")
        i = int(number) if number.isdigit() else -1
        if what == "up" and 0 < i < len(steps):
            steps[i - 1], steps[i] = steps[i], steps[i - 1]
        elif what == "down" and 0 <= i < len(steps) - 1:
            steps[i], steps[i + 1] = steps[i + 1], steps[i]
        elif what == "remove" and 0 <= i < len(steps):
            steps.pop(i)
        elif what == "add":
            steps.append("")
        elif what == "suggest":
            suggestion = suggest_steps(routine["routine"])
            steps, source = suggestion["steps"], suggestion["source"]
            message = None if steps else "Write the steps you use."
        elif what == "save":
            steps = [s for s in steps if s]
            if steps:
                routine.update(steps=steps, added_by=added_by if added_by in helpers else "me")
                save("routines", person["id"], routines)
                flash(f"{routine['routine']} saved.")
                return redirect(url_for("routines"))
            message = "Please write at least one step."

    return render_template("routine_edit.html", title=f"Edit {routine['routine']}", routine=routine,
                           steps=steps or [""], helpers=helpers,
                           added_by=added_by if added_by in helpers else "me",
                           message=message, source=source)


# Me: a profile card (name, what drains and calms the person, with Edit) and four link cards
@app.route("/me")
def me():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    return render_template("me.html", title="Me", person=person)


# Edit what drains and calms the person: comma separated, up to 8 of each, saved in the session.
# The saved week summary is cleared so the gentle step uses the new calms.
@app.route("/me/edit", methods=["POST"])
def me_edit():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    split = lambda text: [w.strip()[:30] for w in text.split(",") if w.strip()][:8]
    save("profile", person["id"], {"drains": split(request.form.get("drains", "")),
                                   "calms": split(request.form.get("calms", ""))})
    session.get("week", {}).pop(person["id"], None)
    flash("Saved.")
    return redirect(url_for("me"))


# My body signals: one card per paired vital (resting heart rate, glucose) with a 21 day line
# (the same chart as Patterns), a plain sentence and where it comes from. Read only.
@app.route("/body")
def body():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    signals = get_body_signals(person["id"], devices_for(person))
    return render_template("body.html", title="My body signals",
                           signals=[{**v, "chart": trend_chart(v["values"], v["usual"])} for v in signals])


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


# Connected Data Sources: list each source by connection type and current status.
@app.route("/devices")
def devices():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    cards = device_cards(person)
    return render_template("devices.html", title="Connected Data Sources", google_name=GOOGLE_DEVICE,
                           paired=[d for d in cards if d["paired"]],
                           available=[d for d in cards if not d["paired"]],
                           connection_types=["Bluetooth device", "Operating-system health service", "API integration"])


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


# Settings: how big the summit celebration is (Big = confetti, Calm = soft glow, Off = message only)
@app.route("/celebrations", methods=["POST"])
def set_celebrations():
    if request.form.get("celebrations") in CELEBRATIONS:
        session["celebrations"] = request.form["celebrations"]
        flash(f"Celebrations set to {CELEBRATIONS[session['celebrations']]}.")
    return redirect(url_for("settings"))


# Save the theme picked on Settings (the cards only preview it until Save is pressed)
@app.route("/theme", methods=["POST"])
def save_theme():
    if request.form.get("theme") in THEMES:
        session["theme"] = request.form["theme"]
        flash(f"Theme saved: {request.form['theme'].capitalize()}.")
    return redirect(url_for("settings"))


# Start the app in debug mode when this file is run directly
if __name__ == "__main__":
    app.run(debug=True)
