import json
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

# The role cards select a sample workspace; authorization still belongs to the member's explicit sharing choices.
DEMO_ROLES = {"member": "Pair member", "coach": "Coach or educator",
              "healthcare": "Healthcare professional", "trusted": "Trusted person",
              "admin": "Organization administrator"}
ROLE_NAVIGATION = {
    "member": [
        ("Home", "today", "sun", ["today"]),
        ("My Plan", "plan", "calendar", ["plan"]),
        ("Check In", "checkin", "check", ["checkin"]),
        ("Health", "health", "heart", ["health", "health_packets", "health_packet",
                                            "health_next_steps", "health_follow_up_action", "patterns", "body", "devices",
                                            "pair_device", "stop_pairing", "visit_start", "visit_page",
                                            "visit_suggest", "visit_add_question", "visit_entry", "visit_review",
                                            "visit_packet_review", "visit_send", "visit_not_sure"]),
        ("My Circle", "circle", "people", ["circle"]),
        ("Me", "me", "user", ["me", "settings", "climb",
                                "climb_done", "climb_add", "routines", "routine_steps", "routine_edit"]),
    ],
    "coach": [
        ("Overview", "coach", "wave", ["coach"]),
        ("Learners", "coach_learners", "people", ["coach_learners", "coach_learner", "coach_assign"]),
        ("Activity Library", "coach_library", "book", ["coach_library"]),
        ("Coach Settings", "coach_settings", "gear", ["coach_settings"]),
    ],
    "healthcare": [
        ("Shared Appointment Packets", "professional_packets", "clipboard",
         ["professional_packets", "professional_packet"]),
        ("Proposed Next Steps", "professional_next_steps", "flag", ["professional_next_steps"]),
        ("Professional Settings", "professional_settings", "gear", ["professional_settings"]),
    ],
    "trusted": [
        ("Shared with Me", "trusted", "heart", ["trusted"]),
        ("Send Encouragement", "trusted_encouragement", "wave", ["trusted_encouragement"]),
        ("Support Settings", "trusted_settings", "gear", ["trusted_settings"]),
    ],
    "admin": [
        ("Accounts", None, "people", []), ("Verify Roles", None, "check", []),
        ("Invitations", None, "clipboard", []), ("Org Settings", "admin_settings", "home", ["admin_settings"]),
        ("Access Logs", None, "wave", []), ("Templates", None, "book", []),
    ],
}
ROLE_IDENTITIES = {"member": "Jordan Reyes", "coach": "Dana Brooks",
                   "healthcare": "Dr. Priya Patel", "trusted": "Marisol Reyes",
                   "admin": "Alex Morgan"}
ROLE_HOME_ENDPOINTS = {"member": "today", "coach": "coach",
                       "healthcare": "professional_packets", "trusted": "trusted",
                       "admin": "admin_settings"}
ROLE_CARDS = [
    {"key": "member", "label": "Pair member", "identity": "Jordan Reyes", "icon": "user",
     "description": "Explore your plan, check in, prepare for health visits, and choose what to share."},
    {"key": "coach", "label": "Coach or educator", "identity": "Dana Brooks", "icon": "book",
     "description": "Review shared learning progress and assign activities from a learner profile."},
    {"key": "healthcare", "label": "Healthcare professional", "identity": "Dr. Priya Patel", "icon": "medical",
     "description": "Review appointment packets that members choose to share with you."},
    {"key": "trusted", "label": "Trusted person", "identity": "Marisol Reyes", "icon": "people",
     "description": "See member-shared summaries and offer encouragement."},
    {"key": "admin", "label": "Organization administrator", "identity": "Alex Morgan", "icon": "gear",
     "description": "Manage organization settings and access records, not private member content."},
]
# Route ownership keeps demo workspaces separate without presenting demo switching as authentication.
ROLE_ENDPOINTS = {
    "member": {"choose_person", "today", "plan", "health", "health_packets", "health_packet",
               "health_next_steps", "health_follow_up_action", "activity_detail", "checkin", "patterns",
               "circle", "circle_save", "circle_remove", "circle_add", "circle_revoke_share", "share",
               "doctor", "visit_start", "visit_page", "visit_suggest", "visit_add_question", "visit_entry",
               "visit_review", "visit_packet_review", "visit_send", "visit_not_sure", "climb", "climb_done",
               "climb_add", "routines", "routine_steps", "routine_finish", "routine_edit", "me", "me_edit",
               "body", "settings_export", "settings_delete_data", "devices", "pair_device",
               "stop_pairing", "set_celebrations", "save_theme", "google.login", "google.callback",
               "google.disconnect", "google.test"},
    "coach": {"coach", "coach_learners", "coach_learner", "coach_assign", "coach_library", "coach_settings"},
    "healthcare": {"professional_packets", "professional_packet", "professional_next_steps",
                   "professional_settings"},
    "trusted": {"trusted", "trusted_encouragement", "trusted_settings"},
    "admin": {"admin_settings"},
}
HEALTH_ENDPOINTS = {
    "health", "health_packets", "health_packet", "health_next_steps", "health_follow_up_action",
    "patterns", "body",
    "devices", "pair_device", "stop_pairing", "visit_start", "visit_page", "visit_suggest",
    "visit_add_question", "visit_entry", "visit_review", "visit_packet_review", "visit_send",
    "visit_not_sure",
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
            "role_identity": ROLE_IDENTITIES[demo_role],
            "role_home": ROLE_HOME_ENDPOINTS[demo_role],
            "public_view": request.endpoint in {"choose", "signin", "forgot_password",
                                                 "organization_signin", "start_begin", "start", "terms"},
            "in_health_section": request.endpoint in HEALTH_ENDPOINTS,
            "data_source": session.get("data_source", "sample"),
            "celebrations": session.get("celebrations", "big"),
            "member_preferences": member_preferences(session.get("person_id")),
            "celebrations_chosen": "celebrations" in session}


