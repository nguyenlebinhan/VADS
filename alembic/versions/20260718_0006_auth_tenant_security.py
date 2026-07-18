"""Add tenant-scoped authentication and authorization data.

Revision ID: 20260718_0006
Revises: 20260718_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260718_0006"
down_revision: str | None = "20260718_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_PROVINCE_ID = "00000000-0000-0000-0000-000000000001"
LEGACY_COMMUNE_ID = "00000000-0000-0000-0000-000000000002"


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "provinces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        *_timestamps(),
    )
    op.create_index("ix_provinces_code", "provinces", ["code"], unique=True)
    op.create_table(
        "communes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "province_id",
            sa.String(36),
            sa.ForeignKey("provinces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        *_timestamps(),
        sa.UniqueConstraint("province_id", "name", name="uq_communes_province_name"),
    )
    op.create_index("ix_communes_province_id", "communes", ["province_id"])
    op.create_index("ix_communes_code", "communes", ["code"], unique=True)

    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            INSERT INTO provinces (id, name, code)
            VALUES (:id, 'Legacy data - requires classification', 'LEGACY')
            """
        ),
        {"id": LEGACY_PROVINCE_ID},
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO communes (id, province_id, name, code)
            VALUES (:id, :province_id, 'Legacy data - requires classification', 'LEGACY')
            """
        ),
        {"id": LEGACY_COMMUNE_ID, "province_id": LEGACY_PROVINCE_ID},
    )

    duplicate_email = connection.execute(
        sa.text(
            """
            SELECT lower(email)
            FROM users
            GROUP BY lower(email)
            HAVING count(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate_email is not None:
        raise RuntimeError(
            "Case-insensitive duplicate user emails must be resolved before migration"
        )

    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("commune_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("username", sa.String(64), nullable=True))
        batch.add_column(sa.Column("position", sa.String(255), nullable=True))
        batch.add_column(sa.Column("department", sa.String(255), nullable=True))
        batch.add_column(
            sa.Column(
                "role",
                sa.Enum(
                    "ADMIN",
                    "USER",
                    name="user_role",
                    native_enum=False,
                    create_constraint=True,
                ),
                nullable=False,
                server_default="USER",
            )
        )
        batch.add_column(
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch.add_column(
            sa.Column(
                "must_change_password",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch.add_column(
            sa.Column(
                "failed_login_attempts",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch.add_column(
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(
            sa.Column("token_version", sa.Integer(), nullable=False, server_default="1")
        )
        batch.add_column(sa.Column("created_by", sa.String(40), nullable=True))

    connection.execute(
        sa.text(
            """
            UPDATE users
            SET commune_id = :commune_id,
                username = 'legacy_' || substr(replace(id, '-', ''), 1, 32),
                is_active = false,
                must_change_password = true
            """
        ),
        {"commune_id": LEGACY_COMMUNE_ID},
    )
    with op.batch_alter_table("users") as batch:
        batch.alter_column("commune_id", nullable=False)
        batch.alter_column("username", nullable=False)
        batch.create_foreign_key(
            "fk_users_commune_id_communes",
            "communes",
            ["commune_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_users_created_by_users",
            "users",
            ["created_by"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_unique_constraint(
            "uq_users_id_commune", ["id", "commune_id"]
        )
        batch.create_check_constraint(
            "users_failed_login_attempts_nonnegative",
            "failed_login_attempts >= 0",
        )
        batch.create_check_constraint("users_token_version_positive", "token_version >= 1")
        batch.alter_column("role", server_default=None)
        batch.alter_column("is_active", server_default=None)
        batch.alter_column("must_change_password", server_default=None)
        batch.alter_column("failed_login_attempts", server_default=None)
        batch.alter_column("token_version", server_default=None)

    op.create_index("ix_users_commune_id", "users", ["commune_id"])
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_is_active", "users", ["is_active"])
    op.create_index(
        "ix_users_commune_role_active",
        "users",
        ["commune_id", "role", "is_active"],
    )
    op.create_index(
        "uq_users_username_ci",
        "users",
        [sa.text("lower(username)")],
        unique=True,
    )
    op.create_index(
        "uq_users_email_ci",
        "users",
        [sa.text("lower(email)")],
        unique=True,
    )

    with op.batch_alter_table("documents") as batch:
        batch.add_column(sa.Column("commune_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("owner_id", sa.String(40), nullable=True))
        batch.add_column(
            sa.Column(
                "approval_status",
                sa.Enum(
                    "DRAFT",
                    "PENDING_APPROVAL",
                    "APPROVED",
                    "REJECTED",
                    name="document_approval_status",
                    native_enum=False,
                    create_constraint=True,
                ),
                nullable=False,
                server_default="DRAFT",
            )
        )
        batch.add_column(sa.Column("meeting_id", sa.String(36), nullable=True))
        batch.add_column(
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(sa.Column("deleted_by", sa.String(40), nullable=True))
    connection.execute(
        sa.text(
            """
            UPDATE documents
            SET commune_id = :commune_id,
                owner_id = uploaded_by,
                is_deleted = CASE WHEN deleted_at IS NULL THEN false ELSE true END
            """
        ),
        {"commune_id": LEGACY_COMMUNE_ID},
    )
    with op.batch_alter_table("documents") as batch:
        batch.alter_column("commune_id", nullable=False)
        batch.create_foreign_key(
            "fk_documents_commune_id_communes",
            "communes",
            ["commune_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_documents_owner_id_users",
            "users",
            ["owner_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_documents_deleted_by_users",
            "users",
            ["deleted_by"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_unique_constraint(
            "uq_documents_id_commune", ["id", "commune_id"]
        )
        batch.create_check_constraint(
            "documents_soft_delete_consistent",
            "(is_deleted = false AND deleted_at IS NULL) OR "
            "(is_deleted = true AND deleted_at IS NOT NULL)",
        )
        batch.alter_column("approval_status", server_default=None)
        batch.alter_column("is_deleted", server_default=None)
    op.create_index("ix_documents_commune_id", "documents", ["commune_id"])
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])
    op.create_index("ix_documents_approval_status", "documents", ["approval_status"])
    op.create_index("ix_documents_meeting_id", "documents", ["meeting_id"])
    op.create_index("ix_documents_is_deleted", "documents", ["is_deleted"])
    op.create_index(
        "ix_documents_commune_deleted",
        "documents",
        ["commune_id", "is_deleted"],
    )
    op.create_index(
        "ix_documents_commune_owner",
        "documents",
        ["commune_id", "owner_id"],
    )

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(40),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("refresh_token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("token_family_id", sa.String(36), nullable=False),
        sa.Column("device_name", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.String(64), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="ck_auth_sessions_auth_session_expiry_after_creation",
        ),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])
    op.create_index("ix_auth_sessions_revoked_at", "auth_sessions", ["revoked_at"])
    op.create_index(
        "ix_auth_sessions_user_revoked",
        "auth_sessions",
        ["user_id", "revoked_at"],
    )
    op.create_index(
        "ix_auth_sessions_family", "auth_sessions", ["token_family_id"]
    )

    op.create_table(
        "refresh_token_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("auth_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "status",
            sa.Enum(
                "ROTATED",
                "REVOKED",
                name="refresh_token_history_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
    )
    op.create_index(
        "ix_refresh_token_history_session_id",
        "refresh_token_history",
        ["session_id"],
    )
    op.create_index(
        "ix_refresh_history_session_status",
        "refresh_token_history",
        ["session_id", "status"],
    )

    op.create_table(
        "document_permissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(40), nullable=False),
        sa.Column("user_id", sa.String(40), nullable=False),
        sa.Column("commune_id", sa.String(36), nullable=False),
        sa.Column(
            "permission",
            sa.Enum(
                "READ",
                "ASK",
                name="document_grant_permission",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "granted_by",
            sa.String(40),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["document_id", "commune_id"],
            ["documents.id", "documents.commune_id"],
            ondelete="CASCADE",
            name="fk_document_permissions_document_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "commune_id"],
            ["users.id", "users.commune_id"],
            ondelete="CASCADE",
            name="fk_document_permissions_user_tenant",
        ),
        sa.UniqueConstraint(
            "document_id",
            "user_id",
            "permission",
            name="uq_document_permission_grant",
        ),
    )
    op.create_index(
        "ix_document_permissions_user_commune",
        "document_permissions",
        ["user_id", "commune_id"],
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "commune_id",
            sa.String(36),
            sa.ForeignKey("communes.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "actor_user_id",
            sa.String(40),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column(
            "result",
            sa.Enum(
                "SUCCESS",
                "DENIED",
                "FAILURE",
                name="audit_result",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("request_id", sa.String(128), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_audit_logs_commune_id", "audit_logs", ["commune_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    op.create_index(
        "ix_audit_logs_commune_created",
        "audit_logs",
        ["commune_id", "created_at"],
    )
    op.create_index(
        "ix_audit_logs_resource",
        "audit_logs",
        ["resource_type", "resource_id"],
    )
    op.create_index(
        "ix_audit_logs_actor_created",
        "audit_logs",
        ["actor_user_id", "created_at"],
    )

    if connection.dialect.name == "postgresql":
        op.execute(
            """
            CREATE FUNCTION vads_revoke_sessions_on_user_security_change()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            DECLARE
                security_reason text;
            BEGIN
                IF NEW.role IS DISTINCT FROM OLD.role THEN
                    security_reason := 'ROLE_CHANGED';
                ELSIF NEW.password_hash IS DISTINCT FROM OLD.password_hash THEN
                    security_reason := 'PASSWORD_CHANGED';
                ELSIF OLD.is_active = true AND NEW.is_active = false THEN
                    security_reason := 'ACCOUNT_LOCKED';
                END IF;

                IF security_reason IS NOT NULL THEN
                    IF NEW.token_version = OLD.token_version THEN
                        NEW.token_version := OLD.token_version + 1;
                    END IF;
                    UPDATE auth_sessions
                    SET revoked_at = now(),
                        revoke_reason = security_reason,
                        updated_at = now()
                    WHERE user_id = OLD.id
                      AND revoked_at IS NULL;
                END IF;
                RETURN NEW;
            END;
            $$
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_users_security_revoke
            BEFORE UPDATE OF role, password_hash, is_active ON users
            FOR EACH ROW
            EXECUTE FUNCTION vads_revoke_sessions_on_user_security_change()
            """
        )
        op.execute(
            """
            CREATE FUNCTION vads_deny_audit_log_mutation()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                RAISE EXCEPTION 'audit_logs is append-only';
            END;
            $$
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_audit_logs_append_only
            BEFORE UPDATE OR DELETE ON audit_logs
            FOR EACH ROW EXECUTE FUNCTION vads_deny_audit_log_mutation()
            """
        )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_users_security_revoke ON users")
        op.execute(
            "DROP FUNCTION IF EXISTS vads_revoke_sessions_on_user_security_change()"
        )
        op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_append_only ON audit_logs")
        op.execute("DROP FUNCTION IF EXISTS vads_deny_audit_log_mutation()")
    op.drop_table("audit_logs")
    op.drop_table("document_permissions")
    op.drop_table("refresh_token_history")
    op.drop_table("auth_sessions")

    for index_name in (
        "ix_documents_commune_owner",
        "ix_documents_commune_deleted",
        "ix_documents_is_deleted",
        "ix_documents_meeting_id",
        "ix_documents_approval_status",
        "ix_documents_owner_id",
        "ix_documents_commune_id",
    ):
        op.drop_index(index_name, table_name="documents")
    with op.batch_alter_table("documents") as batch:
        batch.drop_constraint("uq_documents_id_commune", type_="unique")
        batch.drop_constraint(
            "ck_documents_documents_soft_delete_consistent", type_="check"
        )
        batch.drop_constraint("fk_documents_deleted_by_users", type_="foreignkey")
        batch.drop_constraint("fk_documents_owner_id_users", type_="foreignkey")
        batch.drop_constraint("fk_documents_commune_id_communes", type_="foreignkey")
        for column_name in (
            "deleted_by",
            "is_deleted",
            "meeting_id",
            "approval_status",
            "owner_id",
            "commune_id",
        ):
            batch.drop_column(column_name)

    for index_name in (
        "uq_users_email_ci",
        "uq_users_username_ci",
        "ix_users_commune_role_active",
        "ix_users_is_active",
        "ix_users_role",
        "ix_users_commune_id",
    ):
        op.drop_index(index_name, table_name="users")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ck_users_users_token_version_positive", type_="check")
        batch.drop_constraint(
            "ck_users_users_failed_login_attempts_nonnegative", type_="check"
        )
        batch.drop_constraint("uq_users_id_commune", type_="unique")
        batch.drop_constraint("fk_users_created_by_users", type_="foreignkey")
        batch.drop_constraint("fk_users_commune_id_communes", type_="foreignkey")
        for column_name in (
            "created_by",
            "token_version",
            "locked_until",
            "failed_login_attempts",
            "must_change_password",
            "is_active",
            "role",
            "department",
            "position",
            "username",
            "commune_id",
        ):
            batch.drop_column(column_name)
    op.drop_table("communes")
    op.drop_table("provinces")
