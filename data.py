import os
import pandas as pd

# Folder that holds the demo CSV files
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


# Read one CSV file from the data folder (empty cells become "")
def read_csv(name):
    return pd.read_csv(os.path.join(DATA_DIR, name)).fillna("")


# Turn "a|b|c" into ["a", "b", "c"] (an empty cell becomes [])
def split_list(value):
    return value.split("|") if value else []


# Get one person's rows from a CSV file as a list of dictionaries
def rows_for(name, person_id):
    df = read_csv(name)
    return df[df["person_id"] == person_id].to_dict("records")


# All demo people (id, first_name, last_name), with drains and calms as lists
def get_people():
    people = read_csv("people.csv").to_dict("records")
    for p in people:
        p["drains"] = split_list(p["drains"])
        p["calms"] = split_list(p["calms"])
    return people


# One person by id, or None if there is no such person
def get_person(person_id):
    for p in get_people():
        if p["id"] == person_id:
            return p
    return None


# A person's trust circle: name, relationship, level (access) and whether they can add routines
def get_circle(person_id):
    circle = rows_for("circle.csv", person_id)
    for c in circle:
        c["routines"] = c["routines"] == "yes"
    return circle


# A person's daily signals (sleep, steps, screen time, unlocks, time out, laundry), oldest first
def get_signals(person_id):
    return sorted(rows_for("signals.csv", person_id), key=lambda s: s["date"])


# A person's devices, with signals as a list and paired as True or False
def get_devices(person_id):
    devices = rows_for("devices.csv", person_id)
    for d in devices:
        d["signals"] = split_list(d["signals"])
        d["paired"] = d["paired"] == "yes"
    return devices


# A person's check ins, oldest first (newest last), with body feelings as a list
def get_checkins(person_id):
    checkins = sorted(rows_for("checkins.csv", person_id), key=lambda c: c["date"])
    for c in checkins:
        c["body"] = split_list(c["body"])
    return checkins


# The latest date in signals.csv; the app treats it as "today" so the demo works on any day
def get_today():
    return read_csv("signals.csv")["date"].max()


# A person's weekly goals (goal, kind, rule, target, added_by) in the order they were added
def get_goals(person_id):
    return rows_for("goals.csv", person_id)


# A person's routines (routine, steps as a list, added_by) for the picture steps screen
def get_routines(person_id):
    routines = rows_for("routines.csv", person_id)
    for r in routines:
        r["steps"] = split_list(r["steps"])
    return routines


# Each vitals column and the device signal it needs ("resting heart rate" or "glucose")
VITAL_SIGNALS = {"resting_hr": "resting heart rate", "glucose_avg": "glucose",
                 "glucose_lows": "glucose", "glucose_last": "glucose"}


# A person's vitals by date (oldest first), with only the columns a paired device provides.
# "devices" are the person's current pairing choices; if not given, devices.csv is used.
def get_vitals(person_id, devices=None):
    devices = devices if devices is not None else get_devices(person_id)
    paired = {s for d in devices if d["paired"] for s in d["signals"]}
    keep = [col for col, signal in VITAL_SIGNALS.items() if signal in paired]
    if not keep:
        return []
    rows = sorted(rows_for("vitals.csv", person_id), key=lambda r: r["date"])
    return [{"date": r["date"], **{col: r[col] for col in keep if r[col] != ""}} for r in rows]
