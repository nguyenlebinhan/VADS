from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat.models import ChatMessage, ChatRole, ChatSession, ChatSessionStatus
from app.chat.qa_pipeline import QuestionAnsweringPipeline
from app.chat.schemas import (
    AnswerSchema,
    ChatExchangeData,
    ChatMessageData,
    ChatQuestionRequest,
    ChatSessionCreate,
    ChatSessionData,
    DeleteChatSessionData,
)
from app.exceptions import NotFoundError


class ChatService:
    def __init__(self, session: Session, *, qa_pipeline: QuestionAnsweringPipeline) -> None:
        self.session = session
        self.qa_pipeline = qa_pipeline

    def create_session(
        self,
        workspace_id: str,
        payload: ChatSessionCreate,
    ) -> ChatSessionData:
        session = ChatSession(
            workspace_id=workspace_id,
            title=payload.title.strip() if payload.title else None,
            is_private=payload.is_private,
        )
        self.session.add(session)
        self.session.commit()
        self.session.refresh(session)
        return ChatSessionData.model_validate(session)

    def get_session(self, session_id: str) -> ChatSessionData:
        return ChatSessionData.model_validate(self._active_session(session_id))

    def list_messages(self, session_id: str) -> list[ChatMessageData]:
        self._active_session(session_id)
        messages = self.session.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        return [self._message_data(message) for message in messages]

    def ask(self, session_id: str, payload: ChatQuestionRequest) -> ChatExchangeData:
        chat_session = self._active_session(session_id)
        question = payload.question.strip()
        user_message = ChatMessage(
            session_id=session_id,
            role=ChatRole.USER,
            content=question,
            document_ids=payload.document_ids,
        )
        if chat_session.title is None:
            chat_session.title = question[:120]
        self.session.add(user_message)
        self.session.commit()
        self.session.refresh(user_message)

        answer = self.qa_pipeline.answer(
            question,
            workspace_id=chat_session.workspace_id,
            document_ids=payload.document_ids,
            private=chat_session.is_private,
        )
        assistant_message = ChatMessage(
            session_id=session_id,
            role=ChatRole.ASSISTANT,
            content=answer.answer,
            document_ids=payload.document_ids,
            answer_payload=answer.model_dump(by_alias=True, mode="json"),
        )
        self.session.add(assistant_message)
        self.session.commit()
        self.session.refresh(assistant_message)
        return ChatExchangeData(
            user_message=self._message_data(user_message),
            assistant_message=self._message_data(assistant_message),
            answer=answer,
        )

    def delete_session(self, session_id: str) -> DeleteChatSessionData:
        session = self._active_session(session_id)
        session.status = ChatSessionStatus.DELETED
        session.deleted_at = datetime.now(UTC)
        self.session.commit()
        return DeleteChatSessionData(session_id=session_id)

    def _active_session(self, session_id: str) -> ChatSession:
        session = self.session.scalar(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.status == ChatSessionStatus.ACTIVE,
            )
        )
        if session is None:
            raise NotFoundError("CHAT_SESSION", session_id)
        return session

    @staticmethod
    def _message_data(message: ChatMessage) -> ChatMessageData:
        answer = (
            AnswerSchema.model_validate(message.answer_payload) if message.answer_payload else None
        )
        return ChatMessageData(
            id=message.id,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            document_ids=message.document_ids,
            answer=answer,
            created_at=message.created_at,
        )
