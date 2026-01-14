from abc import ABC, abstractmethod


class IProducer(ABC):
    
    @abstractmethod
    def produce(self, submission_id: str, content: str) -> None:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
