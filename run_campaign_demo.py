"""Run the campaign decision locally with an in-memory capture sink."""

from typing import Any

from nonprofit_agent.campaign_loop import AgentJob, JobKind, run_job


class PrintedCaptures:
    def capture(self, exception: dict[str, Any], event_id: str) -> dict[str, Any]:
        print(f"captured {exception['job_kind']} as {event_id}")
        return {"event_id": event_id}


def reject_receipt(_: AgentJob) -> None:
    raise ValueError("receipt template needs a donor mailing address")


if __name__ == "__main__":
    receipt = AgentJob(
        run_id="fall-drive",
        job_id="receipt-1042",
        kind=JobKind.DONOR_RECEIPT,
        subject_id="donor-1042",
    )
    result = run_job(receipt, reject_receipt, PrintedCaptures())
    print(f"status={result.status} continue_loop={result.continue_loop}")
