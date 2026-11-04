"""Typed access to fictional demo records through a replaceable data-source interface."""

import json
import os
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
