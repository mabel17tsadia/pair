import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from flask import Blueprint, render_template, session, redirect, request, url_for, flash

# All Google routes live here; app.py registers this blueprint
google = Blueprint("google", __name__, url_prefix="/google")

# Google sign-in and Google Health API addresses (see developers.google.com/health)
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API_URL = "https://health.googleapis.com/v4/users/me/dataTypes"

# Must match the redirect URI saved in Google Cloud exactly
REDIRECT_URI = "http://127.0.0.1:5000/google/callback"

# Read-only permissions: sleep, and activity (which includes steps)
SCOPES = [
    "https://www.googleapis.com/auth/googlehealth.sleep.readonly",
    "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
]

# How many recent days to read (Pair compares the last 5 days with the earlier ones)
DAYS = 21

# Sign-in tokens, kept in server memory only (never in files, logs or cookies).
# We chose this over the Flask session because the session is a signed cookie, not an
# encrypted one: anyone with the browser's cookies could read a token stored there.
# The browser only gets a random key that points here; everything is lost on restart.
TOKENS = {}


# The Google page where the person signs in and agrees to share their data
def sign_in_url(state):
    params = {"client_id": os.getenv("GOOGLE_CLIENT_ID"), "redirect_uri": REDIRECT_URI,
              "response_type": "code", "scope": " ".join(SCOPES), "state": state,
              "access_type": "online", "prompt": "consent"}
    return AUTH_URL + "?" + urllib.parse.urlencode(params)


# Send a request and return the JSON reply; on an HTTP error, keep only the status code
def send(req):
    try:
        with urllib.request.urlopen(req, timeout=15) as reply:
            return json.load(reply)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"status {error.code}")


# Print a short error note: only the status code or the kind of error, never tokens or keys
def log_error(where, error):
    print(f"{where} failed:", error if isinstance(error, RuntimeError) else type(error).__name__)


# After sign-in, swap the one-time code from Google for an access token
def exchange_code(code):
    body = urllib.parse.urlencode({"code": code, "redirect_uri": REDIRECT_URI,
                                   "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                                   "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                                   "grant_type": "authorization_code"}).encode()
    return send(urllib.request.Request(TOKEN_URL, data=body))["access_token"]


# Turn Google's {year, month, day} into "2026-10-28"
def to_iso(d):
    return date(d["year"], d["month"], d["day"]).isoformat()


# Steps: one total per day from the dailyRollUp endpoint
def daily_steps(token, start, end):
    civil = lambda d, h, m, s: {"date": {"year": d.year, "month": d.month, "day": d.day},
                                "time": {"hours": h, "minutes": m, "seconds": s}}
    body = json.dumps({"range": {"start": civil(start, 0, 0, 0), "end": civil(end, 23, 59, 59)},
                       "windowSizeDays": 1}).encode()
    reply = send(urllib.request.Request(
        f"{API_URL}/steps/dataPoints:dailyRollUp", data=body, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}))
    return {to_iso(p["civilStartTime"]["date"]): int(p["steps"]["countSum"])
            for p in reply.get("rollupDataPoints", []) if "steps" in p}


# Sleep: minutes asleep per day (by the day the sleep ended), from the reconcile endpoint.
# Counts all sleep for now, naps included; we will check a real reply before handling naps.
def daily_sleep(token, start, end):
    sleep, page = {}, ""
    filter_text = (f'sleep.interval.civil_end_time >= "{start}" AND '
                   f'sleep.interval.civil_end_time < "{end + timedelta(days=1)}"')
    for _ in range(10):
        query = urllib.parse.urlencode({"filter": filter_text, "pageToken": page})
        reply = send(urllib.request.Request(f"{API_URL}/sleep/dataPoints:reconcile?{query}",
                                            headers={"Authorization": f"Bearer {token}"}))
        for p in reply.get("dataPoints", []):
            day = to_iso(p["sleep"]["interval"]["civilEndTime"]["date"])
            sleep[day] = sleep.get(day, 0) + int(p["sleep"].get("summary", {}).get("minutesAsleep", 0))
        page = reply.get("nextPageToken")
        if not page:
            break
    return sleep


# The last 21 days as rows like signals.csv: date, sleep_min, steps (oldest first).
# Only days Google has data for; a missing value counts as 0.
def read_days(token):
    end = date.today()
    start = end - timedelta(days=DAYS - 1)
    sleep, steps = daily_sleep(token, start, end), daily_steps(token, start, end)
    return [{"date": d, "sleep_min": sleep.get(d, 0), "steps": steps.get(d, 0)}
            for d in sorted(set(sleep) | set(steps))]


# True if this browser is signed in to Google Health
def is_connected():
    return session.get("google_key") in TOKENS


# The signed-in person's recent days, or an empty list if not signed in or anything fails
def recent_days():
    token = TOKENS.get(session.get("google_key"))
    if not token:
        return []
    try:
        return read_days(token)
    except Exception as error:
        log_error("Google Health", error)
        return []


# Sign-in, step 1: send the person to Google with a random "state" to check later
@google.route("/login")
def login():
    session["google_state"] = secrets.token_urlsafe(16)
    return redirect(sign_in_url(session["google_state"]))


# Sign-in, step 2: Google sends the person back here with a one-time code
# (or with an error, for example if they said no). Then go back to Settings, or to
# Paired devices if sign-in started there.
@google.route("/callback")
def callback():
    back = url_for("devices" if session.pop("google_from_devices", False) else "settings")
    if request.args.get("state") != session.pop("google_state", None) or "code" not in request.args:
        flash("Google sign-in did not finish. Showing sample data.")
        return redirect(back)
    try:
        token = exchange_code(request.args["code"])
    except Exception as error:
        log_error("Google sign-in", error)
        flash("Google sign-in did not work. Showing sample data.")
        return redirect(back)
    # Keep the token in server memory; the browser only gets a random key that points to it
    session["google_key"] = secrets.token_hex(16)
    TOKENS[session["google_key"]] = token
    flash("Connected to Google Health.")
    return redirect(back)


# Disconnect: delete the token from server memory, then go back to the page the button was on
@google.route("/disconnect", methods=["POST"])
def disconnect():
    TOKENS.pop(session.pop("google_key", None), None)
    flash("Disconnected from Google Health. Showing sample data.")
    return redirect(url_for("devices" if request.form.get("back") == "devices" else "settings"))


# Test page: only how many days of sleep and steps came back, never the data itself
@google.route("/test")
def test():
    days = recent_days()
    return render_template("google_test.html", title="Google Health test",
                           connected=is_connected(),
                           sleep_days=sum(1 for d in days if d["sleep_min"]),
                           step_days=sum(1 for d in days if d["steps"]))
