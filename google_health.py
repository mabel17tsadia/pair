import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

# Google sign-in and Google Health API addresses
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API_URL = "https://health.googleapis.com/v4/users/me/dataTypes"

# Read-only permissions: heart rate, steps (activity) and sleep
SCOPES = [
    "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly",
    "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
    "https://www.googleapis.com/auth/googlehealth.sleep.readonly",
]

# Sign-in tokens, kept in server memory only (never in files, logs or cookies).
# Each browser gets a random key in its session; everything is lost when the app restarts.
TOKENS = {}


# The Google page where the person signs in and agrees to share their data
def sign_in_url(redirect_uri, state):
    params = {"client_id": os.getenv("GOOGLE_CLIENT_ID"), "redirect_uri": redirect_uri,
              "response_type": "code", "scope": " ".join(SCOPES), "state": state,
              "access_type": "online", "prompt": "consent"}
    return AUTH_URL + "?" + urllib.parse.urlencode(params)


# Send a request and return the JSON reply; on an HTTP error, include Google's message
def send(request):
    try:
        with urllib.request.urlopen(request, timeout=15) as reply:
            return json.load(reply)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"{error.code}: {error.read().decode()[:300]}")


# After sign-in, swap the one-time code from Google for an access token
def exchange_code(code, redirect_uri):
    body = urllib.parse.urlencode({"code": code, "redirect_uri": redirect_uri,
                                   "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                                   "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                                   "grant_type": "authorization_code"}).encode()
    return send(urllib.request.Request(TOKEN_URL, data=body))["access_token"]


# Get all data points of one type that match a filter (follows up to 10 pages)
def list_points(token, data_type, filter_text):
    points, page = [], ""
    for _ in range(10):
        query = urllib.parse.urlencode({"filter": filter_text, "pageToken": page})
        request = urllib.request.Request(f"{API_URL}/{data_type}/dataPoints?{query}",
                                         headers={"Authorization": f"Bearer {token}"})
        reply = send(request)
        points += reply.get("dataPoints", [])
        page = reply.get("nextPageToken")
        if not page:
            break
    return points


# Read today's heart rate, steps and last night's sleep, in the same shape as the sample CSVs
def read_today(token):
    start, end = date.today().isoformat(), (date.today() + timedelta(days=1)).isoformat()

    # Heart rate: average the readings into 15-minute blocks, like heart.csv
    blocks = {}
    for p in list_points(token, "heart-rate",
                         f'heartRate.sample_time.civil_time >= "{start}T00:00:00" AND '
                         f'heartRate.sample_time.civil_time < "{end}T00:00:00"'):
        t = p["heartRate"]["sampleTime"]["civilTime"].get("time", {})
        block = f"{t.get('hours', 0):02d}:{t.get('minutes', 0) // 15 * 15:02d}"
        blocks.setdefault(block, []).append(int(p["heartRate"]["beatsPerMinute"]))
    heart = [{"time": f"{start} {b}", "bpm": round(sum(v) / len(v))} for b, v in sorted(blocks.items())]

    # Steps: add up every steps interval that started today
    steps = sum(int(p["steps"]["count"]) for p in list_points(
        token, "steps",
        f'steps.interval.civil_start_time >= "{start}" AND steps.interval.civil_start_time < "{end}"'))

    # Sleep: minutes asleep in sleep sessions that ended today, leaving out naps
    sleep = sum(int(p["sleep"].get("summary", {}).get("minutesAsleep", 0)) for p in list_points(
        token, "sleep",
        f'sleep.interval.civil_end_time >= "{start}" AND sleep.interval.civil_end_time < "{end}"')
        if not p["sleep"].get("metadata", {}).get("nap"))

    return {"heart": heart, "steps": steps, "sleep_min": sleep}
