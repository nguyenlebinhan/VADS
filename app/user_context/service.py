from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.user_context.models import UserContextProfile
from app.user_context.schemas import UserContextData, UserContextUpdate


class UserContextService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user_id: str) -> UserContextData:
        profile = self._find(user_id)
        if profile is None:
            raise NotFoundError("USER_CONTEXT", user_id)
        return UserContextData.model_validate(profile)

    def upsert(self, user_id: str, payload: UserContextUpdate) -> UserContextData:
        profile = self._find(user_id)
        if profile is None:
            profile = UserContextProfile(user_id=user_id, **payload.model_dump())
            self.session.add(profile)
        else:
            for field, value in payload.model_dump().items():
                setattr(profile, field, value)
        self.session.commit()
        self.session.refresh(profile)
        return UserContextData.model_validate(profile)

    def _find(self, user_id: str) -> UserContextProfile | None:
        return self.session.scalar(
            select(UserContextProfile).where(UserContextProfile.user_id == user_id)
        )
