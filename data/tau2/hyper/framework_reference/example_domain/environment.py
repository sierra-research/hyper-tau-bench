"""Example domain: environment wiring."""

from typing import Optional

from .data_model import MockDB
from .tools import MockTools
from tau2.environment.environment import Environment


def get_environment(db: Optional[MockDB] = None) -> Environment:
    if db is None:
        db = MockDB.load("db.json")
    tools = MockTools(db)
    policy = open("policy.md").read()
    return Environment(domain_name="mock", policy=policy, tools=tools)
