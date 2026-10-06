from datetime import datetime
from pydantic import BaseModel, Field, ValidationInfo, field_validator, StringConstraints
from typing import Annotated, Literal

class UserInput(BaseModel):
    request: Annotated[str, Field(min_length=5), StringConstraints(strip_whitespace=True)]

class Event(BaseModel):
    title: Annotated[str, Field(description="A small text description describing the event")]
    start_day_time: Annotated[datetime, Field(description="Start time")]
    end_day_time: Annotated[datetime | None, Field(description="End time")] = None
    location: Annotated[str | None, Field(description="Location of the event")] = None

    # Remove timezone from event to avoid timezone clashes
    @field_validator("start_day_time", "end_day_time")
    @classmethod
    def convert_to_local_timezone(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is not None:
            return v.astimezone().replace(tzinfo=None)
        return v

class AddEvent(Event):
    action: Literal["add"] = "add"

class RemoveEvent(BaseModel):
    action: Literal["remove"] = "remove"
    event_id: Annotated[str | None, Field(description="id of the event to remove, chosen from " \
        "the existing events list. null if no event matches the request")]

    @field_validator("event_id")
    @classmethod
    def must_be_existing_id(cls, v: str | None, info: ValidationInfo) -> str | None:
        # Make sure ids passed in exist
        valid_ids = (info.context or {}).get("valid_ids")
        if v is not None and valid_ids is not None and v not in valid_ids:
            raise ValueError(f"'{v}' is not an existing event id. Choose one of: {sorted(valid_ids)}, or null")
        return v

class CalendarCommand(BaseModel):
    command: Annotated[AddEvent | RemoveEvent, Field(discriminator="action")]