# Redirect a direct cross-role route request to the selected demo workspace with a clear notice.
@app.before_request
def enforce_demo_workspace():
    endpoint = request.endpoint
    required_role = next((role for role, endpoints in ROLE_ENDPOINTS.items() if endpoint in endpoints), None)
    if not required_role:
        return None
    active_role = session.get("demo_role", "member")
    if active_role not in DEMO_ROLES:
        active_role = "member"
    if endpoint == "trusted" and request.method == "GET" and request.args.get("preview") == "member" and active_role == "member":
        return None
    if active_role != required_role:
        flash("That page belongs to another demonstration workspace. Switch view to explore it; this is not sign-in or authorization.")
        return redirect(url_for(ROLE_HOME_ENDPOINTS[active_role]))
    return None


# Return this member's accessible display choices with calm defaults.
def member_preferences(person_id):
    preferences = session.get("member_preferences", {}).get(person_id, {})
    return {"density": preferences.get("density", "comfortable"),
            "picture_preference": preferences.get("picture_preference",
                                                   session.get("checkin_display", {}).get(person_id, "pictures_words")),
            "read_aloud": preferences.get("read_aloud", True),
            "speech_rate": preferences.get("speech_rate", "1")}


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
DEMO_HEALTHCARE_PROFESSIONAL_ID = "health-priya"


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
    "health": ("Health summary", "May receive an appointment packet only after I review and send it."),
}
CIRCLE_TYPES = {"coach": "Coach", "healthcare": "Healthcare professional",
                "family": "Family member", "friend": "Friend"}
