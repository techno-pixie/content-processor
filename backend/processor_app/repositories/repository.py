from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession


class Repository(ABC):
    @abstractmethod
    def get_session(self) -> AsyncSession:
        pass
