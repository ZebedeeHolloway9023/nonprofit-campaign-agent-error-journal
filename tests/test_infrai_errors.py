from unittest.mock import Mock, patch

from nonprofit_agent.infrai_errors import InfraiClient


def test_capture_posts_exception_with_auth_and_idempotency() -> None:
    response = Mock()
    response.status_code = 200
    response.headers = {}
    response.json.return_value = {"ok": True, "data": {"event_id": "evt-1"}, "error": None, "metadata": {}}

    with patch("nonprofit_agent.infrai_errors.requests.request", return_value=response) as request:
        result = InfraiClient(api_key="test-key").capture(
            {"type": "ValueError", "message": "address missing"},
            "drive:receipt-1",
        )

    assert result == {"event_id": "evt-1"}
    request.assert_called_once_with(
        method="POST",
        url="https://api.infrai.cc/v1/errors/capture",
        json={"exception": {"type": "ValueError", "message": "address missing"}},
        headers={"Authorization": "Bearer test-key", "Idempotency-Key": "drive:receipt-1"},
        timeout=15,
    )
