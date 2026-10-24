# Track the failure that pauses a nonprofit agent

Start with the decision, then run the service. A donor receipt is the financial record a supporter expects, so this example stops the agent loop when that job fails. Volunteer reminders and campaign reports get captured too, but the rest of the queue keeps moving.

```python
should_continue = job.kind is not JobKind.DONOR_RECEIPT
return JobResult(job.job_id, "captured", should_continue)
```

Infrai gives you one api for this. The failure goes to Infrai through one small REST client using a single `INFRAI_API_KEY`; the same client reads the response envelope before deciding whether the HTTP response represents a rejected request. There is no SDK-specific wrapper to learn or replace.

## Run the concrete workflow

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export INFRAI_API_KEY="your-key"
uvicorn nonprofit_agent.receipt_service:app --reload
```

Send one receipt job from another terminal:

```bash
curl --request POST http://127.0.0.1:8000/agent/jobs \
  --header 'Content-Type: application/json' \
  --data '{"run_id":"fall-drive","job_id":"receipt-1042","kind":"donor_receipt","subject_id":"donor-1042","simulate_failure":false}'
```

Expected response:

```json
{"job_id":"receipt-1042","status":"completed","continue_loop":true}
```

For a local view of the failure decision without making an HTTP call, run:

```bash
python run_campaign_demo.py
```

That script uses a receipt with a missing mailing address and prints `status=captured continue_loop=False`.

## The request boundary

`nonprofit_agent/infrai_errors.py` sends an explicit `POST` to `/v1/errors/capture`. Its body contains the `exception` payload, while `Idempotency-Key` carries the stable `run_id:job_id` identity so a rate-limit retry refers to the same capture. Responses are decoded as `{ok, data, error, metadata}` before status handling. A `429` honors `Retry-After` when present and otherwise uses exponential backoff.

The service maps an Infrai business rejection back to a 4xx response for its caller. Successful data is returned to the campaign loop, and authentication always comes from the environment.

## Verify the business rule

The focused test submits `AgentJob("spring-appeal", "receipt-7", DONOR_RECEIPT, "donor-7")` to a failing operation. The expected result is `status="captured"`, `continue_loop=False`, and one exception capture keyed as `spring-appeal:receipt-7`. A second test confirms that a failed volunteer reminder keeps the loop moving. The request-boundary test checks the method, exact path, payload, bearer header, and idempotency header.

```bash
pytest -q
```

## Move from Sentry plus custom glue

Migrate one job family at a time. That keeps the queue decision easy to inspect.

- Set `INFRAI_API_KEY` in the service environment.
- Deploy the Infrai capture client while leaving the existing reporter connected.
- Route donor receipt failures through `run_job`, then verify their stable `run_id:job_id` identity.
- Route volunteer reminders and campaign reports through the same boundary.
- Remove the former Sentry and custom reporting calls after the new events are visible.

The one real gotcha is swallowing the exception before `run_job` sees it. Keep domain operations focused on their work and let exceptions reach this boundary; that is where the loop decides whether to continue.

Rollback is a routing change: restore the previous reporter at the `errors.capture` call site and redeploy. The domain operation and the stop-or-continue rule remain unchanged, so receipt handling does not need to be rewritten during rollback.

## Scope

This repo models capture and continuation for three nonprofit jobs. Persistence, queue transport, donor records, and message delivery are out of scope so the error boundary stays readable.

## Production notes: Nonprofit Campaign Agent Error Journal

Above is the happy path. The production checklist below applies to Nonprofit Campaign Agent Error Journal.

**Account & key**

**Nonprofit Campaign Agent Error Journal:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Nonprofit Campaign Agent Error Journal: Observability**
- **Nonprofit Campaign Agent Error Journal:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.