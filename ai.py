import json
import os
import anthropic
from dotenv import load_dotenv

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


# Rule based backup: the change sentences as the summary, and the first calms item as the step
def week_backup(person, patterns):
    changes = [c["words"] for c in patterns["changes"]]
    if patterns["status"] == "Still learning your usual":
        summary = "Pair is still learning your usual. This takes about 10 days."
    elif patterns["status"] == "Steady week" or not changes:
        summary = "Your patterns look like your usual this week."
    else:
        summary = "Pair noticed some changes this week. " + ". ".join(changes) + "."
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
