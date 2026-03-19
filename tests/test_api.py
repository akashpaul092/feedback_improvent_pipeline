"""API endpoint tests."""
import pytest
from fastapi.testclient import TestClient


def test_root(client: TestClient):
    """Health check returns ok."""
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert "service" in r.json()


def test_health(client: TestClient):
    """Health endpoint for load balancers."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_ingest_conversation(client: TestClient):
    """Single conversation ingest stores and queues."""
    payload = {
        "conversation_id": "conv_test_001",
        "agent_version": "v1.0",
        "turns": [
            {"turn_id": 1, "role": "user", "content": "Track my order ORD123"},
            {"turn_id": 2, "role": "assistant", "content": "Checking...", "tool_calls": []},
        ],
        "feedback": {"user_rating": 4},
        "metadata": {"total_latency_ms": 500},
    }
    r = client.post("/conversations/ingest", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["conversation_id"] == "conv_test_001"
    assert data["agent_version"] == "v1.0"
    assert data["status"] == "queued"


def test_ingest_duplicate_returns_already_exists(client: TestClient):
    """Ingesting same conversation twice returns already_exists."""
    payload = {
        "conversation_id": "conv_dup_001",
        "agent_version": "v1.0",
        "turns": [{"turn_id": 1, "role": "user", "content": "Hi"}],
    }
    r1 = client.post("/conversations/ingest", json=payload)
    assert r1.status_code == 200
    assert r1.json()["status"] == "queued"

    r2 = client.post("/conversations/ingest", json=payload)
    assert r2.status_code == 200
    assert r2.json()["status"] == "already_exists"


def test_ingest_batch(client: TestClient):
    """Batch ingest stores and queues multiple conversations."""
    payload = [
        {"conversation_id": "batch_1", "agent_version": "v1", "turns": [{"turn_id": 1, "role": "user", "content": "A"}]},
        {"conversation_id": "batch_2", "agent_version": "v1", "turns": [{"turn_id": 1, "role": "user", "content": "B"}]},
    ]
    r = client.post("/conversations/ingest/batch", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["ingested"] == 2
    assert len(data["results"]) == 2
    assert all(r["status"] == "queued" for r in data["results"])


def test_queue_status(client: TestClient):
    """Queue status returns pending count."""
    r = client.get("/queue/status")
    assert r.status_code == 200
    assert "pending" in r.json()


def test_queue_process_empty(client: TestClient):
    """Process empty queue returns empty status."""
    r = client.post("/queue/process")
    assert r.status_code == 200
    assert r.json()["status"] == "empty"


def test_queue_process_one(client: TestClient):
    """Process one conversation from queue."""
    # Ingest first
    client.post(
        "/conversations/ingest",
        json={
            "conversation_id": "conv_queued_001",
            "agent_version": "v1",
            "turns": [
                {"turn_id": 1, "role": "user", "content": "Track order ORD1"},
                {"turn_id": 2, "role": "assistant", "content": "Checking...", "tool_calls": []},
            ],
        },
    )
    r = client.post("/queue/process")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "processed"
    assert "evaluation_id" in data


def test_queue_process_batch(client: TestClient):
    """Process multiple conversations with batch_size."""
    for i in range(3):
        client.post(
            "/conversations/ingest",
            json={
                "conversation_id": f"conv_batch_{i}",
                "agent_version": "v1",
                "turns": [{"turn_id": 1, "role": "user", "content": "Hi"}, {"turn_id": 2, "role": "assistant", "content": "Hello", "tool_calls": []}],
            },
        )
    r = client.post("/queue/process?batch_size=5")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "processed"
    assert data["processed"] == 3
    assert len(data["evaluations"]) == 3


def test_run_evaluation_404(client: TestClient):
    """Run evaluation for non-existent conversation returns 404."""
    r = client.post("/evaluations/run/nonexistent_conv")
    assert r.status_code == 404


def test_run_evaluation_success(client: TestClient):
    """Run evaluation for existing conversation."""
    client.post(
        "/conversations/ingest",
        json={
            "conversation_id": "conv_eval_001",
            "agent_version": "v1",
            "turns": [
                {"turn_id": 1, "role": "user", "content": "Track my order ORD123"},
                {"turn_id": 2, "role": "assistant", "content": "Checking...", "tool_calls": []},
            ],
        },
    )
    r = client.post("/evaluations/run/conv_eval_001")
    assert r.status_code == 200
    data = r.json()
    assert "evaluation_id" in data
    assert "scores" in data
    assert "overall" in data["scores"]
    assert "issues_detected" in data
    assert "improvement_suggestions" in data


def test_list_evaluations(client: TestClient):
    """List evaluations returns paginated results."""
    r = client.get("/evaluations")
    assert r.status_code == 200
    assert "total" in r.json()
    assert "evaluations" in r.json()


def test_get_suggestions(client: TestClient):
    """Get improvement suggestions."""
    r = client.get("/evaluations/suggestions")
    assert r.status_code == 200
    assert "suggestions" in r.json()


def test_get_calibration(client: TestClient):
    """Get calibration params."""
    r = client.get("/evaluations/calibration")
    assert r.status_code == 200
    assert "calibration" in r.json()


def test_run_calibration(client: TestClient):
    """Run calibration endpoint."""
    r = client.post("/evaluations/calibrate")
    assert r.status_code == 200
    assert "calibration" in r.json() or "blind_spots" in r.json()
