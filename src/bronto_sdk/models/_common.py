"""The shared response base and the audit block every persisted resource carries."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ReadModel(BaseModel):
    """Base for every response model: lenient about unknown fields."""

    model_config = ConfigDict(extra="allow")


class Identity(ReadModel):
    """The actor responsible for an operation on a resource.

    Attributes:
        type: The kind of actor. Known values are ``API_KEY`` and ``USER``.
        id: The actor's identifier — a user id or an API key id.
    """

    type: str | None = None
    id: str | None = None


class ResourceMetadata(ReadModel):
    """The audit block attached to every persisted Bronto resource.

    Every timestamp is epoch milliseconds typed ``int`` — never ``float``,
    which silently rounds values above 2**53.

    Attributes:
        created_at: Creation time in epoch milliseconds.
        created_by: The actor that created the resource.
        modified_at: Last-update time in epoch milliseconds.
        modified_by: The actor that last modified the resource.
        deleted_at: Deletion time in epoch milliseconds.
        deleted_by: The actor that deleted the resource.
        last_heartbeat_at: Time of the last ingest heartbeat in epoch
            milliseconds. Absent on a dataset that has never received data.
    """

    created_at: int | None = None
    created_by: Identity | None = None
    modified_at: int | None = None
    modified_by: Identity | None = None
    deleted_at: int | None = None
    deleted_by: Identity | None = None
    last_heartbeat_at: int | None = None