ACCESS_BY_TYPE = {
    "coach": ["none", "celebrations", "summary", "wellness"],
    "healthcare": ["none", "health"],
    "family": ["none", "celebrations", "summary"],
    "friend": ["none", "celebrations", "summary"],
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
    members = [dict(m) for m in saved("circle", person["id"], None) or data.get_circle(person["id"])]
    for member in members:
        relationship = member.get("relationship", "").lower()
        if member.get("member_type") not in CIRCLE_TYPES:
            if member.get("access") == "health" or "doctor" in relationship or "health" in relationship:
                member["member_type"] = "healthcare"
            elif "coach" in relationship or "fitness" in relationship:
                member["member_type"] = "coach"
            elif relationship in ["family", "mother", "father", "sibling"] or member["name"].lower() in ["mom", "dad"]:
                member["member_type"] = "family"
            else:
                member["member_type"] = "friend"
    return members


# Remove a shared snapshot when the member changes or revokes that person's permission.
def clear_circle_snapshot(person_id, name):
    snapshots = session.get("circle_shared_snapshots", {})
    person_snapshots = snapshots.get(person_id, {})
    person_snapshots.pop(name, None)
    snapshots[person_id] = person_snapshots
    session["circle_shared_snapshots"] = snapshots


# Return only one-time snapshots explicitly shared with a family member or friend.
def trusted_shared_contacts(person):
    snapshots = session.get("circle_shared_snapshots", {}).get(person["id"], {})
    contacts = []
    for member in circle_for(person):
        snapshot = snapshots.get(member["name"])
        if (snapshot and member["member_type"] in ["family", "friend"]
                and member["access"] in ["summary", "celebrations"]
                and snapshot["access"] == member["access"]):
            contacts.append({**member, "snapshot": snapshot})
    return contacts


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


# Entry page: introduce Pair and show the five distinct demonstration workspaces.
@app.route("/")
def choose():
    return render_template("choose.html", title="Explore Pair", role_cards=ROLE_CARDS)


# Keep the old member URL for compatibility, but never offer Maya or Theo as member entry accounts.
@app.route("/choose/<person_id>")
def choose_person(person_id):
    primary_id = load_demo_data()["member"]["application_person_id"]
    if person_id == primary_id or (person_id == NEW_ID and session.get("new_person")):
        session["person_id"] = person_id
        session["demo_role"] = "member"
        return redirect(url_for("today"))
    flash("Maya and Theo are sample learners inside authorized staff workspaces, not member entry accounts.")
    return redirect(url_for("choose"))


# Select a sample workspace and return to that role's own landing page in this demonstration.
@app.route("/demo/role", methods=["POST"])
def set_demo_role():
    role = request.form.get("role")
    if role in DEMO_ROLES:
        session["demo_role"] = role
        if role == "member":
            session["person_id"] = load_demo_data()["member"]["application_person_id"]
        flash(f"Demo view: {ROLE_IDENTITIES[role]} · {DEMO_ROLES[role]}. This does not verify identity or grant access to real member information.")
        return redirect(url_for(ROLE_HOME_ENDPOINTS[role]))
    flash("Choose one of the available demonstration views.")
    return redirect(url_for("choose"))


# Show the prototype sign-in choices without sending or validating the entered demo fields.
@app.route("/signin")
def signin():
    return render_template("signin.html", title="Sign in to Pair")


# Explain that password reset is not connected in this demonstration.
@app.route("/forgot-password")
def forgot_password():
    return render_template("forgot_password.html", title="Forgot password")


# Explain that partner authentication requires an approved organization identity provider.
@app.route("/signin/organization")
def organization_signin():
    return render_template("organization_signin.html", title="Organization sign-in")


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
    session["demo_role"] = "member"
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
@app.route("/my-plan", methods=["GET", "POST"])
def plan():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    if request.method == "POST" and request.form.get("action") == "pace":
        pace = request.form.get("pace")
        if pace in ["one_at_a_time", "full_day"]:
            choices = session.get("plan_pace", {})
            choices[person["id"]] = pace
            session["plan_pace"] = choices
            flash("My Plan display preference saved.")
        return redirect(url_for("plan", time=request.form.get("time", "today"),
                                source=request.form.get("source", "all")))
    records = load_demo_data()
    is_demo_member = person["id"] == records["member"]["application_person_id"]
    assigned = coach_learner_activities(person["id"])
    records = {**records,
               "activities": records["activities"] + assigned if is_demo_member else assigned,
               "health_follow_ups": health_follow_ups_for(person, records) if is_demo_member else []}
    has_activities = is_demo_member or bool(assigned)
    time_filter = request.args.get("time", "today")
    source_filter = request.args.get("source", "all")
    activities = plan_activities(records, data.get_today(), time_filter, source_filter,
                                 session.get("activity_progress", {})) if has_activities else []
    pace = session.get("plan_pace", {}).get(person["id"], "one_at_a_time")
    return render_template("plan.html", title="My Plan", person=person, activities=activities,
                           pace=pace if pace in ["one_at_a_time", "full_day"] else "one_at_a_time",
                           time_filter=time_filter if time_filter in ["today", "tomorrow", "this_week", "later"] else "today",
                           source_filter=source_filter if source_filter in ["all", "member", "coach", "health"] else "all",
                           has_demo_records=has_activities)


# Return Health fixture records only when the active demo member owns the fixture profile.
def health_demo_records(person):
    """Return only Health records linked to the current sample member's stable app ID."""
    records = load_demo_data()
    return records if person["id"] == records["member"]["application_person_id"] else None


# Apply this member's session-only decisions to their simulated Health follow-up actions.
def health_follow_ups_for(person, records=None):
    records = records or health_demo_records(person)
    if not records:
        return []
    saved_states = session.get("health_action_states", {}).get(person["id"], {})
    proposals = session.get("professional_proposals", {}).get(person["id"], [])
    actions = records["health_follow_ups"] + proposals
    return [{**action,
             "status": saved_states.get(action["id"], {}).get("status", action["status"]),
             "member_question": saved_states.get(action["id"], {}).get("question", ""),
             "action_type_label": action.get("action_type", "other_instruction").replace("_", " ").capitalize()}
            for action in actions]


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
                           upcoming=upcoming, next_steps=health_follow_ups_for(person, records)[:2],
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


# Return only member-reviewed packets sent to this demo professional within their authorization period.
def professional_authorized_packets():
    records = load_demo_data()
    today = data.get_today()
    return [packet for packet in records["appointment_packets"]
            if packet["member_id"] == records["member"]["id"]
            and packet["recipient_id"] == DEMO_HEALTHCARE_PROFESSIONAL_ID
            and packet["review_status"] == "member_reviewed_demo_only"
            and packet.get("authorization_starts_on", "0000-00-00") <= today <= packet["access_expires_on"]]


# List new member-shared packets that are still inside their authorization period.
@app.route("/professional/packets")
def professional_packets():
    records = load_demo_data()
    packets = professional_authorized_packets()
    professional = next((item for item in records["professionals"]
                         if item["id"] == DEMO_HEALTHCARE_PROFESSIONAL_ID), None)
    return render_template("professional_packets.html", title="Shared Appointment Packets",
                           packets=packets, member=records["member"], professional=professional,
                           today=data.get_today())


# Show only the contents and preferences included in one currently authorized packet.
@app.route("/professional/packets/<packet_id>")
def professional_packet(packet_id):
    packet = next((item for item in professional_authorized_packets() if item["id"] == packet_id), None)
    if not packet:
        abort(404)
    records = load_demo_data()
    member = records["member"]
    professional = next((item for item in records["professionals"]
                         if item["id"] == DEMO_HEALTHCARE_PROFESSIONAL_ID), None)
    return render_template("professional_packet.html", title="Packet Detail", packet=packet,
                           member=member, professional=professional, today=data.get_today())


# Show actions tied to currently authorized packets and accept new professional proposals.
@app.route("/professional/next-steps", methods=["GET", "POST"])
def professional_next_steps():
    packets = professional_authorized_packets()
    packet_ids = {packet["id"] for packet in packets}
    records = load_demo_data()
    member = data.get_person(records["member"]["application_person_id"])
    if request.method == "POST":
        packet_id = request.form.get("packet_id", "")
        packet = next((item for item in packets if item["id"] == packet_id), None)
        action_type = request.form.get("action_type", "")
        instruction = request.form.get("instruction", "").strip()[:240]
        supporting_detail = request.form.get("supporting_detail", "").strip()[:500]
        due_on = request.form.get("due_on", "").strip()
        try:
            if due_on:
                date.fromisoformat(due_on)
        except ValueError:
            due_on = "invalid"
        if not packet or action_type not in ["prescription_pickup", "test", "referral",
                                             "follow_up_appointment", "other_instruction"]:
            abort(403)
        if not instruction or not supporting_detail or due_on == "invalid":
            flash("Add clear instructions and supporting details. The due date is optional.")
            return redirect(url_for("professional_next_steps"))
        proposals = session.get("professional_proposals", {})
        member_proposals = proposals.get(member["id"], [])
        step = {"id": f"professional-step-{len(member_proposals) + 1}", "packet_id": packet_id,
                "member_id": packet["member_id"], "source_id": DEMO_HEALTHCARE_PROFESSIONAL_ID,
                "source_name": "Dr. Priya Patel", "action_type": action_type,
                "instruction": instruction, "due_on": due_on, "status": "proposed",
                "supporting_detail": supporting_detail, "estimated_minutes": 10}
        proposals[member["id"]] = member_proposals + [step]
        session["professional_proposals"] = proposals
        flash("Proposed next step saved in the demo. The member can review it in Health.")
        return redirect(url_for("professional_next_steps"))
    actions = [item for item in health_follow_ups_for(member, records)
               if item.get("packet_id") in packet_ids]
    return render_template("professional_next_steps.html", title="Proposed Next Steps",
                           packets=packets, actions=actions)


# Save professional display preferences without changing any packet authorization.
@app.route("/professional/settings", methods=["GET", "POST"])
def professional_settings():
    settings = session.get("professional_settings", {"review_reminders": "weekly"})
    if request.method == "POST":
        reminders = request.form.get("review_reminders")
        if reminders in ["daily", "weekly", "off"]:
            settings["review_reminders"] = reminders
            session["professional_settings"] = settings
            flash("Professional settings saved in this demo.")
        return redirect(url_for("professional_settings"))
    return render_template("professional_settings.html", title="Professional Settings", settings=settings)


# Let the member accept, question, or decline one of their own proposed Health actions.
@app.route("/health/next-steps/<action_id>", methods=["POST"])
def health_follow_up_action(action_id):
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    records = health_demo_records(person)
    action = next((item for item in health_follow_ups_for(person, records)
                   if item["id"] == action_id), None) if records else None
    if not action:
        abort(404)
    states = session.get("health_action_states", {}).get(person["id"], {})
    current_status = states.get(action_id, {}).get("status", action["status"])
    if current_status in ["accepted", "declined"]:
        flash("This follow-up already has a final choice.")
        return redirect(url_for("health_next_steps", _anchor=action_id))
    choice = request.form.get("choice")
    if choice == "ask_question":
        question = request.form.get("question", "").strip()[:500]
        if not question:
            flash("Write your question before saving it.")
            return redirect(url_for("health_next_steps", _anchor=action_id))
        status, saved_question = "question_asked", question
        message = "Your question is saved in this demo. It was not sent to the healthcare professional."
    elif choice == "accept":
        status, saved_question, message = "accepted", "", "You accepted this step. It now appears in My Plan."
    elif choice == "decline":
        status, saved_question, message = "declined", "", "You declined this step. It will not appear in My Plan."
    else:
        abort(400)
    states[action_id] = {"status": status, "question": saved_question}
    all_states = session.get("health_action_states", {})
    all_states[person["id"]] = states
    session["health_action_states"] = all_states
    flash(message)
    return redirect(url_for("health_next_steps", _anchor=action_id))


# Show all healthcare follow-up statuses in the Health section.
@app.route("/health/next-steps")
def health_next_steps():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    records = health_demo_records(person)
    return render_template("health_next_steps.html", title="Next Steps", person=person,
                           follow_ups=health_follow_ups_for(person, records),
                           has_demo_records=bool(records))


# Activity detail: keep step navigation, presentation choices, and feedback in this demo session.
@app.route("/activity/<activity_id>", methods=["GET", "POST"])
def activity_detail(activity_id):
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    records = load_demo_data()
    if person["id"] == records["member"]["application_person_id"]:
        assigned = session.get("coach_assignments", {}).get(person["id"], [])
        activities = records["activities"] + assigned
    else:
        activities = session.get("coach_assignments", {}).get(person["id"], [])
    activity = next((item for item in activities if item["id"] == activity_id), None)
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
    preferences = member_preferences(person["id"])
    return render_template("activity.html", title=activity["title"], activity=activity,
                           step=current_step, step_number=step_number, mode=mode,
                           instruction=instruction, state=state,
                           pictures=state.get("pictures", preferences["picture_preference"] != "words_only"),
                           read_aloud=preferences["read_aloud"])


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
    display = displays.get(pid, member_preferences(pid)["picture_preference"])

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
    presentation = {
        "sleep_min": ("Sleep", "sleep", "My phone · sleep estimate"),
        "steps": ("Daily steps", "footprints", "My phone · step count"),
        "late_screen_min": ("Phone time late at night", "phone", "My phone · screen-time estimate"),
        "unlocks": ("Phone pickups", "phone", "My phone · pickup count"),
        "time_out_min": ("Time away from home", "home", "My phone · minutes only; no map"),
    }
    trends = []
    for trend in get_trends(person["id"], devices_for(person)):
        name, pictogram, source = presentation[trend["signal"]]
        sentence = trend["sentence"].replace(trend["name"] + ":", name + ":", 1)
        trends.append({**trend, "name": name, "pictogram": pictogram,
                       "source_label": source, "sentence": sentence,
                       "chart": trend_chart(trend["values"], trend["usual"])})
    checkins = [{"mood": str(item.get("feeling", item.get("mood", "Okay"))).capitalize(),
                 "date": item.get("date", data.get_today())}
                for item in data.get_checkins(person["id"])]
    checkins += [{"mood": item["feeling"], "date": item["date"]}
                 for item in session.get("checkins", []) if item.get("person_id") == person["id"]]
    checkins = sorted(checkins, key=lambda item: item["date"])[-4:]
    return render_template("patterns.html", title="Health Patterns",
                           trends=trends, checkins=checkins, person=person)


# Return only people who granted the demo's activity and learning preference sharing level.
def coach_shared_learners():
    return [person for person in data.get_people()
            if any(member["access"] == "wellness" for member in circle_for(person))]


# Add activity-only counts to each consented learner row.
def coach_learner_summaries():
    progress = session.get("activity_progress", {})
    summaries = []
    for learner in coach_shared_learners():
        activities = coach_learner_activities(learner["id"])
        completed = sum(progress.get(item["id"], {}).get("status", item["status"]) == "completed"
                        for item in activities)
        summaries.append({**learner, "activity_count": len(activities), "completed_count": completed})
    return summaries


# Return reusable activities from the library and coach-created demo templates.
def coach_library_items():
    records = load_demo_data()
    samples = [item for item in records["activities"] if item["source"] == "coach"]
    return samples + session.get("coach_activity_library", [])


# Return activities assigned to one learner from fixtures and this demo session.
def coach_learner_activities(learner_id):
    records = load_demo_data()
    samples = [item for item in records["activities"] if item.get("assigned_to") == learner_id]
    return samples + session.get("coach_assignments", {}).get(learner_id, [])


# Coach Overview shows activity-only counts for learners who shared this demo view.
@app.route("/coach")
def coach():
    learners = coach_learner_summaries()
    total_assignments = sum(p["activity_count"] for p in learners)
    return render_template("coach.html", title="Coach Overview", learners=learners,
                           assigned_count=total_assignments,
                           library_count=len(coach_library_items()),
                           active_count=sum(p["activity_count"] - p["completed_count"] for p in learners))


# List learners who shared activity progress and learning preferences with a coach.
@app.route("/coach/learners")
def coach_learners():
    return render_template("coach_learners.html", title="Learners", learners=coach_learner_summaries())


# Open one shared learner profile before the coach can assign an activity.
@app.route("/coach/learners/<learner_id>")
def coach_learner(learner_id):
    learner = next((p for p in coach_shared_learners() if p["id"] == learner_id), None)
    if not learner:
        abort(404)
    opened = session.get("coach_opened_learners", [])
    if learner_id not in opened:
        opened.append(learner_id)
        session["coach_opened_learners"] = opened
    progress = session.get("activity_progress", {})
    ui_states = session.get("activity_ui", {})
    activities = []
    for item in coach_learner_activities(learner_id):
        state = progress.get(item["id"], {})
        ui = ui_states.get(item["id"], {})
        activities.append({**item, "status": state.get("status", item["status"]),
                           "next_action": state.get("next_action", item["next_action"]),
                           "feedback": list(ui.get("feedback", {}).values())})
    records = load_demo_data()
    preferences = records.get("learning_preferences", {}).get(learner_id, {})
    return render_template("coach_learner.html", title=f"{learner['first_name']} {learner['last_name']}",
                           learner=learner, activities=activities, preferences=preferences,
                           library=coach_library_items(), can_assign=learner_id in session.get("coach_opened_learners", []))


# Assign a reusable activity only after this browser session has opened that learner profile.
@app.route("/coach/learners/<learner_id>/assign", methods=["POST"])
def coach_assign(learner_id):
    learner = next((p for p in coach_shared_learners() if p["id"] == learner_id), None)
    if not learner:
        abort(404)
    if learner_id not in session.get("coach_opened_learners", []):
        abort(403)
    template = next((item for item in coach_library_items()
                     if item["id"] == request.form.get("activity_id")), None)
    if not template:
        abort(404)
    due_on = request.form.get("due_on", "").strip()
    try:
        if due_on:
            date.fromisoformat(due_on)
    except ValueError:
        due_on = ""
    assignments = session.get("coach_assignments", {})
    learner_assignments = assignments.get(learner_id, [])
    assignment_id = f"assigned-{learner_id}-{template['id']}-{len(learner_assignments) + 1}"
    assigned = {**template, "id": assignment_id, "assigned_to": learner_id,
                "source": "coach", "source_name": "Dana Brooks", "due_on": due_on,
                "scheduled_for": "", "estimated_minutes": template.get("estimated_minutes", 15),
                "status": "not_started", "next_action": "Open the activity"}
    assignments[learner_id] = learner_assignments + [assigned]
    session["coach_assignments"] = assignments
    flash(f"{template['title']} assigned to {learner['first_name']}.")
    return redirect(url_for("coach_learner", learner_id=learner_id))


# Create and manage reusable step-by-step activities in the coach's demo library.
@app.route("/coach/library", methods=["GET", "POST"])
def coach_library():
    if request.method == "POST":
        title = request.form.get("title", "").strip()[:80]
        objective = request.form.get("objective", "").strip()[:200]
        instructions = [line.strip()[:240] for line in request.form.get("steps", "").splitlines() if line.strip()][:10]
        if not title or not objective or not instructions:
            flash("Add a title, learning objective, and at least one step.")
            return redirect(url_for("coach_library"))
        library = session.get("coach_activity_library", [])
        activity_id = f"coach-library-{len(library) + 1}"
        steps = [{"order": i, "instruction": text, "picture": "📘", "short_instruction": text,
                  "different_explanation": text, "example": "", "picture_label": "book"}
                 for i, text in enumerate(instructions, 1)]
        library.append({"id": activity_id, "title": title, "source": "coach", "source_name": "Dana Brooks",
                        "scheduled_for": "", "due_on": "", "estimated_minutes": len(steps) * 5,
                        "status": "not_started", "next_action": "Open the activity",
                        "objective": objective, "steps": steps})
        session["coach_activity_library"] = library
        flash(f"{title} is saved in the Activity Library.")
        return redirect(url_for("coach_library"))
    return render_template("coach_library.html", title="Activity Library", activities=coach_library_items())


# Save the coach's demo summary preference without changing learner permissions.
@app.route("/coach/settings", methods=["GET", "POST"])
def coach_settings():
    settings = session.get("coach_settings", {"summary_frequency": "weekly"})
    if request.method == "POST":
        frequency = request.form.get("summary_frequency")
        if frequency in ["weekly", "on_request"]:
            settings["summary_frequency"] = frequency
            session["coach_settings"] = settings
            flash("Coach settings saved.")
        return redirect(url_for("coach_settings"))
    return render_template("coach_settings.html", title="Coach Settings", settings=settings)


# Trust circle: one clean list (initials, name, relationship, level chip). Tapping a row opens an
# edit panel; a form at the bottom adds someone new.
@app.route("/circle")
def circle():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    snapshots = session.get("circle_shared_snapshots", {}).get(person["id"], {})
    encouragements = session.get("trusted_encouragements", {}).get(person["id"], [])
    return render_template("circle.html", title="Circle", circle=circle_for(person), levels=LEVELS,
                           circle_types=CIRCLE_TYPES, access_by_type=ACCESS_BY_TYPE,
                           snapshots=snapshots, encouragements=encouragements)


# Save one member's level, relationship and "Can add routines" (the whole circle goes in the session)
@app.route("/circle/save", methods=["POST"])
def circle_save():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    members = circle_for(person)
    member = next((m for m in members if m["name"] == request.form.get("name")), None)
    if member:
        member_type = request.form.get("member_type")
        member_type = member_type if member_type in CIRCLE_TYPES else member["member_type"]
        access = request.form.get("access")
        if access not in ACCESS_BY_TYPE[member_type]:
            access = "none"
            flash("That access level is not available for this person type. No access was granted.")
        if member_type != member["member_type"] or access != member["access"]:
            clear_circle_snapshot(person["id"], member["name"])
        relationship = request.form.get("relationship", "").strip()[:40] or CIRCLE_TYPES[member_type]
        member.update(member_type=member_type, access=access, routines="routines" in request.form,
                      relationship=relationship)
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
    clear_circle_snapshot(person["id"], name)
    save("circle", person["id"], [m for m in circle_for(person) if m["name"] != name])
    flash(f"{name} removed from your circle.")
    return redirect(url_for("circle"))


# Add a person type and exact permission; no access is granted unless the member chooses it.
@app.route("/circle/add", methods=["POST"])
def circle_add():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    members = circle_for(person)
    name = request.form.get("name", "").strip()[:40]
    member_type = request.form.get("member_type", "")
    access = request.form.get("access", "none")
    if not name:
        flash("Please add a name.")
    elif member_type not in CIRCLE_TYPES:
        flash("Choose a coach, healthcare professional, family member, or friend.")
    elif any(m["name"] == name for m in members):
        flash(f"{name} is already in your circle.")
    else:
        if access not in ACCESS_BY_TYPE[member_type]:
            access = "none"
            flash("That access level is not available for this person type. They were added with no access.")
        relationship = request.form.get("relationship", "").strip()[:40] or CIRCLE_TYPES[member_type]
        members.append({"name": name, "member_type": member_type, "relationship": relationship,
                        "access": access, "routines": False, "status": "demo_invited"})
        save("circle", person["id"], members)
        flash(f"{name} was added to your demo Circle. No external invitation was sent.")
    return redirect(url_for("circle"))


# Revoke a one-time snapshot without removing the Circle contact or changing their access level.
@app.route("/circle/revoke-share", methods=["POST"])
def circle_revoke_share():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    name = request.form.get("name", "")
    clear_circle_snapshot(person["id"], name)
    flash(f"Stopped sharing the saved snapshot with {name}.")
    return redirect(url_for("circle"))


# Preview summaries and save only the one-time snapshots the member explicitly selects.
@app.route("/share", methods=["GET", "POST"])
def share():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    members = circle_for(person)
    patterns = get_patterns(person["id"], devices_for(person))
    celebrations = celebrations_for(person)
    if request.method == "POST":
        selected = [m for m in members if m["name"] in request.form.getlist("share")
                    and m["access"] not in ["none", "health"]]
        snapshots = session.get("circle_shared_snapshots", {})
        person_snapshots = snapshots.get(person["id"], {})
        for member in selected:
            person_snapshots[member["name"]] = {
                "access": member["access"], "shared_on": data.get_today(),
                "member_name": person["first_name"],
                "items": shared_view(member["access"], patterns, celebrations),
            }
        if selected:
            snapshots[person["id"]] = person_snapshots
            session["circle_shared_snapshots"] = snapshots
        names = [m["name"] for m in selected]
        if names:
            flash(f"Saved a one-time summary for {words_filter(names)} in this demo. No automatic updates will be shared.")
        else:
            flash("No one was ticked, so nothing was shared.")
        return redirect(url_for("today"))
    return render_template("share.html", title="Share with my circle", levels=LEVELS,
                           members=[{**m, "view": shared_view(m["access"], patterns, celebrations)} for m in members])


# Show only a one-time summary the member explicitly shared with a family member or friend.
@app.route("/trusted")
def trusted():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    contacts = trusted_shared_contacts(person)
    support_enabled = session.get("trusted_settings", {}).get("encouragement", True)
    name = request.args.get("contact", "")
    selected = next((item for item in contacts if item["name"] == name), contacts[0] if contacts else None)
    return render_template("trusted.html", title="Shared with Me", contacts=contacts,
                           selected=selected, levels=LEVELS, support_enabled=support_enabled)


# Save an encouragement option without sharing any additional member information.
@app.route("/trusted/encouragement", methods=["GET", "POST"])
def trusted_encouragement():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    contacts = trusted_shared_contacts(person)
    support_enabled = session.get("trusted_settings", {}).get("encouragement", True)
    name = request.values.get("contact", "")
    selected = (next((item for item in contacts if item["name"] == name), contacts[0] if contacts else None)
                if support_enabled else None)
    options = {"cheer": "You have got this.", "here": "I am here if you want to talk.",
               "together": "Would you like to work on this together?"}
    if request.method == "POST":
        option = request.form.get("encouragement", "")
        if not selected or option not in options:
            abort(403)
        messages = session.get("trusted_encouragements", {})
        received = messages.get(person["id"], [])
        received.append({"from": selected["name"], "message": options[option], "date": data.get_today()})
        messages[person["id"]] = received
        session["trusted_encouragements"] = messages
        flash("Encouragement sent in this demo. No additional member information was shared.")
        return redirect(url_for("trusted_encouragement", contact=selected["name"]))
    return render_template("trusted_encouragement.html", title="Send Encouragement",
                           contacts=contacts, selected=selected, options=options)


# Let a trusted person hide their encouragement options in this demo session.
@app.route("/trusted/settings", methods=["GET", "POST"])
def trusted_settings():
    settings = session.get("trusted_settings", {"encouragement": True})
    if request.method == "POST":
        settings["encouragement"] = request.form.get("encouragement") == "on"
        session["trusted_settings"] = settings
        flash("Support settings saved for this demo session.")
        return redirect(url_for("trusted_settings"))
    return render_template("trusted_settings.html", title="Support Settings", settings=settings)


# Explain that organization-wide controls are not available in this demonstration.
@app.route("/admin/settings")
def admin_settings():
    return render_template("admin_settings.html", title="Organization Settings")


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
    draft = saved("visit_packet_drafts", pid, {}).get(visit, {})
    return render_template("visit.html", title="Get ready for an appointment", person=person,
                           visit=visit, visit_label=VISITS[visit]["label"],
                           period=f"{start.day} {start:%B} to {end.day} {end:%B %Y}",
                           patterns=patterns, counts=feeling_counts(checkins),
                           summary=daily_cache("doctor", person, lambda: explain_for_doctor(person, patterns, checkins)),
                           questions=draft.get("questions", saved("visit_questions", pid, "")),
                           suggestions=suggestions if suggestions and suggestions["visit"] == visit else None,
                           tell=things_to_tell(visit, patterns, body, devices),
                           entries=saved("visit_entries", pid, []),
                           reason=draft.get("reason", saved("visit_reasons", pid, {}).get(visit, "")),
                           appointment_on=draft.get("appointment_on", ""),
                           selected_changes=draft.get("changes", []),
                           appointment_min=data.get_today(),
                           sources=[d["device"] for d in devices if d["paired"]] + ["My own check ins"])


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


# Save the member's selected reason, changes and questions as a draft for final review.
@app.route("/visit/<visit>/review", methods=["POST"])
def visit_review(visit):
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    if visit not in VISITS:
        abort(404)
    devices = devices_for(person)
    changes = things_to_tell(visit, get_patterns(person["id"], devices),
                             get_body_signals(person["id"], devices), devices)
    selected = request.form.getlist("selected")
    chosen = [changes[int(index)] for index in selected
              if index.isdigit() and int(index) < len(changes)]
    appointment_on = request.form.get("appointment_on", "").strip()
    try:
        if appointment_on:
            date.fromisoformat(appointment_on)
    except ValueError:
        appointment_on = ""
    draft = {"visit": visit, "appointment_type": VISITS[visit]["label"],
             "appointment_on": appointment_on,
             "reason": request.form.get("reason", "").strip()[:500],
             "changes": chosen, "questions": request.form.get("questions", "").strip()[:1000]}
    save("visit_packet_drafts", person["id"], {**saved("visit_packet_drafts", person["id"], {}), visit: draft})
    return redirect(url_for("visit_packet_review", visit=visit))


# Show selected packet contents so the member can choose a recipient and expiration.
@app.route("/visit/<visit>/review", methods=["GET"])
def visit_packet_review(visit):
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    if visit not in VISITS:
        abort(404)
    draft = saved("visit_packet_drafts", person["id"], {}).get(visit)
    if not draft:
        return redirect(url_for("visit_page", visit=visit))
    contacts = [m for m in circle_for(person) if m["access"] == "health"]
    return render_template("visit_review.html", title="Review appointment packet", person=person,
                           draft=draft, contacts=contacts, today=data.get_today())


# Confirm only after a reviewed packet, allowed recipient, and expiration date are submitted.
@app.route("/visit/<visit>/send", methods=["POST"])
def visit_send(visit):
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    if visit not in VISITS:
        abort(404)
    draft = saved("visit_packet_drafts", person["id"], {}).get(visit)
    contacts = [m for m in circle_for(person) if m["access"] == "health"]
    recipient = next((m for m in contacts if m["name"] == request.form.get("recipient")), None)
    expiration = request.form.get("expires_on", "")
    try:
        valid_expiration = date.fromisoformat(expiration) >= date.fromisoformat(data.get_today())
    except ValueError:
        valid_expiration = False
    if not draft or request.form.get("reviewed") != "yes" or not recipient or not valid_expiration:
        flash("Review the packet, choose an approved recipient, and set a valid expiration date before continuing.")
        return redirect(url_for("visit_packet_review", visit=visit))
    flash(f"Reviewed for {recipient['name']} through {expiration}. This demo did not send or share the packet.")
    return redirect(url_for("visit_page", visit=visit))


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


# Show settings that match the selected demo role and save member display preferences.
@app.route("/settings", methods=["GET", "POST"])
def settings():
    role_routes = {"coach": "coach_settings", "healthcare": "professional_settings",
                   "trusted": "trusted_settings", "admin": "admin_settings"}
    if session.get("demo_role", "member") in role_routes:
        return redirect(url_for(role_routes[session["demo_role"]]))
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    # Demo controls: save the chosen data source
    if request.method == "POST" and request.form.get("source") in SOURCES:
        session["data_source"] = request.form["source"]
        flash(f"Data source set to {SOURCES[request.form['source']]}.")
        return redirect(url_for("settings"))
    if request.method == "POST" and request.form.get("action") == "save_member_preferences":
        density, pictures = request.form.get("density"), request.form.get("picture_preference")
        rate = request.form.get("speech_rate")
        if density in ["comfortable", "compact"] and pictures in dict(CHECKIN_DISPLAY) and rate in ["0.8", "1", "1.2"]:
            preferences = {"density": density, "picture_preference": pictures,
                           "read_aloud": request.form.get("read_aloud") == "on", "speech_rate": rate}
            all_preferences = session.get("member_preferences", {})
            all_preferences[person["id"]] = preferences
            session["member_preferences"] = all_preferences
            displays = session.get("checkin_display", {})
            displays[person["id"]] = pictures
            session["checkin_display"] = displays
            if request.form.get("theme") in THEMES:
                session["theme"] = request.form["theme"]
            flash("Your display and reading preferences were saved in this demo.")
        return redirect(url_for("settings"))
    return render_template("settings.html", title="Settings", sources=SOURCES,
                           google_connected=google_health.is_connected(), person=person,
                           preferences=member_preferences(person["id"]), display_options=CHECKIN_DISPLAY)


# Download only this member's changes saved in the current demo session.
@app.route("/settings/export")
def settings_export():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    person_id = person["id"]
    saved_keys = ["profile", "member_preferences", "circle", "circle_shared_snapshots", "paired",
                  "checkin_display", "checkin_response", "goals_added", "goals_done", "climb_seen",
                  "badges", "routines", "health_action_states", "professional_proposals",
                  "trusted_encouragements", "coach_assignments",
                  "visit_questions", "visit_suggestions", "visit_entries", "visit_packet_drafts"]
    changes = {key: session.get(key, {}).get(person_id) for key in saved_keys
               if person_id in session.get(key, {})}
    changes["checkins"] = [item for item in session.get("checkins", [])
                            if item.get("person_id") == person_id]
    changes["circle"] = circle_for(person)
    changes["connected_sources"] = devices_for(person)
    demo = load_demo_data()
    activities = demo["activities"] if person_id == demo["member"]["application_person_id"] else []
    activities = activities + session.get("coach_assignments", {}).get(person_id, [])
    activity_ids = [item["id"] for item in activities]
    changes["activity_states"] = {activity_id: {
        "progress": session.get("activity_progress", {}).get(activity_id),
        "presentation": session.get("activity_ui", {}).get(activity_id)}
        for activity_id in activity_ids
        if activity_id in session.get("activity_progress", {}) or activity_id in session.get("activity_ui", {})}
    export = {"scope": "Member changes, Circle choices, and source choices from this demo session; baseline CSV health readings are not included.",
              "member": {"id": person_id, "first_name": person["first_name"]},
              "preferences": {**member_preferences(person_id), "theme": session.get("theme", "ocean"),
                              "celebrations": session.get("celebrations", "big")},
              "session_changes": changes}
    response = app.response_class(json.dumps(export, ensure_ascii=False, indent=2),
                                  mimetype="application/json")
    response.headers["Content-Disposition"] = f"attachment; filename=pair-demo-export-{person_id}.json"
    return response


# Remove this member's demo changes and disconnect the optional in-memory Google token.
@app.route("/settings/delete-data", methods=["POST"])
def settings_delete_data():
    person = current_person()
    if not person:
        return redirect(url_for("choose"))
    if request.form.get("confirm_delete") != "yes":
        flash("Select the confirmation box before deleting your demo data.")
        return redirect(url_for("settings"))
    person_id = person["id"]
    demo = load_demo_data()
    activities = demo["activities"] if person_id == demo["member"]["application_person_id"] else []
    activities = activities + session.get("coach_assignments", {}).get(person_id, [])
    for key in ["profile", "member_preferences", "circle", "circle_shared_snapshots", "paired",
                "checkin_display", "checkin_response", "week", "doctor", "goals_added", "goals_done",
                "climb_seen", "badges", "routines", "health_action_states", "professional_proposals",
                "trusted_encouragements", "coach_assignments", "visit_questions", "visit_suggestions",
                "visit_entries", "visit_packet_drafts"]:
        values = session.get(key)
        if isinstance(values, dict):
            values.pop(person_id, None)
            session[key] = values
    for key in ["activity_ui", "activity_progress"]:
        values = session.get(key, {})
        for activity in activities:
            values.pop(activity["id"], None)
        session[key] = values
    session["checkins"] = [item for item in session.get("checkins", [])
                           if item.get("person_id") != person_id]
    session.pop("google_from_devices", None)
    google_health.TOKENS.pop(session.pop("google_key", None), None)
    if person_id == NEW_ID:
        session.pop("new_person", None)
        session.pop("signup", None)
    session.pop("person_id", None)
    session.pop("theme", None)
    session.pop("celebrations", None)
    session.pop("data_source", None)
    flash("Your member changes were removed from this demo session. Simulated sample records remain in the demo.")
    return redirect(url_for("choose"))


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
