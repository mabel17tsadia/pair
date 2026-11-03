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


# A person's sleep and steps for the last 7 days
def get_daily(person_id):
    return rows_for("daily.csv", person_id)


# A person's heart rate readings for today (every 15 minutes)
def get_heart(person_id):
    return rows_for("heart.csv", person_id)


# A person's tasks for today, with steps as a list
def get_tasks(person_id):
    tasks = rows_for("tasks.csv", person_id)
    for t in tasks:
        t["steps"] = split_list(t["steps"])
    return tasks


# A person's inbox messages, each with a suggested task
def get_inbox(person_id):
    return rows_for("inbox.csv", person_id)


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
