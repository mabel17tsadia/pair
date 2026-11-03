from patterns import SIGNALS

# Every signal Pair can tell a professional about (daily patterns and body signals)
ALL_SIGNALS = ["sleep_min", "steps", "late_screen_min", "unlocks", "time_out_min", "resting_hr", "glucose_avg"]

# The kinds of professional a person can get ready to see: the label on the choice card, why people
# often see them (for "Not sure who to see?"), which signals are worth telling them about, and
# 3 general questions (the rule based backup for "Suggest questions")
VISITS = {
    "primary": {
        "label": "Primary care doctor",
        "why": "People often start here for most health questions, and to be pointed to the right specialist.",
        "signals": ALL_SIGNALS,
        "questions": ["Is there anything in these changes you would like me to keep an eye on?",
                      "What would be a good next step for me?",
                      "When should I come back or get in touch?"]},
    "dietitian": {
        "label": "Dietitian",
        "why": "People often see a dietitian for help with food, energy and blood sugar.",
        "signals": ["glucose_avg", "steps"],
        "questions": ["Is there anything in my week you would like me to track before next time?",
                      "How can I plan meals around my usual day?",
                      "Who should I contact if my readings change?"]},
    "endo": {
        "label": "Diabetes or hormone doctor (endocrinologist)",
        "why": "People often see an endocrinologist about diabetes, blood sugar or hormones.",
        "signals": ["glucose_avg", "resting_hr", "sleep_min"],
        "questions": ["What would you like me to watch in my monitor readings?",
                      "How should I follow my care plan on busy days?",
                      "When should I contact your team between visits?"]},
    "womens": {
        "label": "Women's health (gynecologist)",
        "why": "People often see a gynecologist about periods, pregnancy and other women's health questions.",
        "signals": ["sleep_min", "resting_hr"],
        "questions": ["Is there anything in these changes you would like me to track?",
                      "What should I note down before my next visit?",
                      "When should I get in touch between visits?"]},
    "therapist": {
        "label": "Therapist or counselor",
        "why": "People often see a therapist or counselor when they feel worried, low or overwhelmed for a while.",
        "signals": ["sleep_min", "steps", "late_screen_min", "unlocks", "time_out_min"],
        "questions": ["How can I notice early when my week is getting harder?",
                      "What could I try on days I feel overwhelmed?",
                      "How often should we meet for now?"]},
    "dentist": {
        "label": "Dentist",
        "why": "People often see a dentist for teeth, gums or mouth pain.",
        "signals": [],
        "questions": ["Is there anything I should do differently at home?",
                      "When should I come back?",
                      "Who do I call if I have pain before then?"]},
    "other": {
        "label": "Other",
        "why": "Any other health professional.",
        "signals": ALL_SIGNALS,
        "questions": ["Is there anything in these changes you would like me to keep an eye on?",
                      "What would be a good next step for me?",
                      "When should I come back or get in touch?"]},
}


# The change and body sentences worth telling this professional, each with the device it came from
# (read only: these come straight from paired devices)
def things_to_tell(visit, patterns, body, devices):
    keep = VISITS[visit]["signals"]
    device_for = {s: d["device"] for d in devices if d["paired"] for s in d["signals"]}
    items = [{"text": c["words"], "source": device_for.get(SIGNALS[c["signal"]][1], "My phone")}
             for c in patterns["changes"] if c["signal"] in keep]
    items += [{"text": v["sentence"], "source": v["source"]} for v in body if v["signal"] in keep]
    return items
