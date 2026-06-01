import torch

from lerobot.scripts.rl.actor import _select_transition_action


def test_select_transition_action_keeps_policy_action_without_intervention_action():
    action = torch.tensor([[0.1, 0.2, 0.3, 1.0]])

    selected, did_intervene = _select_transition_action(
        info={"is_intervention": True},
        action=action,
    )

    assert selected is action
    assert did_intervene is False


def test_select_transition_action_uses_intervention_action_when_available():
    action = torch.tensor([[0.1, 0.2, 0.3, 1.0]])
    intervention_action = torch.tensor([[0.4, 0.5, 0.6, 2.0]])

    selected, did_intervene = _select_transition_action(
        info={"is_intervention": True, "action_intervention": intervention_action},
        action=action,
    )

    assert selected is intervention_action
    assert did_intervene is True
