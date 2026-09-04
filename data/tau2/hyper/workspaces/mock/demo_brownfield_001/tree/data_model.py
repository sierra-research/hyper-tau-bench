"""Task-board data layer.

The production export is a two-table JSON document: work items keyed by id,
and teammates keyed by id with the ids of the items on their plate. Field
names follow the export, not our internal naming — do not rename them.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from tau2.environment.db import DB

ItemStatus = Literal["pending", "completed"]


class WorkItem(BaseModel):
    task_id: str = Field(description="Stable id of the work item")
    title: str = Field(description="One-line summary")
    description: Optional[str] = Field(
        None, description="Free-form detail; often absent on quick captures"
    )
    status: ItemStatus = Field(description="Current board column")


class Teammate(BaseModel):
    user_id: str = Field(description="Stable id of the teammate")
    name: str = Field(description="Display name")
    tasks: List[str] = Field(description="Ids of items on this teammate's plate")


class TaskBoardDB(DB):
    """The task board as loaded from the production export."""

    tasks: Dict[str, WorkItem] = Field(description="Work items keyed by id")
    users: Dict[str, Teammate] = Field(description="Teammates keyed by id")

    def require_item(self, item_id: str) -> WorkItem:
        if item_id not in self.tasks:
            raise ValueError(f"No work item with id {item_id}")
        return self.tasks[item_id]

    def require_teammate(self, teammate_id: str) -> Teammate:
        if teammate_id not in self.users:
            raise ValueError(f"No teammate with id {teammate_id}")
        return self.users[teammate_id]
