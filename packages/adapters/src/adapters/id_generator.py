from uuid import UUID

from uuid_extensions import uuid7


class IDGenerator:
    def generate(self) -> UUID:
        return uuid7()
