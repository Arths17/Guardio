from backend.models import Attack, Defense, SimulationResult


def test_attack_model_validation():
    """Validates the Attack Pydantic schema constraints and attributes."""
    attack = Attack(
        id="attack1",
        name="Test Attack",
        description="This is a test attack.",
        severity=5,
        tactics=["tactic1", "tactic2"],
        techniques=["technique1", "technique2"],
    )
    assert attack.id == "attack1"
    assert attack.name == "Test Attack"
    assert attack.description == "This is a test attack."
    assert attack.severity == 5
    assert attack.tactics == ["tactic1", "tactic2"]
    assert attack.techniques == ["technique1", "technique2"]


def test_defense_model_validation():
    """Validates the Defense Pydantic schema constraints and attributes."""
    defense = Defense(
        id="defense1",
        name="Test Defense",
        description="This is a test defense.",
        mitigates=["attack1", "attack2"],
    )
    assert defense.id == "defense1"
    assert defense.name == "Test Defense"
    assert defense.description == "This is a test defense."
    assert defense.mitigates == ["attack1", "attack2"]


def test_simulation_result_model_validation():
    """Validates the SimulationResult Pydantic schema constraints and attributes."""
    simulation_result = SimulationResult(
        attack_id="attack1",
        defense_id="defense1",
        success=True,
        details="The defense successfully mitigated the attack.",
    )
    assert simulation_result.attack_id == "attack1"
    assert simulation_result.defense_id == "defense1"
    assert simulation_result.success is True
    assert simulation_result.details == "The defense successfully mitigated the attack."