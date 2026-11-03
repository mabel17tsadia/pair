# Pair

A web app for the North American AI Challenge, built with Flask and with our challenge partner
**First Place AZ** in mind.

## What Pair does

Pair connects, with consent, to devices a person already uses (phone first; optionally a smart
washer, a mattress sensor, a smart ring or watch, or a glucose monitor). It learns the person's
own usual patterns, notices when several patterns change together, and **tells the person first**,
in plain language. The person then chooses what each member of their trust circle can see.

- **Today:** the week's status ("Steady week", "A few changes", "Several changes"), what Pair
  noticed, body signals, a routine note (for example "No laundry in 13 days"), one gentle step,
  and a small climb card.
- **Climb:** personal weekly goals shown as flags on a mountain, with a summit celebration and
  badges. Personal only: never compared or ranked.
- **Check in:** pick a mood; Pair puts it side by side with what patterns and devices show.
- **Circle:** five sharing levels, a share preview, and nothing is ever sent without the person.
- **Me:** profile, routines with picture steps, patterns, body signals, paired devices,
  getting ready for an appointment, and settings.

Pair **does not diagnose** and is **not a task planner**.

## Who it is for

Adults who want to notice early when their week is getting harder, and who want to decide
themselves who hears about it: family, a friend, a life skills coach or 360 wellness staff, or a
doctor. It is designed to be calm and readable for someone who is easily overwhelmed: large tap
targets, short sentences, three themes, no red, and celebrations that respect reduced motion.

## Partner research that shaped it

> **To fill in by the team:** the findings from our conversations with First Place AZ
> (who we spoke to, what they told us, and which features came from it).

What the app already reflects:
- The weekly climb is inspired by First Place's **Vertical Miles Challenge** poster.
- Out of scope on purpose: task lists, adding tasks, an inbox, requiring a wearable, and medical
  devices such as pacemakers.

## The patterns rule

"Recent" is the last 5 days; "usual" is all earlier days. With fewer than 10 days Pair says
"Still learning your usual". A signal is only checked if a paired device provides it.

| Signal | Counts as a change when the last 5 days are… |
|---|---|
| Sleep | 45 or more minutes less than usual |
| Steps | 25% or more lower |
| Phone time late at night | 30 or more minutes higher |
| Phone pickups (unlocks) | 25% or more higher |
| Time away from home | 30% or more lower (only if "Time away from home" is paired) |

**Status:** 0 or 1 changes = Steady week, 2 = A few changes, 3 or more = Several changes.
**Notes:** steps 15% or more above usual add "You moved more than usual this week"; a paired washer
with no laundry for 10 or more days adds a routine note. Body signals (resting heart rate, glucose)
are shown separately and never change the week status. All thresholds are named at the top of
[patterns.py](patterns.py) and [vitals.py](vitals.py).

## What data is simulated

All device data is simulated from CSV files in [data/](data/): `people.csv`, `signals.csv`
(21 days of sleep, steps, screen time, unlocks, time out, laundry), `devices.csv`, `vitals.csv`
(resting heart rate and glucose), `checkins.csv`, `circle.csv`, `goals.csv` and `routines.csv`.
The demo "today" is the latest date in `signals.csv`, so the demo works on any day.
Everything a person changes (pairing, circle, goals, routines, check ins, sign up) is kept in the
Flask session only, and the CSV files never change. The only real connection is the optional
Google Health sign in (testing mode), which is not used for patterns yet.

## How AI is used, and the backup

Pair uses Claude Haiku 5.5 through the Anthropic API ([ai.py](ai.py), one `ask_claude` helper).
Every AI feature has a **rule based backup** that runs when there is no API key or anything fails,
and the page shows **"Written with AI"** or **"Written by rules"** so you can see which ran.

| Feature | AI writes | Backup |
|---|---|---|
| Today | A 2 to 3 sentence week summary and one gentle step | One short sentence and the first "calms" item |
| Check in | 2 sentences and a suggestion that put the mood next to the facts | Fixed messages for each mood and signals case |
| Appointment summary | A neutral paragraph a professional can scan in 30 seconds | The same facts in fixed sentences |
| Questions to ask | 3 to 5 questions in the person's voice, fitted to the visit type | 3 general questions per visit type |
| Not sure who to see? | Picks 1 to 3 kinds of professional (the reasons are fixed text) | Primary care doctor |
| Routines | 3 to 6 short steps for a routine | An empty list to write your own |

**Safety rules:** AI never diagnoses and never suggests food, medicine or doses (a check in answer
that mentions them is replaced by the rules answer; for glucose it only says "follow your care
plan"). Emergency words in a note ("chest pain", "can't breathe", "hurt myself", "suicide",
"kill myself") are checked by rules **before** any AI call and show only 911 and 988.
**What is sent:** only the first name, calms (and drains for the week summary), the mood, mood and
body feeling counts, the week status, plain change and body signal sentences, the visit type, and
on "Not sure who to see?" the text the person types there. Never last names, check in notes or
device names. Week and appointment
summaries are cached once per person per day.

## Privacy choices

- Pair only reads what the person pairs, after a consent page that says what it reads, what it
  never reads (messages, photos, exact places, who you call) and that they can stop at any time.
- Time away from home is only minutes, never a map, and is never shared at any level.
- Check in notes are never shared and never sent to AI.
- Circle levels: Just in my circle (sees nothing, the default), Cheers me on, Weekly summary,
  Wellness details, Health summary. Sharing always shows a preview with every box unticked.
- Readings from devices can never be edited; things the person types are labelled "Entered by …".
- API keys live only in `.env`. The Google token is kept in server memory, never in a cookie or file.

## How to run (Windows PowerShell)

1. Create the virtual environment (first time only): `python -m venv venv`
2. Turn it on: `venv\Scripts\Activate.ps1`
3. Install the packages (first time only): `pip install -r requirements.txt`
4. Start the app: `python app.py`
5. Open http://127.0.0.1:5000, pick a demo person (Jordan, Maya or Theo), or tap
   **New to Pair? Get started**.

API keys go in a `.env` file, which is never committed. It needs:
```
ANTHROPIC_API_KEY=your-key
SECRET_KEY=any-long-random-text
```
Without `ANTHROPIC_API_KEY` the app still works and uses the rule based backups.

Optional, for Google Health in Settings > Demo controls (Google Cloud project in testing mode):
```
GOOGLE_CLIENT_ID=your-web-client-id
GOOGLE_CLIENT_SECRET=your-web-client-secret
```
In Google Cloud, add `http://127.0.0.1:5000/google/callback` as an authorized redirect URI and add
each tester's email as a test user.

## How we used AI to build this

We built Pair one stage at a time with Claude Code as a coding assistant, following the rules in
[CLAUDE.md](CLAUDE.md): short readable code, one feature per stage, a plain English comment above
every function and template section, no new libraries without asking, and no keys or real personal
data in the code. Every prompt we gave, stage by stage, is in
[notes/prompts-log.md](notes/prompts-log.md), and what we tested is in
[notes/testing-log.md](notes/testing-log.md).
