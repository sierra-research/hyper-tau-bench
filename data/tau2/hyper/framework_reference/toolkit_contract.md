# Toolkit & Database Contract

Your domain needs two Python files: `data_model.py` (database schema) and
`tools.py` (the toolkit the agent calls).

---

## Database (`data_model.py`)

Your database class must inherit from `tau2.environment.db.DB`, which is a
Pydantic `BaseModel`. It represents the entire domain state as a JSON-
serializable model.

```python
from pydantic import BaseModel, Field
from tau2.environment.db import DB

class User(BaseModel):
    user_id: str = Field(description="Unique user identifier")
    name: str = Field(description="User's name")

class MyDomainDB(DB):
    """Database for my domain."""
    users: list[User] = Field(description="All users")
```

The DB is loaded from the structured database file present in `database/` at
startup. The file may be JSON, TOML, YAML, or YML; use the extension that
actually exists in the kit:

```python
db = MyDomainDB.load("path/to/database/db.toml")  # or db.json/db.yaml/db.yml
```

The raw loaded structure must validate against your Pydantic model. This
matters in two places:

1. Startup loads `database/db.{json,toml,yaml,yml}` (whichever exists) through
   your `DB.load(...)` method.
2. Task setup replay updates the DB through `ToolKitBase.update_db(...)`, which
   merges update data and then calls `YourDB.model_validate(...)` directly.

Construction kits may also include `database/schema.json`. When present, this
file is the public assistant database contract: legal developer-owned top-level
tables, table shapes, fields, JSON types, and stable enum-like values that are
not fully visible in the baseline database. It is not task setup data and does
not contain concrete deployment data or customer-side runtime state.
Your DB models should accept states that conform to this schema through
`ToolKitBase.update_db(...)`.

Because setup replay does not call your custom `load(...)` method, do not rely
on `load(...)` as the only place where raw database shapes are normalized. If
the database file stores records as lists, the simplest robust approach is to
model those fields as lists and add helper lookup methods in your toolkit or DB.
If you prefer dictionary lookup tables internally, add a Pydantic
`@model_validator(mode="before")` so both startup and setup replay accept the
raw list-shaped data.

Use `Field(description=...)` on every field — these descriptions appear in
error messages and documentation.

```python
from pydantic import Field, model_validator
from tau2.environment.db import DB

class MyDomainDB(DB):
    """Database that accepts raw list-shaped data and stores lookup tables."""

    users: dict[str, User] = Field(description="Users keyed by user_id")

    @model_validator(mode="before")
    @classmethod
    def normalize_raw_tables(cls, data):
        if isinstance(data, dict) and isinstance(data.get("users"), list):
            data = dict(data)
            data["users"] = {user["user_id"]: user for user in data["users"]}
        return data
```

### Tips

- Match the raw database shape unless you also add a `model_validator` that
  accepts the raw shape during setup replay.
- Use `dict[str, Model]` for lookup tables only when your model can validate
  raw task setup updates as well as startup loads.
- If `database/schema.json` is present, make sure the assistant-side DB model
  accepts the documented tables and fields too. Task initialization can legally
  populate developer-owned fields that are absent from the baseline database
  file. Host-owned user/customer simulator state is not part of this contract.
- Use `Literal` types for enums (e.g., `Literal["pending", "completed"]`)
- Use `Union` types when a field can have different shapes depending on a
  discriminator (e.g., flight status varies by whether the flight is
  available, delayed, cancelled, etc.)
- Use `Optional[T]` for fields that may be absent
- The DB is mutable during a simulation — your tools modify it in place

---

## Toolkit (`tools.py`)

Your toolkit class must inherit from `tau2.environment.toolkit.ToolKitBase`.
This is a metaclass-powered base that auto-discovers methods decorated with
`@is_tool`.

```python
from tau2.environment.toolkit import ToolKitBase, ToolType, is_tool

class MyTools(ToolKitBase):
    db: MyDomainDB

    def __init__(self, db: MyDomainDB) -> None:
        super().__init__(db)

    @is_tool(ToolType.READ)
    def get_user(self, user_id: str) -> User:
        """
        Look up a user by ID.

        Args:
            user_id: The user's unique identifier.

        Returns:
            The user profile.

        Raises:
            ValueError: If the user is not found.
        """
        if user_id not in self.db.users:
            raise ValueError(f"User {user_id} not found")
        return self.db.users[user_id]
```

### The `@is_tool` decorator

Every method you want exposed to the agent as a callable tool must be
decorated with `@is_tool(tool_type)` where `tool_type` is one of:

- `ToolType.READ` — queries data without side effects
- `ToolType.WRITE` — creates, updates, or deletes data
- `ToolType.GENERIC` — utility functions (calculator, transfer to human, etc.)
- `ToolType.THINK` — internal reasoning (no side effects, no new data)

The tool type classification affects normal evaluation replay. WRITE tools are
re-executed when the framework reconstructs your generated environment from
its own trajectory; READ tools are skipped. Construction-mode environment
assertions are scored from the final DB/user-DB state, not by replaying your
generated public tool names through an internal toolkit.

Because WRITE tools are re-executed, they must be **deterministic**: given the
same arguments and the same database state, a tool must return byte-identical
output every time. Do not use unseeded randomness (`random`, `uuid`, `secrets`)
or wall-clock time (`datetime.now()`) to generate ids, timestamps, or any other
returned value — a replayed call that returns different content than the
recorded one fails evaluation for that entire task. Derive new ids from the
database state instead (e.g. a counter, or a hash of the request contents).

### Docstrings matter

The method's docstring becomes the tool description the agent sees. Write
it in this format:

```
Short description of what the tool does.

Args:
    param_name: Description of the parameter.

Returns:
    What the tool returns.

Raises:
    ValueError: When something goes wrong.
```

The `Args:` section is parsed to generate parameter descriptions in the
tool schema. Be precise — this is what the LLM reads to decide how to
call your tool.

### Return types

Tools can return:
- Pydantic models (serialized to JSON automatically)
- Strings
- Lists of models
- Dicts

### Private helpers

Methods that do NOT have `@is_tool` are private helpers — they won't be
exposed to the agent. Use them for shared logic (e.g., a private
`_get_user` method that multiple tools call).

### Error handling

Raise `ValueError` with a clear message when a tool call is invalid
(user not found, insufficient balance, etc.). The error message is
returned to the agent, which can then communicate it to the customer.

---

## Putting it together

The framework instantiates your toolkit with the loaded database, then
extracts the tools for the agent:

```python
db = MyDomainDB.load("database/db.toml")  # use the file that exists in your kit
toolkit = MyTools(db)
tools = toolkit.get_tools()  # dict of Tool objects from @is_tool methods
```

The agent receives these tools as callable functions. When the agent calls
a tool, the framework invokes the corresponding method on your toolkit
instance, passing the arguments the agent provided. The return value is
serialized and sent back to the agent.
