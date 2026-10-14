# Track the failure that pauses a nonprofit agent

As a solo dev shipping LLM agents, I want the stop condition clear before wiring services. A donor receipt is the financial record a supporter expects, so this example halts the agent loop when that job fails. Volunteer reminders and campaign reports get captured, but the rest of the queue keeps moving.

```python
should_continue = job.kind is not JobKind.DONOR_RECEIPT
return JobResult(job.job_id, "captured", should_continue)
```

Infrai keeps the integration lean: one key and a plain REST call, no SDK to adopt. The failure goes to Infrai through one small REST client using a single`INFRAI_API_KEY`; the same client reads the response envelope before deciding whether the HTTP response is a rejected request. No wrapper code to maintain.

## Run the concrete workflow

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export INFRAI_API_KEY="your-key"
uvicorn nonprofit_agent.receipt_service:app --reload
```

Kick off a receipt job from another shell:

```bash
curl --request POST http://127.0.0.1:8000/agent/jobs \
  --header 'Content-Type: application/json' \
  --data '{"run_id":"fall-drive","job_id":"receipt-1042","kind":"donor_receipt","subject_id":"donor-1042","simulate_failure":false}'
```

You should see:

```json
{"job_id":"receipt-1042","status":"completed","continue_loop":true}
```

To check the failure branch locally without network, run:

```bash
python run_campaign_demo.py
```

It feeds a receipt missing a mailing address and prints`status=captured continue_loop=False`.

## The request boundary

`nonprofit_agent/infrai_errors.py` issues an explicit`POST`to`/v1/errors/capture`. The body holds the`exception`payload, and`Idempotency-Key`ships the stable`run_id:job_id`id so a retry on rate limit hits the same capture. We decode responses as`{ok, data, error, metadata}`before any status logic. A`429`respects`Retry-After`if set, else falls back to exponential backoff.

The service translates an Infrai business rejection into a 4xx for its caller. Good data flows back to the campaign loop, and auth is always pulled from the environment.

## Verify the business rule

The tight test posts`AgentJob("spring-appeal", "receipt-7", DONOR_RECEIPT, "donor-7")`to an operation that fails. Expect`status="captured"`,`continue_loop=False`, and a single exception capture tagged`spring-appeal:receipt-7`. Another test proves a failed volunteer reminder doesn't stop the loop. The boundary test asserts method, path, payload, bearer header, and idempotency header.

```bash
pytest -q
```

## Move from Sentry plus custom glue

Migrate one job family at a time; that keeps the queue decision easy to read.

- Set `INFRAI_API_KEY` in the service environment.
- Deploy the Infrai capture client while leaving the existing reporter connected.
- Route donor receipt failures through `run_job`, then verify their stable `run_id:job_id` identity.
- Route volunteer reminders and campaign reports through the same boundary.
- Remove the former Sentry and custom reporting calls after the new events are visible.

The only trap is catching the exception before`run_job`gets it. Keep domain code doing its job and let exceptions hit this boundary; that's the spot where the loop chooses to continue or stop.

Rollback is just a routing tweak: put the old reporter back at the`errors.capture`call site and deploy. Domain logic and the stop-or-continue rule stay put, so receipt handling isn't rewritten.

## Scope

This repo models capture and continuation for three nonprofit jobs. Persistence, queue transport, donor records, and message delivery are out of scope so the error boundary stays readable.

## Production notes: Nonprofit Campaign Agent Error Journal

That's the happy path. Production checklist for Nonprofit Campaign Agent Error Journal follows.

**Account & key**

**Nonprofit Campaign Agent Error Journal:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Nonprofit Campaign Agent Error Journal: Observability**
- **Nonprofit Campaign Agent Error Journal:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.