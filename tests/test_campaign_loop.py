from typing import Any

from nonprofit_agent.campaign_loop import AgentJob, JobKind, run_job


class CaptureSpy:
    def __init__(self) -> None:
        self.calls: list[tuple[dict[str, Any], str]] = []

    def capture(self, exception: dict[str, Any], event_id: str) -> dict[str, Any]:
        self.calls.append((exception, event_id))
        return {"event_id": event_id}


def fail(_: AgentJob) -> None:
    raise ValueError("mailing address missing")


def test_failed_donor_receipt_is_captured_and_stops_the_loop() -> None:
    captures = CaptureSpy()
    job = AgentJob("spring-appeal", "receipt-7", JobKind.DONOR_RECEIPT, "donor-7")

    result = run_job(job, fail, captures)

    assert result.status == "captured"
    assert result.continue_loop is False
    assert captures.calls == [
        (
            {
                "type": "ValueError",
                "message": "mailing address missing",
                "run_id": "spring-appeal",
                "job_id": "receipt-7",
                "job_kind": "donor_receipt",
                "subject_id": "donor-7",
            },
            "spring-appeal:receipt-7",
        )
    ]


def test_failed_reminder_is_captured_and_keeps_the_loop_moving() -> None:
    captures = CaptureSpy()
    job = AgentJob("spring-appeal", "reminder-9", JobKind.VOLUNTEER_REMINDER, "volunteer-9")

    result = run_job(job, fail, captures)

    assert result.continue_loop is True
    assert captures.calls[0][0]["job_kind"] == "volunteer_reminder"
