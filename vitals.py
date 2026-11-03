import data
from patterns import RECENT_DAYS, MIN_DAYS

# The vitals shown on My body signals: column -> (name, the device signal that provides it)
VITALS = {"resting_hr": ("Resting heart rate", "resting heart rate"),
          "glucose_avg": ("Glucose", "glucose")}
HR_CLOSE_BEATS = 3   # a resting heart rate within 3 beats of usual counts as "close to your usual"
LOW_DAYS = 7         # low glucose readings are counted over the last 7 days


# Each paired vital: daily values, usual (earlier days average), recent (last 5 days average),
# the latest value, the device it comes from, one plain sentence, short facts for Check in, and
# "changed" (heart rate not close to usual, or any low glucose reading this week).
# Sentences only describe: never "good" or "bad", and never advice about food, medicine or doses.
def get_body_signals(person_id, devices=None):
    devices = devices if devices is not None else data.get_devices(person_id)
    rows = data.get_vitals(person_id, devices)
    source = {s: d["device"] for d in devices if d["paired"] for s in d["signals"]}
    signals = []
    for col, (name, signal) in VITALS.items():
        days = [r for r in rows if col in r]
        if len(days) < MIN_DAYS:
            continue
        values = [round(float(r[col])) for r in days]
        usual = sum(values[:-RECENT_DAYS]) / (len(values) - RECENT_DAYS)
        recent = sum(values[-RECENT_DAYS:]) / RECENT_DAYS

        lows = 0
        if col == "resting_hr":
            latest = values[-1]
            diff = round(recent - usual)
            changed = abs(diff) >= HR_CLOSE_BEATS
            if not changed:
                sentence = "Resting heart rate is close to your usual."
                facts = ["Resting heart rate close to your usual"]
            else:
                more = "higher" if diff > 0 else "lower"
                sentence = f"Resting heart rate is about {abs(diff)} beats {more} than your usual."
                facts = [f"Resting heart rate about {abs(diff)} beats {more} than usual"]
        else:
            latest = round(float(days[-1]["glucose_last"]))
            lows = round(sum(float(r["glucose_lows"]) for r in days[-LOW_DAYS:]))
            changed = lows > 0
            count = "no low readings" if lows == 0 else f"{lows} low reading{'s' if lows != 1 else ''}"
            sentence = f"Your monitor showed {count} this week. Your latest reading is {latest}."
            facts = [f"Latest glucose reading {latest}"] + ([f"{lows} low glucose reading{'s' if lows != 1 else ''} this week"] if lows else [])

        signals.append({"signal": col, "name": name, "dates": [r["date"] for r in days], "values": values,
                        "usual": usual, "recent": recent, "latest": latest, "sentence": sentence,
                        "facts": facts, "changed": changed, "lows": lows, "source": source[signal]})
    return signals
