from abc import ABC, abstractmethod


class IContentValidator(ABC):

    @abstractmethod
    def validate(self, content: str) -> bool:
        pass
