"""Form responses, evidence, provenance and supervisor review.

RF-043..RF-048 (responses), M07 (evidence), RF-052/RF-140 (provenance), M11 (review).

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "form_response",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "business_unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_unit.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "work_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("work_order.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("form_code", sa.String(16), nullable=False),
        sa.Column("form_version", sa.String(16), nullable=False),
        sa.Column("answers", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("state", sa.String(16), nullable=False, server_default="borrador"),
        # AI summary and the technician's edit kept apart: the difference is a training signal.
        sa.Column("summary_ai", sa.Text, nullable=True),
        sa.Column("summary_final", sa.Text, nullable=True),
        sa.Column("device_key", sa.String(128), nullable=True),
        sa.Column("captured_by", sa.String(255), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("work_order_id", "form_code", name="uq_form_response_identity"),
        sa.CheckConstraint(
            "state IN ('borrador', 'enviada', 'devuelta', 'aprobada')",
            name="ck_form_response_state",
        ),
    )
    op.create_index("ix_form_response_unit_state", "form_response", ["business_unit_id", "state"])

    op.create_table(
        "field_provenance",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "response_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("form_response.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_key", sa.String(128), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False),
        sa.Column("proposed_value", postgresql.JSONB, nullable=True),
        sa.Column("final_value", postgresql.JSONB, nullable=True),
        sa.Column("model_name", sa.String(64), nullable=True),
        sa.Column("model_version", sa.String(32), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column(
            "accepted_unchanged", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column("confirmed_by", sa.String(255), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_level", sa.String(16), nullable=True),
        sa.Column("source_transcript", sa.Text, nullable=True),
        sa.UniqueConstraint("response_id", "field_key", name="uq_field_provenance_identity"),
        sa.CheckConstraint(
            "origin IN ('manual', 'voz', 'vision', 'calculado', 'precargado')",
            name="ck_field_provenance_origin",
        ),
    )
    op.create_index("ix_field_provenance_origin", "field_provenance", ["origin"])
    # The active-learning query: low-confidence proposals get labelled first.
    op.create_index("ix_field_provenance_confidence", "field_provenance", ["confidence"])

    op.create_table(
        "evidence",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "response_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("form_response.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("stage", sa.String(16), nullable=False, server_default="no_aplica"),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("mime_type", sa.String(64), nullable=True),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.Column("gps_accuracy_m", sa.Float, nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("framing", sa.String(64), nullable=True),
        sa.Column(
            "integrity_verified", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column("vision_result", postgresql.JSONB, nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_evidence_response_stage", "evidence", ["response_id", "stage"])
    # Deduplication: the same file uploaded twice is stored once.
    op.create_index("ix_evidence_hash", "evidence", ["content_hash"])

    op.create_table(
        "review_decision",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "business_unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_unit.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "work_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("work_order.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "response_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("form_response.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("reviewer_sub", sa.String(255), nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        # For the anchoring-bias blind sample (RF-111a).
        sa.Column("blind_sample", sa.Boolean, nullable=True),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "decision IN ('aprobada', 'devuelta', 'anulada')", name="ck_review_decision"
        ),
    )
    op.create_index(
        "ix_review_decision_unit", "review_decision", ["business_unit_id", "decided_at"]
    )
    op.create_index("ix_review_decision_work_order", "review_decision", ["work_order_id"])

    op.create_table(
        "field_observation",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "decision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("review_decision.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_key", sa.String(128), nullable=False),
        sa.Column("message", sa.String(1000), nullable=False),
        sa.Column("suggested_value", postgresql.JSONB, nullable=True),
    )
    op.create_index("ix_field_observation_decision", "field_observation", ["decision_id"])


def downgrade() -> None:
    op.drop_table("field_observation")
    op.drop_table("review_decision")
    op.drop_table("evidence")
    op.drop_table("field_provenance")
    op.drop_table("form_response")
