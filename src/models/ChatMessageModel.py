from .BaseDataModel import BaseDataModel
from .db_schemes import ChatMessage
from sqlalchemy.future import select
from sqlalchemy import delete


class ChatMessageModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_client = db_client

    @classmethod
    async def create_instance(cls, db_client: object):
        return cls(db_client)

    async def create_chat_message(
        self,
        *,
        session_id: str,
        project_id: int,
        role: str,
        content: dict,
    ) -> ChatMessage:
        message = ChatMessage(
            session_id=session_id,
            project_id=project_id,
            role=role,
            content=content,
        )

        async with self.db_client() as session:
            async with session.begin():
                session.add(message)
            await session.commit()
            await session.refresh(message)

        return message

    async def get_chat_history(
        self,
        *,
        session_id: str,
        project_id: int,
        limit: int = 20,
    ) -> list[ChatMessage]:
        async with self.db_client() as session:
            stmt = (
                select(ChatMessage)
                .where(
                    ChatMessage.session_id == session_id,
                    ChatMessage.project_id == project_id,
                )
                .order_by(ChatMessage.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            messages = result.scalars().all()

        return list(reversed(messages))

    async def clear_chat_history(self, *, session_id: str, project_id: int) -> int:
        async with self.db_client() as session:
            stmt = delete(ChatMessage).where(
                ChatMessage.session_id == session_id,
                ChatMessage.project_id == project_id,
            )
            result = await session.execute(stmt)
            await session.commit()

        return result.rowcount
