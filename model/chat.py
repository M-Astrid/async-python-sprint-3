import json
from asyncio import StreamWriter
from dataclasses import dataclass

from mashumaro import DataClassDictMixin

from model.exceptions import InvalidMessageError

QUIT_CODE = 1


@dataclass
class Client:
    username: str
    writer: StreamWriter


@dataclass
class Message(DataClassDictMixin):
    data: str
    from_username: str | None = None
    to_username: str | None = None
    is_private: bool = False
    is_system: bool = False
    is_error: bool = False

    def to_bytes(self):
        return f"{json.dumps(self.to_dict())}\n".encode()

    @classmethod
    def from_bytes(cls, jsonb):
        data = json.loads(jsonb.strip())
        if not data["data"].strip():
            raise InvalidMessageError("Empty data")
        try:
            return cls(**data)
        except AttributeError as e:
            raise InvalidMessageError from e
