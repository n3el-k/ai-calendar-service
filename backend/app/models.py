from datetime import datetime
from pydantic import AfterValidator, BaseModel, Field, ValidationInfo, field_validator, StringConstraints, model_validator
from typing import Annotated, Literal, Self, Any

class UserInput(BaseModel):
    request: Annotated[str, Field(min_length=5), StringConstraints(strip_whitespace=True)]

# Shared validators
def _to_local_naive(v: datetime) -> datetime:
    # Remove timezone from datetimes to avoid timezone clashes
    if v.tzinfo is not None:
        return v.astimezone().replace(tzinfo=None)
    return v

LocalDatetime = Annotated[datetime, AfterValidator(_to_local_naive)]

def _check_end_after_start(start: datetime | None, end: datetime | None) -> None:
    if start is not None and end is not None and end < start:
        raise ValueError("Invalid timings. End time is before start time for event")
    

class Event(BaseModel):
    title: Annotated[str, Field(description="A small text description describing the event")]
    start_day_time: Annotated[LocalDatetime, Field(description="Start time")]
    end_day_time: Annotated[LocalDatetime | None, Field(description="End time")] = None
    location: Annotated[str | None, Field(description="Location of the event")] = None

    @model_validator(mode='after')
    def check_day_time(self) -> Self:
        _check_end_after_start(self.start_day_time, self.end_day_time)
        return self

class TargetEvent(BaseModel):
    event_id: Annotated[str | None, Field(description="id of the existing event this applies to, "
        "chosen from the existing events list. null if no event matches")]

    @field_validator("event_id")
    @classmethod
    def must_be_existing_id(cls, v, info: ValidationInfo):
        # Make sure ids passed in exist
        valid_ids = (info.context or {}).get("valid_ids")
        if v is not None and valid_ids is not None and v not in valid_ids:
            raise ValueError(f"'{v}' is not an existing event id. Choose one of: {sorted(valid_ids)}, or null")
        return v

class AddEvent(Event):
    action: Literal["add"] = "add"

class UpdateEvent(TargetEvent):
    action: Literal["update"] = "update"
    title: Annotated[str | None, Field(description="New title for the event, or null to leave it unchanged")] = None
    start_day_time: Annotated[LocalDatetime | None, Field(description="New start time, or null to leave it unchanged")] = None
    end_day_time: Annotated[LocalDatetime | None, Field(description="New end time, or null to leave it unchanged")] = None
    location: Annotated[str | None, Field(description="New location, or null to leave it unchanged")] = None

    @model_validator(mode='after')
    def check_day_time(self) -> Self:
        # not a full test as we need to compare the values in the db if they arent being changed here
        _check_end_after_start(self.start_day_time, self.end_day_time)
        return self

class RemoveEvent(TargetEvent):
    action: Literal["remove"] = "remove"

class SearchFilters(BaseModel):
    # Input for the agent's search_events tool; every filter is optional
    query: str | None = None
    start_time: LocalDatetime | None = None
    end_time: LocalDatetime | None = None

class CalendarCommand(BaseModel):
    command: Annotated[AddEvent | RemoveEvent | UpdateEvent, Field(discriminator="action")]

# Agent models
class AgentActions(BaseModel):

    tool: str
    input: dict[str, Any]
    is_error: bool

class PendingAction(BaseModel):

    action: Literal["add", "update"] # wont be remove, no need to put remove into pending.
    event_id: str | None
    event: Event

class AgentResponse(BaseModel):

    reply: str
    truncated: bool
    actions: list[AgentActions]
    pending: PendingAction | None
