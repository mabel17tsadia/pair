import json
import os
import anthropic
from dotenv import load_dotenv
from patterns import feeling_counts
from visits import VISITS, VISIT_TOPIC_GUIDANCE

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
You get their first name, what helps them feel calm, the mood they chose, and short facts that their
patterns and paired devices show. Write to the person as "you", in plain, short, warm sentences.
Never diagnose, never guess a cause, never say a fact explains how they feel, and never use the
words good or bad about a reading. Never suggest food, drinks, medicine or doses. For glucose, only
say "follow your care plan" or "check with your care team". Do not use exclamation marks.
message: exactly 2 short sentences that put the mood and the facts side by side.
- Calm or okay, facts steady: encourage them.
- Calm or okay, but facts show changes or a low glucose reading: a gentle heads up about one fact.
- Tired, facts steady: gentle motivation, using one item from their calms list.
- Worried or overwhelmed, facts steady: validate how they feel.
- Worried or overwhelmed, facts show changes: validate, and say it is okay to go gently.
- Another feeling: acknowledge the feeling without guessing what it means.
- Facts say Pair is still learning: thank them; each check in helps Pair learn their usual.
suggestion: one small step under 15 words, using one item from their calms list when it fits.
If a fact mentions a low glucose reading, the suggestion is "Follow your care plan before anything active." """

# The exact JSON shape we want back: two sentences and one suggestion
CHECKIN_SCHEMA = {
    "type": "object",
    "properties": {"message": {"type": "string"}, "suggestion": {"type": "string"}},
    "required": ["message", "suggestion"],
    "additionalProperties": False,
}

# Moods on the Check in page that count as "calm or okay"
OKAY_FEELINGS = ["Calm", "Okay"]

# Moods that get "Share with my circle" when signals changed
WORRIED_FEELINGS = ["Worried", "Overwhelmed"]

# Week statuses that count as "patterns changed" ("Steady week" and "Still learning" count as steady)
CHANGED_STATUSES = ["A few changes", "Several changes"]

# Words in the note that may mean an emergency (checked by rules, before any AI call).
# "’" is the curly apostrophe phones often type in "can't".
URGENT_WORDS = ["chest pain", "can't breathe", "cant breathe", "can\u2019t breathe", "cannot breathe",
                "hurt myself", "suicide", "kill myself"]

# Words an AI answer must never contain (food, medicine or doses); if one appears, the rules answer is used
BLOCKED_WORDS = ["eat", "food", "snack", "juice", "sugar", "carb", "carbs", "insulin", "medicine", "medication",
                 "dose", "doses", "pill", "pills", "tablet"]

# The suggestion whenever the glucose monitor shows a low reading
CARE_PLAN = "Follow your care plan before anything active."


# True if the optional note contains words that may mean an emergency
def is_urgent(note):
    note = note.lower()
    return any(word in note for word in URGENT_WORDS)


# Up to three short facts from body signals and patterns: changed body signals first (so a low
# glucose reading is never left out), then pattern changes, then anything steady
def checkin_facts(patterns, body):
    changed = [f for v in body if v["changed"] for f in v["facts"]]
    steady = [f for v in body if not v["changed"] for f in v["facts"]]
    pattern_facts = [c["words"] for c in patterns["changes"]]
    if patterns["status"] == "Still learning your usual":
        steady.append("Pair is still learning your usual")
    elif not pattern_facts:
        steady.append("Your daily patterns look like your usual")
    return (changed + pattern_facts + steady)[:3]


# Rule based backup for the cases (mood calm or okay, tired, worried or overwhelmed; signals steady
# or changed; a low glucose reading always gets the care plan suggestion)
def checkin_backup(person, mood, facts, changed, low_glucose, learning):
    calm = person["calms"][0] if person["calms"] else "a short, quiet break"
    if learning and not changed:
        message = "Thank you for checking in. Each check in helps Pair learn what is usual for you."
        suggestion = "A short walk could feel good today." if mood in OKAY_FEELINGS else f"Try: {calm}"
    elif mood in OKAY_FEELINGS and not changed:
        message = f"Glad you feel {mood.lower()}. Your patterns look like your usual."
        suggestion = "A short walk could feel good today."
    elif mood in OKAY_FEELINGS:
        heads_up = "Your glucose monitor shows a low reading" if low_glucose else "Pair noticed: " + facts[0][0].lower() + facts[0][1:]
        message = f"Glad you feel {mood.lower()}. {heads_up}."
        suggestion = "If today includes somewhere busy, give yourself extra breaks."
    elif mood == "Tired" and not changed:
        message = "Thank you for telling Pair you feel tired. Your sleep and movement look like your usual."
        suggestion = f"Something from your calms list, like {calm.lower()}, might lift your energy."
    elif not changed:
        message = "Thank you for telling Pair how you feel. It is okay to have days like this."
        suggestion = f"Try: {calm}"
    else:
        message = "Thank you for telling Pair how you feel. Some of your signals have changed too, so go gently today."
        suggestion = f"One gentle step: {calm}"
    return {"message": message, "suggestion": CARE_PLAN if low_glucose else suggestion, "source": "rules"}


# Respond right after a check in. First a rule based emergency check of the note (no AI call if it
# matches). Otherwise: up to three facts from patterns and body signals, then 2 sentences and one
# suggestion (AI, or the rules backup), and whether to offer "Share with my circle" (worried or
# overwhelmed, and signals changed). Sends only the first name, calms, the mood and the facts:
# never the note, last names or device names. Live signals (heart rate, glucose) come from paired devices.
def respond_to_checkin(person, mood, patterns, body, note=""):
    if is_urgent(note):
        return {"urgent": True}
    facts = checkin_facts(patterns, body)
    changed = patterns["status"] in CHANGED_STATUSES or any(v["changed"] for v in body)
    low_glucose = any(v["lows"] for v in body)
    learning = patterns["status"] == "Still learning your usual"
    extra = {"facts": facts, "share": mood in WORRIED_FEELINGS and changed}
    backup = lambda: {**checkin_backup(person, mood, facts, changed, low_glucose, learning), **extra}
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("No API key found, using rule based check in response")
        return backup()
    details = json.dumps({"first_name": person["first_name"], "calms": person["calms"], "mood": mood, "facts": facts})
    try:
        answer = json.loads(ask_claude(CHECKIN_SYSTEM, details, {"type": "json_schema", "schema": CHECKIN_SCHEMA}))
        text = (answer["message"] + " " + answer["suggestion"]).lower()
        if not answer["message"].strip() or not answer["suggestion"].strip():
            raise ValueError("Empty answer")
        if any(word in text.replace(",", " ").replace(".", " ").split() for word in BLOCKED_WORDS):
            raise ValueError("Answer mentioned food, medicine or doses")
        suggestion = CARE_PLAN if low_glucose else answer["suggestion"]
        return {"message": answer["message"], "suggestion": suggestion, "source": "ai", **extra}
    # Any error at all uses the backup instead of crashing
    except Exception as error:
        print("AI check in response failed, using rule based response:", type(error).__name__)
        return backup()


# Instructions for Claude when suggesting questions for an appointment
QUESTIONS_SYSTEM = """You help a person get ready for a health appointment. You get their first name,
who they are seeing, sentences about how their daily patterns and body signals changed, and how
often they chose each mood in check ins. Write 3 to 5 short questions (under 25 words each) the person
could ask, in their own voice ("I", "my"), fitted to this kind of professional. A question may mention
one fact, for example for a dietitian: "My monitor showed some low readings this week. What should I
eat before work?" Only use the facts given; never invent details. Never name a condition and never
suggest a diagnosis or treatment yourself; only ask."""

# The exact JSON shape we want back: a list of questions
QUESTIONS_SCHEMA = {
    "type": "object",
    "properties": {"questions": {"type": "array", "items": {"type": "string"}}},
    "required": ["questions"],
    "additionalProperties": False,
}


# What Pair may tell the AI about a person's week: change sentences, body signal sentences and mood counts
def week_facts(patterns, body, mood_counts):
    return {"changes": [c["words"] for c in patterns["changes"]],
            "body_signals": [v["sentence"] for v in body], "mood_counts": dict(mood_counts)}


# Suggest 3 to 5 questions for this kind of appointment; use the 3 general questions for that
# visit type if there is no API key or anything goes wrong. Sends only the first name, the visit
# type, the change and body sentences and mood counts (never notes or last names).
def suggest_questions(person, visit, patterns, body, mood_counts):
    backup = {"questions": VISITS[visit]["questions"], "source": "rules"}
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("No API key found, using general questions")
        return backup
    details = json.dumps({"first_name": person["first_name"], "seeing": VISITS[visit]["label"],
                          **week_facts(patterns, body, mood_counts)})
    try:
        answer = json.loads(ask_claude(QUESTIONS_SYSTEM, details, {"type": "json_schema", "schema": QUESTIONS_SCHEMA}))
        questions = [q.strip()[:200] for q in answer["questions"] if q.strip()][:5]
        if len(questions) < 3:
            raise ValueError("Too few questions")
        return {"questions": questions, "source": "ai"}
    # Any error at all uses the general questions instead of crashing
    except Exception as error:
        print("AI question suggestions failed, using general questions:", type(error).__name__)
        return backup


# Adapt fixed visit topics using only the chosen professional and concerns the member entered for this visit.
def suggest_visit_topics(visit, concerns=""):
    guidance = VISIT_TOPIC_GUIDANCE[visit]
    backup = {"topics": guidance["topics"], "source": "rules", "source_name": guidance["source_name"],
              "reference": guidance["source"]}
    if not os.getenv("ANTHROPIC_API_KEY"):
        return backup
    details = json.dumps({"professional": VISITS[visit]["label"], "scope": guidance["scope"],
                          "member_selected_concerns": concerns[:500]})
    schema = {"type": "object", "properties": {"topics": {"type": "array", "items": {"type": "string"}}},
              "required": ["topics"], "additionalProperties": False}
    system = """Offer 3 to 5 short, neutral topics a person might choose to discuss with this type of
    health professional. Use only the profession, scope and optional concerns the member entered. Topics are examples,
