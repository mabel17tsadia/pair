import json
import os
import anthropic
from dotenv import load_dotenv
from patterns import feeling_counts

# Load ANTHROPIC_API_KEY from the .env file (the Anthropic client reads it from there)
load_dotenv()

# Instructions for Claude when explaining the person's week
WEEK_SYSTEM = """You write for Pair, an app that tells a person in kind, plain words how their
daily patterns changed this week. Write to the person as "you", in short, simple sentences.
summary: 2 or 3 sentences describing what changed. If the status is "Steady week", reassure them.
Only describe changes. Never use medical words, never guess a cause or a diagnosis, and never
use words like bad, warning or abnormal.
gentle_step: one small suggestion under 12 words, built from one item in their calms list and
linked to what changed (for example, more late screen time and less sleep could suggest
"Music in a quiet room before bed"). On a steady week, suggest something they enjoy from calms."""

# The exact JSON shape we want back: a summary and one gentle step
WEEK_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}, "gentle_step": {"type": "string"}},
    "required": ["summary", "gentle_step"],
    "additionalProperties": False,
}


# Send one message to Claude and return its text reply (raises an error if anything goes wrong)
def ask_claude(system, text, output_format=None):
    client = anthropic.Anthropic(timeout=20.0, max_retries=1)
    output_config = {"effort": "low"}
    if output_format:
        output_config["format"] = output_format
    response = client.messages.create(
        model="claude-haiku-5-5",
        max_tokens=16000,
        output_config=output_config,
        system=system,
        messages=[{"role": "user", "content": text}],
    )
    if response.stop_reason == "refusal":
        raise ValueError("Claude declined the request")
    return next((b.text for b in response.content if b.type == "text"), "")


# Rule based backup: one short summary (the change rows on Today give the details),
# and the first calms item as the step
def week_backup(person, patterns):
    if patterns["status"] == "Still learning your usual":
        summary = "Pair is still learning your usual. This takes about 10 days."
    elif patterns["status"] == "Steady week":
        summary = "Your patterns look like your usual this week."
    else:
        summary = f"Pair noticed {patterns['change_count']} changes this week. The details are below."
    step = f"Try: {person['calms'][0]}" if person["calms"] else "Try: a short, quiet break"
    return {"summary": summary, "gentle_step": step, "source": "rules"}


# Ask Claude for a kind summary of the week and one gentle step; use the rule based backup
# if there is no API key, Pair is still learning, or anything goes wrong.
# Sends only the first name, drains, calms, the status and the change sentences
# (never last names, check in notes or device names).
def explain_week(person, patterns):
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("No API key found, using rule based week summary")
        return week_backup(person, patterns)
    if patterns["status"] == "Still learning your usual":
        return week_backup(person, patterns)
    details = json.dumps({"first_name": person["first_name"], "drains": person["drains"],
                          "calms": person["calms"], "status": patterns["status"],
                          "changes": [c["words"] for c in patterns["changes"]]})
    try:
        answer = json.loads(ask_claude(WEEK_SYSTEM, details, {"type": "json_schema", "schema": WEEK_SCHEMA}))
        if not answer["summary"].strip() or not answer["gentle_step"].strip():
            raise ValueError("Empty answer")
        return {"summary": answer["summary"], "gentle_step": answer["gentle_step"], "source": "ai"}
    # Any error at all (network, bad key, odd answer, SDK problem) uses the backup instead of crashing
    except Exception as error:
        print("AI week summary failed, using rule based summary:", type(error).__name__)
        return week_backup(person, patterns)


# Instructions for Claude when writing the doctor visit paragraph
DOCTOR_SYSTEM = """You write a short, neutral paragraph that a doctor can scan in 30 seconds.
It describes a person's daily pattern changes (the last 5 days compared with their usual) and how
often they reported moods and body feelings in their own check ins (the last 14 days). Keep these two
time spans correct. Write in third person using only their first name
(repeat the name instead of using he, she or they). Under 80 words, plain text, no lists.
Only describe what was recorded. Never suggest a diagnosis, a cause, or any treatment or advice."""


# "Tired: 4 times, Headache: 2 times" from a list like [("Tired", 4), ("Headache", 2)]
def count_words(counts):
    return ", ".join(f"{name}: {n} time{'s' if n != 1 else ''}" for name, n in counts)


# Rule based backup for the doctor paragraph: the same facts in fixed sentences
def doctor_backup(person, patterns, counts):
    name = person["first_name"]
    changes = [c["words"][0].lower() + c["words"][1:] for c in patterns["changes"]]
    if changes:
        text = f"Over the last 5 days, compared with {name}'s usual, Pair noticed: " + "; ".join(changes) + "."
    else:
        text = f"Pair noticed no large changes in {name}'s daily patterns over the last 5 days."
    if counts["moods"]:
        text += f" Moods in {name}'s check ins over 14 days: {count_words(counts['moods'])}."
    if counts["body"]:
        text += f" Body feelings mentioned: {count_words(counts['body'])}."
    return {"text": text, "source": "rules"}


