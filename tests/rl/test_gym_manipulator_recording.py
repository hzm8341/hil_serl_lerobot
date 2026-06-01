import torch

from lerobot.scripts.rl.gym_manipulator import _select_recorded_action


def test_select_recorded_action_falls_back_to_env_action_without_intervention():
    action = torch.tensor([[0.1, 0.2, 0.3, 1.0]])

    recorded = _select_recorded_action(info={}, policy=None, action=action)

    assert torch.equal(recorded, action.squeeze(0).float())


def test_select_recorded_action_prefers_intervention_action_for_teleop():
    action = torch.tensor([[0.1, 0.2, 0.3, 1.0]])
    intervention_action = torch.tensor([[0.4, 0.5, 0.6, 2.0]])

    recorded = _select_recorded_action(
        info={"action_intervention": intervention_action},
        policy=None,
        action=action,
    )

    assert torch.equal(recorded, intervention_action.squeeze(0).float())
