"""Assistant-side operations on the task board."""

from data_model import ItemStatus, TaskBoardDB, Teammate, WorkItem

from tau2.environment.toolkit import ToolKitBase, ToolType, is_tool


class TaskBoardToolkit(ToolKitBase):
    """Operations the assistant may perform for a teammate."""

    db: TaskBoardDB

    def __init__(self, db: TaskBoardDB) -> None:
        super().__init__(db)

    @is_tool(ToolType.READ)
    def list_teammates(self) -> list[Teammate]:
        """
        List every teammate on the board with the items on their plate.

        Returns:
            All teammates.
        """
        return list(self.db.users.values())

    @is_tool(ToolType.WRITE)
    def open_work_item(
        self, user_id: str, title: str, description: str = None
    ) -> WorkItem:
        """
        Open a new work item on a teammate's plate.

        Args:
            user_id: The teammate the item belongs to.
            title: One-line summary of the work.
            description: Optional free-form detail.

        Returns:
            The newly opened work item.

        Raises:
            ValueError: If the teammate does not exist.
        """
        owner = self.db.require_teammate(user_id)
        # Item ids are ordinal over the whole board, matching the export.
        item_id = f"task_{len(self.db.tasks) + 1}"
        item = WorkItem(
            task_id=item_id,
            title=title,
            # Quick captures often have no detail; store an absent description
            # as absent rather than as an empty string.
            description=description or None,
            status="pending",
        )
        self.db.tasks[item_id] = item
        owner.tasks.append(item_id)
        return item

    @is_tool(ToolType.WRITE)
    def move_work_item(self, task_id: str, status: ItemStatus) -> WorkItem:
        """
        Move a work item to a different board column.

        Args:
            task_id: The id of the work item.
            status: The column to move it to.

        Returns:
            The updated work item.

        Raises:
            ValueError: If the work item does not exist.
        """
        item = self.db.require_item(task_id)
        item.status = status
        return item

    @is_tool(ToolType.GENERIC)
    def hand_off_to_support(self, summary: str) -> str:
        """
        Hand the conversation to the support rotation.

        Use only when the teammate explicitly asks for a person, or the
        request cannot be served with the operations above.

        Args:
            summary: A short handoff summary of the request so far.

        Returns:
            Confirmation that the handoff was recorded.
        """
        return "Handoff recorded"
