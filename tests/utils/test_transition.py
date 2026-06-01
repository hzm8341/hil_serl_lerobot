import numpy as np
import torch

from lerobot.utils.transition import move_transition_to_device


def test_move_transition_to_device_converts_numpy_complementary_info():
    transition = {
        "state": {"observation.state": torch.zeros(1, 2)},
        "action": torch.zeros(1, 2),
        "reward": 0.0,
        "next_state": {"observation.state": torch.ones(1, 2)},
        "done": False,
        "truncated": False,
        "complementary_info": {"teleop_action": np.array([0.1, 0.2], dtype=np.float32)},
    }

    moved = move_transition_to_device(transition=transition, device="cpu")

    assert torch.equal(moved["complementary_info"]["teleop_action"], torch.tensor([0.1, 0.2]))
