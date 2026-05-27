from backend.db import (
    delete_replay,
    get_replay,
    get_replay_summary,
    list_replays,
    save_replay,
)


def test_replay_persistence():
    replay_data = {
        "id": "test-replay-1",
        "name": "Test Replay",
        "events": [
            {
                "event_id": "evt-1",
                "type": "login_attempt",
                "timestamp": "2024-01-01T00:00:00Z",
            },
            {
                "event_id": "evt-2",
                "type": "file_access",
                "timestamp": "2024-01-01T00:01:00Z",
            },
        ],
    }

    save_replay(replay_data)

    replays = list_replays()
    assert any(r["id"] == "test-replay-1" for r in replays)

    fetched_replay = get_replay("test-replay-1")
    assert fetched_replay is not None
    assert fetched_replay["id"] == replay_data["id"]
    assert fetched_replay["name"] == replay_data["name"]
    assert fetched_replay["events"] == replay_data["events"]

    delete_replay("test-replay-1")

    deleted_replay = get_replay("test-replay-1")
    assert deleted_replay is None or deleted_replay == {}

    post_delete_replays = list_replays()
    assert not any(r["id"] == "test-replay-1" for r in post_delete_replays)


def test_replay_summary_behavior():
    replay_data = {
        "id": "test-summary-val",
        "name": "Summary Test",
        "events": [
            {"event_id": "evt-1", "type": "login_attempt"},
            {"event_id": "evt-2", "type": "file_access"},
            {"event_id": "evt-3", "type": "file_access"},
        ],
    }

    save_replay(replay_data)

    try:
        summary = get_replay_summary("test-summary-val")
        assert summary is not None
        assert summary["id"] == replay_data["id"]
        assert summary["name"] == replay_data["name"]
        assert summary["total_events"] == 3
        assert summary["event_counts"]["login_attempt"] == 1
        assert summary["event_counts"]["file_access"] == 2
    finally:
        delete_replay("test-summary-val")
