"""Idempotently create local-only demo accounts for frontend testing."""

from __future__ import annotations

import os
from dataclasses import dataclass

from sqlalchemy import create_engine, func, or_, select
from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.core.permissions import UserRole
from app.core.security import hash_password
from app.model.tenancy import Commune, Province
from app.model.users import User, UserStatus
from app.utils.model_registry import import_models


@dataclass(frozen=True)
class DemoAccount:
    username: str
    email: str
    full_name: str
    position: str
    department: str
    role: UserRole
    password: str


def _accounts() -> tuple[DemoAccount, DemoAccount]:
    return (
        DemoAccount(
            username=os.getenv("VADS_DEMO_ADMIN_USERNAME", "admin.demo"),
            email=os.getenv("VADS_DEMO_ADMIN_EMAIL", "admin.demo@vads.local"),
            full_name="Quản trị VADS",
            position="Quản trị viên",
            department="Văn phòng UBND",
            role=UserRole.ADMIN,
            password=os.getenv("VADS_DEMO_ADMIN_PASSWORD", "VadsAdmin@2026"),
        ),
        DemoAccount(
            username=os.getenv("VADS_DEMO_USER_USERNAME", "user.demo"),
            email=os.getenv("VADS_DEMO_USER_EMAIL", "user.demo@vads.local"),
            full_name="Chuyên viên VADS",
            position="Chuyên viên",
            department="Phòng Pháp chế",
            role=UserRole.USER,
            password=os.getenv("VADS_DEMO_USER_PASSWORD", "VadsUser@2026!"),
        ),
    )


def _get_or_create_commune(session: Session) -> Commune:
    province = session.scalar(select(Province).where(Province.code == "VADS-DEMO"))
    if province is None:
        province = Province(name="Tỉnh Demo VADS", code="VADS-DEMO")
        session.add(province)
        session.flush()

    commune = session.scalar(select(Commune).where(Commune.code == "VADS-DEMO-XA"))
    if commune is None:
        commune = Commune(
            province_id=province.id,
            name="Xã Demo VADS",
            code="VADS-DEMO-XA",
        )
        session.add(commune)
        session.flush()
    return commune


def _upsert_account(
    session: Session,
    *,
    commune: Commune,
    account: DemoAccount,
    created_by: str | None,
) -> User:
    username = account.username.strip().casefold()
    email = account.email.strip().casefold()
    matches = session.scalars(
        select(User).where(
            or_(
                func.lower(User.username) == username,
                func.lower(User.email) == email,
            )
        )
    ).all()
    if len(matches) > 1:
        raise RuntimeError(
            f"Demo username/email collide with different users: {username}, {email}"
        )

    user = matches[0] if matches else User()
    is_existing = bool(matches)
    if not is_existing:
        session.add(user)

    user.commune_id = commune.id
    user.username = username
    user.email = email
    user.full_name = account.full_name
    user.position = account.position
    user.department = account.department
    user.role = account.role
    user.password_hash = hash_password(account.password)
    user.is_active = True
    user.must_change_password = False
    user.failed_login_attempts = 0
    user.locked_until = None
    user.status = UserStatus.ACTIVE
    user.created_by = created_by
    if is_existing:
        user.token_version += 1
    session.flush()
    return user


def seed_demo_accounts(session: Session) -> tuple[DemoAccount, DemoAccount]:
    accounts = _accounts()
    commune = _get_or_create_commune(session)
    admin = _upsert_account(
        session,
        commune=commune,
        account=accounts[0],
        created_by=None,
    )
    _upsert_account(
        session,
        commune=commune,
        account=accounts[1],
        created_by=admin.id,
    )
    return accounts


def main() -> None:
    settings = Settings()
    is_deployed = settings.environment in {"staging", "production"}
    allow_deployed_seed = os.getenv("VADS_ALLOW_DEMO_ACCOUNT_SEED", "").casefold() in {
        "1",
        "true",
        "yes",
    }
    if is_deployed and not allow_deployed_seed:
        raise RuntimeError(
            "Set VADS_ALLOW_DEMO_ACCOUNT_SEED=true explicitly for a one-time deployed seed."
        )
    if is_deployed and not all(
        os.getenv(name)
        for name in ("VADS_DEMO_ADMIN_PASSWORD", "VADS_DEMO_USER_PASSWORD")
    ):
        raise RuntimeError(
            "Deployed demo accounts require explicit VADS_DEMO_ADMIN_PASSWORD and "
            "VADS_DEMO_USER_PASSWORD values."
        )

    import_models()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        with Session(engine) as session, session.begin():
            accounts = seed_demo_accounts(session)
    finally:
        engine.dispose()

    for account in accounts:
        print(f"seeded {account.role.value}: {account.username} ({account.email})")


if __name__ == "__main__":
    main()
