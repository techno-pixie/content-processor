from typing import Optional, List
from datetime import datetime
import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import sqlalchemy
from processor_app.content_processor_service.schema import Submission, SubmissionStatus
from processor_app.repositories.repository import Repository
from processor_app.content_processor_service.request.content_request import ContentSubmissionRequest
from processor_app.interfaces.producer import IProducer

logger = logging.getLogger(__name__)

class ContentProcessorRepository:

    def __init__(self, repository: Repository, producer: Optional[IProducer] = None):
        self.repo = repository
        self.producer = producer

    def _get_session(self) -> AsyncSession:
        return self.repo.get_session()
    
    async def create(self, submission: ContentSubmissionRequest) -> Submission:
        try:
            async with self._get_session() as session:
                async with session.begin():
                    submission_id = str(uuid.uuid4())
                    submission = Submission(
                        id=submission_id,
                        content=submission.content,
                        status=SubmissionStatus.PENDING
                    )
                    session.add(submission)
                    await session.commit()
            
            if self.producer and self.producer.is_available():
                logger.info(f"[{submission_id}] Triggering producer for submission")
                self.producer.produce(submission_id, submission.content)
            
            return submission
        except sqlalchemy.exc.IntegrityError as e:
            raise e

    async def get_by_id(self, submission_id: str) -> Optional[Submission]:
        try:
            async with self._get_session() as session:
                async with session.begin():
                    return await self._get_by_id(session, submission_id)
        except sqlalchemy.exc.SQLAlchemyError as e:
            raise e
        

    async def update_status(
        self,
        submission_id: str,
        status: SubmissionStatus,
        processed_at: Optional[datetime] = None,
        processing_started_at: Optional[datetime] = None
    ) -> Optional[Submission]:
        try:
            async with self._get_session() as session:
                async with session.begin():
                    submission = await self._get_by_id(session, submission_id)
                    if submission:
                        submission.status = status
                        if processed_at:
                            submission.processed_at = processed_at
                        if processing_started_at:
                            submission.processing_started_at = processing_started_at
                        await session.commit()
                    return submission
        except sqlalchemy.exc.IntegrityError as e:
            raise e
        
    async def list_all(self) -> List[Submission]:
        try:
            async with self._get_session() as session:
                async with session.begin():
                    return await self._list_all(session)
        except sqlalchemy.exc.SQLAlchemyError as e:
            raise e
    
    @staticmethod
    async def _get_by_id(session: AsyncSession, submission_id: str) -> Optional[Submission]:
        result = await session.execute(
            select(Submission).filter(Submission.id == submission_id)
        )
        return result.scalars().first()
    
    @staticmethod
    async def _list_all(session: AsyncSession) -> List[Submission]:
        result = await session.execute(
            select(Submission).order_by(Submission.created_at.desc())
        )
        return result.scalars().all()
        
    async def get_pending(self) -> List[Submission]:
        try:
            async with self._get_session() as session:
                async with session.begin():
                    result = await session.execute(
                        select(Submission).filter(Submission.status == SubmissionStatus.PENDING)
                    )
                    return result.scalars().all()
        except sqlalchemy.exc.SQLAlchemyError as e:
            raise e