# Ask Claude for a short, neutral paragraph for a doctor; use the rule based backup if there is
# no API key or anything goes wrong. Sends only the first name, the change sentences and the
# mood and body counts (never check in notes, last names or device names).
def explain_for_doctor(person, patterns, checkins):
    counts = feeling_counts(checkins)
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("No API key found, using rule based doctor summary")
        return doctor_backup(person, patterns, counts)
    details = json.dumps({"first_name": person["first_name"],
                          "changes": [c["words"] for c in patterns["changes"]],
                          "mood_counts": dict(counts["moods"]), "body_counts": dict(counts["body"])})
    try:
        text = ask_claude(DOCTOR_SYSTEM, details).strip()
        if not text:
            raise ValueError("Empty answer")
        return {"text": text, "source": "ai"}
    # Any error at all uses the backup instead of crashing
    except Exception as error:
        print("AI doctor summary failed, using rule based summary:", type(error).__name__)
        return doctor_backup(person, patterns, counts)


# Instructions for Claude when answering a check in
CHECKIN_SYSTEM = """You write for Pair, an app that responds kindly right after a person checks in.
You get how they say they feel (and any body feelings) and how their daily patterns changed this week.
Write to the person as "you", in plain, short, warm sentences. Never use medical words, never
diagnose, never guess a cause, and never say that a pattern explains how they feel (mention them
side by side instead). Do not use exclamation marks.
message: exactly 2 short sentences that connect how they feel with their patterns.
- Feeling good or okay and patterns steady: encourage them.
- Feeling good or okay but patterns changed: a gentle heads up about one change, linked to a drain if it fits.
- Feeling low or overwhelmed and patterns steady: validate how they feel.
- Feeling low or overwhelmed and patterns changed: validate, and say it is okay to go gently.
suggestion: one small suggestion under 15 words. When they feel low or overwhelmed, use one item
from their calms list."""

# The exact JSON shape we want back: two sentences and one suggestion
CHECKIN_SCHEMA = {
    "type": "object",
    "properties": {"message": {"type": "string"}, "suggestion": {"type": "string"}},
    "required": ["message", "suggestion"],
    "additionalProperties": False,
}

# A heads up for the first change, in words with no numbers (used by the rule based backup)
CHANGE_HEADS_UP = {
    "sleep_min": "Your sleep has been shorter this week",
    "steps": "You have been moving less this week",
    "late_screen_min": "You have been on your phone later at night this week",
    "unlocks": "You have been picking up your phone more often this week",
    "time_out_min": "You have been spending more time at home this week",
}

# Feelings on the Check in page that count as "good or okay"; the others count as "low or overwhelmed"
OKAY_FEELINGS = ["Calm", "Okay"]

# Week statuses that count as "patterns changed" ("Steady week" and "Still learning" count as steady)
CHANGED_STATUSES = ["A few changes", "Several changes"]


# Rule based backup: the four cases (feels okay or low, patterns steady or changed)
def checkin_backup(person, mood, patterns):
    calm = person["calms"][0] if person["calms"] else "a short, quiet break"
    feels_okay = mood in OKAY_FEELINGS
    changed = patterns["status"] in CHANGED_STATUSES
    if feels_okay and not changed:
        message = "Your patterns look like your usual. It is good to hear you feel " + mood.lower() + "."
        suggestion = "A short walk could feel good today."
    elif feels_okay:
        message = f"Glad you feel {mood.lower()}. {CHANGE_HEADS_UP[patterns['changes'][0]['signal']]}."
        suggestion = "If today includes somewhere busy, give yourself extra breaks."
    elif not changed:
        message = "Thank you for telling Pair how you feel. It is okay to have days like this."
        suggestion = f"Try: {calm}"
    else:
        message = "Thank you for telling Pair how you feel. Your patterns have changed this week too, so go gently today."
        suggestion = f"One gentle step: {calm}"
    return {"message": message, "suggestion": suggestion, "source": "rules"}


# Respond right after a check in: 2 short sentences and one suggestion that combine how the person
# feels with this week's patterns, plus whether to offer "Share with my circle" (feeling low and
# patterns changed). Sends only the first name, drains, calms, the feeling, body feelings, the
# status and the change sentences (never the check in note, last names or device names).
# A real product could also use live signals here, such as heart rate or glucose from a paired device.
def respond_to_checkin(person, mood, body, patterns):
    offer_share = mood not in OKAY_FEELINGS and patterns["status"] in CHANGED_STATUSES
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("No API key found, using rule based check in response")
        return {**checkin_backup(person, mood, patterns), "share": offer_share}
    details = json.dumps({"first_name": person["first_name"], "drains": person["drains"],
                          "calms": person["calms"], "feeling": mood, "body": body,
                          "status": patterns["status"],
                          "changes": [c["words"] for c in patterns["changes"]]})
    try:
        answer = json.loads(ask_claude(CHECKIN_SYSTEM, details, {"type": "json_schema", "schema": CHECKIN_SCHEMA}))
        if not answer["message"].strip() or not answer["suggestion"].strip():
            raise ValueError("Empty answer")
        return {"message": answer["message"], "suggestion": answer["suggestion"], "source": "ai", "share": offer_share}
    # Any error at all uses the backup instead of crashing
    except Exception as error:
        print("AI check in response failed, using rule based response:", type(error).__name__)
        return {**checkin_backup(person, mood, patterns), "share": offer_share}
