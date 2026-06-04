import numpy as np
import torch

from lerobot.scripts.rl.gym_manipulator import (
    MUJOCO_COLLISION_GEOM_GROUP,
    _hide_mujoco_collision_geoms_from_viewer,
    _hide_mujoco_collision_geoms_in_model,
    _resolve_keyboard_control_state,
    _resolve_idle_action,
    _select_recorded_action,
    _teleop_action_is_active,
)


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


def test_resolve_idle_action_uses_random_sample_when_configured():
    current_action = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)
    sampled_action = np.array([0.1, -0.2, 0.3, 0.0], dtype=np.float32)

    resolved = _resolve_idle_action(
        current_action=current_action,
        sampled_action=sampled_action,
        idle_behavior="random",
    )

    np.testing.assert_array_equal(resolved, sampled_action)


def test_resolve_idle_action_holds_position_with_neutral_gripper():
    current_action = np.array([0.2, -0.1, 0.4, 0.0], dtype=np.float32)
    sampled_action = np.array([-0.4, 0.3, -0.2, 2.0], dtype=np.float32)

    resolved = _resolve_idle_action(
        current_action=current_action,
        sampled_action=sampled_action,
        idle_behavior="hold",
    )

    np.testing.assert_array_equal(resolved, np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32))


def test_teleop_action_is_active_ignores_neutral_hold_command():
    assert not _teleop_action_is_active(np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32))


def test_teleop_action_is_active_detects_motion_and_gripper_commands():
    assert _teleop_action_is_active(np.array([0.01, 0.0, 0.0, 1.0], dtype=np.float32))
    assert _teleop_action_is_active(np.array([0.0, 0.0, 0.0, 2.0], dtype=np.float32))


def test_hide_mujoco_collision_geoms_in_model_makes_collision_geoms_transparent():
    import mujoco

    model = mujoco.MjModel.from_xml_string(
        """
        <mujoco>
          <worldbody>
            <geom name="visual" type="sphere" size="0.1" group="2" rgba="1 0 0 1"/>
            <geom name="collision" type="sphere" size="0.1" group="3" rgba="0.5 0.5 0.5 1"/>
          </worldbody>
        </mujoco>
        """
    )
    collision_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "collision")

    _hide_mujoco_collision_geoms_in_model(model)

    np.testing.assert_array_equal(model.geom_rgba[collision_id], [0.0, 0.0, 0.0, 0.0])
    assert model.geom_group[collision_id] == MUJOCO_COLLISION_GEOM_GROUP


def test_hide_mujoco_collision_geoms_from_viewer_disables_collision_display_only():
    class FakeViewer:
        class Options:
            def __init__(self):
                self.geomgroup = np.array([1, 1, 1, 1, 1, 1], dtype=np.uint8)
                self.flags = np.array([1] * 12, dtype=np.uint8)

        def __init__(self):
            self.opt = self.Options()
            self.locked = False
            self.changed_while_locked = False

        def lock(self):
            viewer = self

            class Lock:
                def __enter__(self):
                    viewer.locked = True

                def __exit__(self, exc_type, exc, tb):
                    viewer.changed_while_locked = bool(
                        viewer.opt.geomgroup[3] == 0
                        and viewer.opt.flags[0] == 0
                        and viewer.opt.flags[10] == 0
                    )
                    viewer.locked = False

            return Lock()

        def sync(self):
            pass

    viewer = FakeViewer()

    _hide_mujoco_collision_geoms_from_viewer(viewer)

    np.testing.assert_array_equal(viewer.opt.geomgroup, np.array([1, 1, 1, 0, 1, 1], dtype=np.uint8))
    assert viewer.opt.flags[0] == 0
    assert viewer.opt.flags[10] == 0
    assert viewer.changed_while_locked is True


def test_resolve_keyboard_control_state_keeps_auto_action_without_intervention():
    proposed_action = np.array([0.3, -0.2, 0.1, 1.0], dtype=np.float32)
    teleop_action = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)

    result = _resolve_keyboard_control_state(
        proposed_action=proposed_action,
        teleop_action=teleop_action,
        is_intervention_active=False,
        current_state="manual",
        last_manual_input_timestamp=12.0,
        now=13.0,
        manual_input_timeout_s=1.0,
        timeout_behavior="hold",
        safe_retreat_action=np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32),
        safe_retreat_steps_remaining=5,
    )

    assert result["state"] == "auto"
    np.testing.assert_array_equal(result["action"], proposed_action)
    assert result["last_manual_input_timestamp"] is None
    assert result["safe_retreat_steps_remaining"] == 0


def test_resolve_keyboard_control_state_prefers_manual_action_during_intervention():
    teleop_action = np.array([0.0, 0.1, 0.0, 1.0], dtype=np.float32)

    result = _resolve_keyboard_control_state(
        proposed_action=np.array([0.3, -0.2, 0.1, 1.0], dtype=np.float32),
        teleop_action=teleop_action,
        is_intervention_active=True,
        current_state="auto",
        last_manual_input_timestamp=None,
        now=7.5,
        manual_input_timeout_s=1.0,
        timeout_behavior="hold",
        safe_retreat_action=np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32),
        safe_retreat_steps_remaining=5,
    )

    assert result["state"] == "manual"
    np.testing.assert_array_equal(result["action"], teleop_action)
    assert result["last_manual_input_timestamp"] == 7.5
    assert result["safe_retreat_steps_remaining"] == 5


