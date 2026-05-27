from backend.db import (
    save_replay,
    list_replays,
    get_replay,
    delete_replay,
)


def test_replay_persistence():
    # 1. Create a sample replay data
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

    # 2. Save the replay
    save_replay(replay_data)

    # 3. List replays and check if the new replay is listed
    replays = list_replays()
    assert any(r["id"] == "test-replay-1" for r in replays)

    # 4. Fetch the replay and check if the data matches
    fetched_replay = get_replay("test-replay-1")
    assert fetched_replay is not None
    assert fetched_replay["id"] == replay_data["id"]
    assert fetched_replay["name"] == replay_data["name"]
    assert fetched_replay["events"] == replay_data["events"]

    # 5. Delete the replay and verify it's gone (Completing the lifecycle)
    delete_replay("test-replay-1")

    # Verify it can no longer be fetched
    deleted_replay = get_replay("test-replay-1")
    assert deleted_replay is None or deleted_replay == {}

    # Verify it is no longer present in the list
    post_delete_replays = list_replays()
    assert not any(r["id"] == "test-replay-1" for r in post_delete_replays)