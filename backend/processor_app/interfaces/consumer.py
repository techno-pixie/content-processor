from abc import ABC, abstractmethod


class IConsumer(ABC):
    
    @abstractmethod
    async def start(self) -> None:
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        pass
    
    @abstractmethod
    async def is_running(self) -> bool:
        pass
