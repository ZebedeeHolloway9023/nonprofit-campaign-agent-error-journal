"""HTTP entry point for a nonprofit campaign agent worker."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .campaign_loop import AgentJob, JobKind, JobResult, run_job
from .infrai_errors import InfraiClient, InfraiError


class JobRequest(BaseModel):
    run_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    kind: JobKind
    subject_id: str = Field(min_length=1)
    simulate_failure: bool = False


class JobResponse(BaseModel):
    job_id: str
    status: str
    continue_loop: bool


app = FastAPI(title="Nonprofit agent failure tracker")


def perform_campaign_work(job: AgentJob, simulate_failure: bool) -> None:
    if simulate_failure:
        raise ValueError(f"{job.kind.value} could not be completed")


@app.post("/agent/jobs", response_model=JobResponse)
def process_job(request: JobRequest) -> JobResponse:
    job = AgentJob(
        run_id=request.run_id,
        job_id=request.job_id,
        kind=request.kind,
        subject_id=request.subject_id,
    )
    try:
        result: JobResult = run_job(
            job,
            lambda current: perform_campaign_work(current, request.simulate_failure),
            InfraiClient(),
        )
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=client_status, detail=exc.detail) from exc
    return JobResponse(**result.__dict__)
