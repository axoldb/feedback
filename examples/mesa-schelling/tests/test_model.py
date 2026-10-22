from mesa_axol.model import SchellingModel


def test_checkpoint_round_trip_state() -> None:
    first = SchellingModel(width=6, height=6, seed=123)
    for _ in range(4):
        first.step()
    signature = first.signature()
    second = SchellingModel(width=6, height=6, density=first.density,
                            minority_fraction=first.minority_fraction, threshold=first.threshold,
                            agents=first.agent_rows(), steps=first.steps_completed,
                            moves_total=first.moves_total, random_state=signature["random_state"],
                            numpy_rng_state=signature["numpy_rng_state"])
    assert second.signature() == signature
    first.step()
    second.step()
    assert second.signature() == first.signature()


def test_stable_identity_survives_moves() -> None:
    model = SchellingModel(width=6, height=6, seed=456)
    identities = {agent["stable_id"] for agent in model.agent_rows()}
    model.step()
    assert {agent["stable_id"] for agent in model.agent_rows()} == identities
