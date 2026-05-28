import asyncio

import pytest  # type: ignore[import-not-found]

from backend.db import DB  # type: ignore[import-untyped]
from backend.defense import defense  # type: ignore[import-untyped]
from backend.ids import ids  # type: ignore[import-untyped]
from backend.replay import ReplayStore  # type: ignore[import-untyped]
from backend import simulation as simulation_module
from backend.telemetry import telemetry  # type: ignore[import-untyped]
from backend.ws_manager import manager


@pytest.fixture(autouse=True)
def reset_shared_state():
    telemetry.reset()

    async def _reset_defense() -> None:
        await defense.reset()

    asyncio.run(_reset_defense())
    simulation_module.sim.running = False
    simulation_module.sim.active_attack = None
    simulation_module.sim._events = []
    simulation_module.sim._compromised_hosts.clear()
    simulation_module.sim._task = None
    yield
    asyncio.run(_reset_defense())


def test_db_and_replay_roundtrip(tmp_path):
    test_db = DB(str(tmp_path / "guardio-test.db"))
    events = [{"type": "attack", "ts": "2026-05-26T00:00:00Z"}]

    assert "0001_initial.sql" in test_db.applied_migrations()
    assert test_db.readiness_snapshot()["connected"] is True

    test_db.save_replay("replay-1", events)
    listed = test_db.list_replays()
    assert listed[0]["id"] == "replay-1"
    assert test_db.get_events("replay-1") == events

    test_db.purge_replay("replay-1")
    assert test_db.get_events("replay-1") == []

    store = ReplayStore()
    rid = store.save(events)
    assert store.get(rid) == events
    assert store.list()[0]["id"] == rid
    assert store.summary(rid)["event_count"] == 1


@pytest.mark.asyncio
async def test_emit_packet_routes_core_branches(monkeypatch):
    emitted = []

    async def fake_broadcast(message):
        emitted.append(message)

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr(manager, "broadcast_json", fake_broadcast)
    monkeypatch.setattr(telemetry, "increment", lambda *args, **kwargs: None)
    monkeypatch.setattr(ids, "alert_for", lambda packet: {"type": "alert"})
    monkeypatch.setattr(simulation_module.asyncio, "sleep", fake_sleep)

    await defense.block_host("host-blocked")
    await simulation_module.sim._emit_packet(
        simulation_module.sim._generate_packet(
            normal=True,
            src="host-blocked",
            dst="srv-1",
        )
    )
    assert emitted[-1]["type"] == "dropped"

    await defense.reset()
    await defense.create_segment("seg-a", {"srv-1"})
    await defense.create_segment("seg-b", {"srv-2"})
    await simulation_module.sim._emit_packet(
        simulation_module.sim._generate_packet(
            normal=True,
            src="srv-1",
            dst="srv-2",
        )
    )
    assert any(message.get("reason") == "segment-isolation" for message in emitted)

    await defense.reset()
    await defense.add_honeypot("srv-9")
    await simulation_module.sim._emit_packet(
        simulation_module.sim._generate_packet(
            normal=True,
            src="host-1",
            dst="srv-9",
        )
    )
    assert any(message.get("type") == "honeypot" for message in emitted)
    assert any(message.get("type") == "alert" for message in emitted)


@pytest.mark.asyncio
async def test_attack_helpers_execute(monkeypatch):
    emitted = []

    async def fake_broadcast(message):
        emitted.append(message)

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr(manager, "broadcast_json", fake_broadcast)
    monkeypatch.setattr(telemetry, "increment", lambda *args, **kwargs: None)
    monkeypatch.setattr(ids, "alert_for", lambda packet: None)
    monkeypatch.setattr(simulation_module.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(simulation_module.sim, "_target_host", lambda: "srv-1")
    monkeypatch.setattr(simulation_module.sim, "_pick", lambda pool: pool[0])
    monkeypatch.setattr(simulation_module.random, "choice", lambda seq: seq[0])
    monkeypatch.setattr(simulation_module.random, "randint", lambda a, b: a)
    monkeypatch.setattr(
        simulation_module.random,
        "sample",
        lambda seq, count: list(seq)[:count],
    )

    await simulation_module.sim._attack_ddos()
    await simulation_module.sim._attack_malware()
    await simulation_module.sim._attack_ransomware()
    await simulation_module.sim._attack_phishing()
    await simulation_module.sim._attack_botnet()

    assert emitted
    assert simulation_module.sim._compromised_hosts