not medical advice. Never diagnose, imply the person has a condition, recommend treatment, or tell
the person which professional they need. Return short topic labels only."""
    try:
        answer = json.loads(ask_claude(system, details, {"type": "json_schema", "schema": schema}))
        topics = [item.strip()[:100] for item in answer["topics"] if item.strip()][:5]
        unsafe = ["you have", "diagnos", "treatment", "prescrib", "you should see", "recommend a", "must see"]
        if len(topics) < 3 or any(word in item.lower() for item in topics for word in unsafe):
            raise ValueError("Unsafe or incomplete topic list")
        return {"topics": topics, "source": "ai", "source_name": guidance["source_name"],
                "reference": guidance["source"]}
    except Exception as error:
        print("Visit topic suggestions failed, using built-in guidance:", type(error).__name__)
        return backup
# Instructions for Claude when helping someone choose who to see
PROFESSIONALS_SYSTEM = """You help a person choose which kind of health professional to see.
You get their first name, how they say they have been feeling, and sentences about their patterns
and body signals. Pick 1 to 3 kinds of professional from the allowed list that people with similar
feelings often see. Never diagnose and never name a condition. If unsure, pick "primary"."""

# The exact JSON shape we want back: 1 to 3 keys from the visit types (not "other")
PROFESSIONALS_SCHEMA = {
    "type": "object",
    "properties": {"visits": {"type": "array",
                              "items": {"type": "string", "enum": [k for k in VISITS if k != "other"]}}},
    "required": ["visits"],
    "additionalProperties": False,
}


# Suggest 1 to 3 kinds of professional for what the person typed; Primary care doctor if there is
# no API key or anything goes wrong. The reason shown for each comes from VISITS (fixed sentences),
# not from the AI. Run the emergency check (is_urgent) before calling this.
def suggest_professionals(person, text, patterns, body):
    backup = {"visits": ["primary"], "source": "rules"}
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("No API key found, suggesting a primary care doctor")
        return backup
    details = json.dumps({"first_name": person["first_name"], "feelings": text[:500],
                          "changes": [c["words"] for c in patterns["changes"]],
                          "body_signals": [v["sentence"] for v in body]})
    try:
        answer = json.loads(ask_claude(PROFESSIONALS_SYSTEM, details, {"type": "json_schema", "schema": PROFESSIONALS_SCHEMA}))
        visits = list(dict.fromkeys(v for v in answer["visits"] if v in VISITS))[:3]
        if not visits:
            raise ValueError("No suggestions")
        return {"visits": visits, "source": "ai"}
    # Any error at all suggests a primary care doctor instead of crashing
    except Exception as error:
        print("AI professional suggestions failed, suggesting a primary care doctor:", type(error).__name__)
        return backup


# Instructions for Claude when suggesting steps for a routine
STEPS_SYSTEM = """You help a person break a home routine into small picture steps.
Write 3 to 6 short, concrete steps for the routine, in order. Each step is under 10 words,
starts with a verb, and is one simple action. Plain words, no advice beyond the steps."""

# The exact JSON shape we want back: a list of steps
STEPS_SCHEMA = {
    "type": "object",
    "properties": {"steps": {"type": "array", "items": {"type": "string"}}},
    "required": ["steps"],
    "additionalProperties": False,
}


# Suggest 3 to 6 short steps for a routine; sends only the routine name. If there is no API key or
# anything goes wrong, return an empty list so the person writes the steps they use.
def suggest_steps(routine):
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("No API key found, no step suggestions")
        return {"steps": [], "source": "rules"}
    try:
        answer = json.loads(ask_claude(STEPS_SYSTEM, routine, {"type": "json_schema", "schema": STEPS_SCHEMA}))
        steps = [s.strip()[:80] for s in answer["steps"] if s.strip()][:6]
        if len(steps) < 3:
            raise ValueError("Too few steps")
        return {"steps": steps, "source": "ai"}
    # Any error at all gives an empty list instead of crashing
    except Exception as error:
        print("AI step suggestions failed:", type(error).__name__)
        return {"steps": [], "source": "rules"}
