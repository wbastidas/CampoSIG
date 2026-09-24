"""Persistence for the pre-review: runs, reports and traces (RF-170, RF-180).

Deliberately **outside** `app/agents/`. The structural guard on that package forbids importing
SQLAlchemy at all, which is how rule 14 — an agent writes only its report — holds without anybody
having to remember it. Splitting the packages says the same thing the rule says: the agents compute,
the platform stores. A guard with an exception list for "the file that is allowed to write" would be
a guard somebody extends.

Three tables because RF-180 asks for three different questions to be answerable:

* `agent_run` — did this work order get a pre-review at all, and how did it end? Its acceptance
  criterion is that **every** synced order has a run in some terminal state, and that failures
  retry without blocking human review.
* `agent_report` — the consolidated result the supervisor reads.
* `agent_step_trace` — what each node did, with its model and its inputs, so «la reproducción de una
  ejecución con la misma versión da el mismo informe» is something a person can check rather than
  a claim in a document.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.database import Base


class RunState:
    """States a run passes through. Plain constants: the set is small and never branches."""

    PENDING = "pendiente"
    RUNNING = "en_curso"
    DONE = "terminado"
    #: Finished, but a node did not run. The report exists and says what is missing (RF-204).
    PARTIAL = "parcial"
    FAILED = "fallido"

    TERMINAL = (DONE, PARTIAL, FAILED)


class AgentRun(Base):
    """One execution of the pre-review graph for one work order."""

    __tablename__ = "agent_run"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_unit.id", ondelete="CASCADE"), nullable=False
    )
    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_order.id", ondelete="CASCADE"), nullable=False
    )

    graph_version: Mapped[str] = mapped_column(String(32), nullable=False)
    hardware_profile: Mapped[str] = mapped_column(String(8), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default=RunState.PENDING)

    #: Why it failed, when it did. Kept so a retry is a decision rather than a guess.
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    compute_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    report: Mapped[StoredReport | None] = relationship(
        back_populates="run", cascade="all, delete-orphan", uselist=False
    )
    traces: Mapped[list[AgentStepTrace]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="AgentStepTrace.started_at"
    )

    __table_args__ = (
        Index("ix_agent_run_order", "work_order_id"),
        # The worker's query: this unit's runs still waiting.
        Index("ix_agent_run_pending", "business_unit_id", "state"),
    )

    @property
    def is_terminal(self) -> bool:
        return self.state in RunState.TERMINAL


class StoredReport(Base):
    """The consolidated report (RF-175), as produced.

    Stored whole, in the Annex D shape, rather than normalised into observation rows. The report is
    an artifact a supervisor read on a date: reshaping it into tables would make the schema the
    source of truth and leave no way to render what somebody actually saw.
    """

    __tablename__ = "agent_report"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_run.id", ondelete="CASCADE"), nullable=False
    )
    risk_level: Mapped[str] = mapped_column(String(8), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    #: The whole `AgentReport`, validated before storage.
    document: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    #: Counted out of the document so the review queue can sort without parsing JSONB.
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    discarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    run: Mapped[AgentRun] = relationship(back_populates="report")

    __table_args__ = (
        # One report per run. A second one would mean nobody can say which the supervisor read.
        UniqueConstraint("agent_run_id", name="uq_agent_report_run"),
    )


class AgentStepTrace(Base):
    """What one node did (RF-180)."""

    __tablename__ = "agent_step_trace"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_run.id", ondelete="CASCADE"), nullable=False
    )
    node: Mapped[str] = mapped_column(String(48), nullable=False)
    #: The alias, never the model name: that is what M19 is for (rule 13). The resolved model and
    #: version travel beside it so a report can still be traced to what produced it.
    model_alias: Mapped[str | None] = mapped_column(String(32))
    model_version: Mapped[str | None] = mapped_column(String(64))
    #: Hash rather than the prompt: a prompt is not small, and what an audit needs is to know
    #: whether it changed.
    prompt_hash: Mapped[str | None] = mapped_column(String(64))
    #: Which observations the node produced, and why it did not run when it did not.
    output: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    skipped_reason: Mapped[str | None] = mapped_column(Text)
    tools: Mapped[list[str]] = mapped_column(ARRAY(String(64)), nullable=False, default=list)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    run: Mapped[AgentRun] = relationship(back_populates="traces")

    __table_args__ = (Index("ix_agent_step_trace_run", "agent_run_id"),)
