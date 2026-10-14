"""Business decisions for donor, volunteer, and campaign agent jobs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


class ErrorCapture(Protocol):
    def capture(self, exception: dict[str, Any], event_id: str) -> dict[str, Any]:
        return {}


class JobKind(str, Enum):
    DONOR_RECEIPT = "donor_receipt"
    VOLUNTEER_REMINDER = "volunteer_reminder"
    CAMPAIGN_REPORT = "campaign_report"


@dataclass(frozen=True)
class AgentJob:
    run_id: str
    job_id: str
    kind: JobKind
    subject_id: str


@dataclass(frozen=True)
class JobResult:
    job_id: str
    status: str
    continue_loop: bool


def run_job(
    job: AgentJob,
    operation: Callable[[AgentJob], Any],
    errors: ErrorCapture,
) -> JobResult:
    """Run one job and make the campaign-loop continuation decision visible."""
    try:
        operation(job)
        return JobResult(job.job_id, "completed", True)
    except Exception as exc:
        errors.capture(
            exception={
                "type": type(exc).__name__,
                "message": str(exc),
                "run_id": job.run_id,
                "job_id": job.job_id,
                "job_kind": job.kind.value,
                "subject_id": job.subject_id,
            },
            event_id=f"{job.run_id}:{job.job_id}",
        )
        should_continue = job.kind is not JobKind.DONOR_RECEIPT
        return JobResult(job.job_id, "captured", should_continue)
