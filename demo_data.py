"""Typed access to fictional demo records through a replaceable data-source interface."""

import json
import os
from datetime import date, datetime, timedelta
from typing import Optional, Protocol, TypedDict


class DemoData(TypedDict):
    """The shared record groups exposed to pages, regardless of storage source."""
    member: dict
    professionals: list
    circle: list
    activities: list
    health_follow_ups: list
    check_ins: list
    connected_sources: list
    appointment_packets: list


class DemoDataProvider(Protocol):
    """The small interface a fixture, API, or database provider can implement."""

    def load(self) -> DemoData:
        """Return all records used by the demonstration experience."""
        ...


class JsonDemoDataProvider:
    """Load the fictional demonstration records from the checked-in JSON fixture."""

    def __init__(self, path=None):
        """Keep the fixture path configurable for tests and alternate local fixtures."""
        self.path = path or os.path.join(os.path.dirname(__file__), "data", "demo_records.json")

    def load(self) -> DemoData:
        """Read the fixture without coupling presentation code to JSON or file paths."""
        with open(self.path, encoding="utf-8") as fixture:
            return json.load(fixture)


def load_demo_data(provider: Optional[DemoDataProvider] = None) -> DemoData:
    """Use the default JSON fixture or an injected provider with the same interface."""
    return (provider or JsonDemoDataProvider()).load()


def plan_activities(records, today, time_filter="today", source_filter="all", progress=None):
    """Return activities and accepted Health follow-ups matching the selected filters."""
    current = date.fromisoformat(today)
    tomorrow = current + timedelta(days=1)
    week_end = current + timedelta(days=6 - current.weekday())
    sources = {"all", "member", "coach", "health"}
    times = {"today", "tomorrow", "this_week", "later"}
    source_filter = source_filter if source_filter in sources else "all"
    time_filter = time_filter if time_filter in times else "today"
    rows = []

    progress = progress or {}
    for activity in records["activities"]:
        saved = progress.get(activity["id"], {})
        rows.append({**activity, **saved, "source_label": {
            "member": "Added by me", "coach": "From my coach"}.get(activity["source"], activity["source"])})
    for follow_up in records["health_follow_ups"]:
        if follow_up["status"] == "accepted":
            rows.append({
                "id": follow_up["id"], "title": follow_up["instruction"], "source": "health",
                "source_name": follow_up["source_name"], "source_label": "From Health",
                "due_on": follow_up["due_on"], "scheduled_for": "",
                "estimated_minutes": follow_up.get("estimated_minutes", 10),
                "status": "accepted", "next_action": "Review the details in Health",
                "health_link": f"/health/next-steps#{follow_up['id']}",
            })

    visible = []
    for item in rows:
        planned_day = date.fromisoformat(item["due_on"] or item["scheduled_for"][:10])
        if time_filter == "today" and planned_day != current:
            continue
        if time_filter == "tomorrow" and planned_day != tomorrow:
            continue
        if time_filter == "this_week" and not current <= planned_day <= week_end:
            continue
        if time_filter == "later" and planned_day <= week_end:
            continue
        if source_filter != "all" and item["source"] != source_filter:
            continue

        item["date_label"] = f"{planned_day:%A}, {planned_day:%B} {planned_day.day}"
        if item["scheduled_for"]:
            scheduled = datetime.fromisoformat(item["scheduled_for"])
            item["date_label"] += f" · {scheduled:%I:%M %p}".replace(" 0", " ")
        item["status_label"] = item["status"].replace("_", " ").capitalize()
        visible.append(item)

    return sorted(visible,
                  key=lambda item: (item["due_on"] or item["scheduled_for"][:10], item["scheduled_for"]))