def test_resolve_keyboard_control_state_holds_before_timeout_expires():
    neutral_action = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)

    result = _resolve_keyboard_control_state(
        proposed_action=np.array([0.3, -0.2, 0.1, 1.0], dtype=np.float32),
        teleop_action=neutral_action,
        is_intervention_active=True,
        current_state="manual",
        last_manual_input_timestamp=10.0,
        now=10.5,
        manual_input_timeout_s=1.0,
        timeout_behavior="hold",
        safe_retreat_action=np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32),
        safe_retreat_steps_remaining=5,
    )

    assert result["state"] == "manual"
    np.testing.assert_array_equal(result["action"], neutral_action)
    assert result["timed_out"] is False


def test_resolve_keyboard_control_state_enters_safe_hold_after_timeout():
    neutral_action = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)

    result = _resolve_keyboard_control_state(
        proposed_action=np.array([0.3, -0.2, 0.1, 1.0], dtype=np.float32),
        teleop_action=neutral_action,
        is_intervention_active=True,
        current_state="manual",
        last_manual_input_timestamp=10.0,
        now=11.5,
        manual_input_timeout_s=1.0,
        timeout_behavior="hold",
        safe_retreat_action=np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32),
        safe_retreat_steps_remaining=5,
    )

    assert result["state"] == "safe_hold"
    np.testing.assert_array_equal(result["action"], neutral_action)
    assert result["timed_out"] is True


def test_resolve_keyboard_control_state_enters_safe_retreat_after_timeout():
    neutral_action = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)
    retreat_action = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32)

    result = _resolve_keyboard_control_state(
        proposed_action=np.array([0.3, -0.2, 0.1, 1.0], dtype=np.float32),
        teleop_action=neutral_action,
        is_intervention_active=True,
        current_state="manual",
        last_manual_input_timestamp=10.0,
        now=11.5,
        manual_input_timeout_s=1.0,
        timeout_behavior="retreat",
        safe_retreat_action=retreat_action,
        safe_retreat_steps_remaining=3,
    )

    assert result["state"] == "safe_retreat"
    np.testing.assert_array_equal(result["action"], retreat_action)
    assert result["safe_retreat_steps_remaining"] == 2


def test_resolve_keyboard_control_state_falls_back_to_safe_hold_after_retreat_steps():
    neutral_action = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)
    retreat_action = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32)

    result = _resolve_keyboard_control_state(
        proposed_action=np.array([0.3, -0.2, 0.1, 1.0], dtype=np.float32),
        teleop_action=neutral_action,
        is_intervention_active=True,
        current_state="safe_retreat",
        last_manual_input_timestamp=10.0,
        now=11.5,
        manual_input_timeout_s=1.0,
        timeout_behavior="retreat",
        safe_retreat_action=retreat_action,
        safe_retreat_steps_remaining=0,
    )

    assert result["state"] == "safe_hold"
    np.testing.assert_array_equal(result["action"], neutral_action)


def test_resolve_keyboard_control_state_requires_manual_rearm_after_timeout():
    proposed_action = np.array([0.3, -0.2, 0.1, 1.0], dtype=np.float32)
    teleop_action = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)

    result = _resolve_keyboard_control_state(
        proposed_action=proposed_action,
        teleop_action=teleop_action,
        is_intervention_active=False,
        current_state="safe_hold",
        last_manual_input_timestamp=10.0,
        now=12.0,
        manual_input_timeout_s=1.0,
        timeout_behavior="hold",
        safe_retreat_action=np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32),
        safe_retreat_steps_remaining=0,
        require_manual_rearm_after_timeout=True,
        rearm_requested=False,
    )

    assert result["state"] == "safe_hold"
    np.testing.assert_array_equal(result["action"], teleop_action)
    assert result["awaiting_rearm"] is True


def test_resolve_keyboard_control_state_allows_rearm_after_confirmation():
    proposed_action = np.array([0.3, -0.2, 0.1, 1.0], dtype=np.float32)
    teleop_action = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)

    result = _resolve_keyboard_control_state(
        proposed_action=proposed_action,
        teleop_action=teleop_action,
        is_intervention_active=False,
        current_state="safe_hold",
        last_manual_input_timestamp=10.0,
        now=12.0,
        manual_input_timeout_s=1.0,
        timeout_behavior="hold",
        safe_retreat_action=np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32),
        safe_retreat_steps_remaining=0,
        require_manual_rearm_after_timeout=True,
        rearm_requested=True,
    )

    assert result["state"] == "auto"
    np.testing.assert_array_equal(result["action"], proposed_action)
    assert result["awaiting_rearm"] is False
