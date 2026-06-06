# LeRobot HIL-SERL Simulation Workspace

English | [中文](README.zh-CN.md)

This repository is a LeRobot-based workspace focused on Human-in-the-Loop Soft Actor-Critic reinforcement learning in simulation. The current project centers on a MuJoCo Franka Panda pick-cube task through `gym_hil`, with keyboard/gamepad intervention, demonstration recording, online actor/learner training, and safer keyboard timeout behavior for industrial-style experiments.

The codebase is based on Hugging Face LeRobot and adds local HIL-SERL simulation configuration, SAC policy support, keyboard end-effector intervention logic, dataset recording paths, and smoke/demo assets under `configs/hilserl_sim`, `src/lerobot/scripts/rl`, and `docs`.

## What This Project Does

- Runs Gymnasium-compatible robot manipulation environments through LeRobot.
- Supports the `gym_hil` Franka Panda MuJoCo task family:
  - `PandaPickCubeKeyboard-v0`
  - `PandaPickCubeGamepad-v0`
  - `PandaPickCubeBase-v0`
- Demonstrates Human-in-the-Loop RL:
  - an actor proposes actions,
  - a human can intervene through keyboard/gamepad control,
  - the learner consumes transitions and updates the SAC policy.
- Records local LeRobot-format demonstration datasets from simulation.
- Trains a visual/state SAC policy using front and wrist camera observations plus robot state.
- Provides keyboard safety examples:
  - random idle action for original HIL smoke behavior,
  - hold after manual timeout,
  - retreat then hold after manual timeout,
  - optional manual rearm before returning to automatic control.
- Includes notes and diagrams explaining the HIL-SERL workflow in `docs/hilserl_sim_notes.html`.

## Repository Layout

```text
configs/hilserl_sim/
  gym_hil_keyboard_smoke.json          # keyboard smoke/demo environment
  gym_hil_keyboard_record_1ep.json     # one-episode recording demo
  gym_hil_keyboard_hold_demo.json      # timeout-to-hold safety demo
  gym_hil_keyboard_retreat_demo.json   # timeout-to-retreat safety demo
  train_gym_hil_keyboard_smoke.json    # SAC actor/learner training config
  upstream/                            # reference upstream HIL configs

src/lerobot/
  scripts/rl/gym_manipulator.py        # HIL simulation runner and recording path
  scripts/rl/actor.py                  # online actor process
  scripts/rl/learner.py                # learner process
  policies/sac/                        # SAC policy implementation
  transport/                           # gRPC transport between actor and learner

tests/rl/
  test_gym_manipulator_recording.py    # keyboard intervention and safety-state tests
  test_actor_learner.py                # actor/learner transport tests

docs/
  source/hilserl_sim.mdx               # upstream-style HIL simulation guide
  hilserl_sim_notes.html               # local Chinese analysis/demo notes
  img/                                 # local explanatory images

outputs/
  hilserl_sim/                         # local generated datasets, logs, checkpoints
```

## Requirements

The current HIL simulation path expects:

- Linux is recommended.
- Python 3.10 or a compatible LeRobot environment.
- NVIDIA GPU for the provided CUDA configs.
- A working MuJoCo display context for interactive simulation windows.
- Keyboard or gamepad input for teleoperation/intervention.
- Python dependencies from LeRobot plus the `hilserl` extra, especially:
  - `gym-hil>=0.1.9`
  - `gymnasium`
  - `torch`
  - `torchvision`
  - `grpcio`
  - `placo`

This workspace already contains a local `.venv` in many development setups. The examples below use `.venv/bin/python` when possible.

## Setup

From the repository root:

Recommended setup path:

```bash
scripts/setup_environment.sh
source .venv/bin/activate
```

The setup script creates or reuses `.venv`, installs the HIL-SERL runtime dependencies, and runs a small import check for `gym_hil`, MuJoCo, PyTorch, torchvision, gRPC, and protobuf.

Useful script options:

```bash
# Reuse the current environment without installing or checking dependencies.
scripts/setup_environment.sh --skip-install --skip-check

# Create the environment with a specific Python executable.
scripts/setup_environment.sh --python python3.10

# Remove and recreate the virtual environment.
scripts/setup_environment.sh --recreate

# Install only the minimal HIL-SERL runtime dependencies.
scripts/setup_environment.sh --install-mode minimal
```

Manual fallback:

```bash
# Use the existing local environment if it is available.
source .venv/bin/activate

# If you need to install the project dependencies from a fresh checkout:
pip install -e ".[hilserl]"
```

If your checkout does not include packaging metadata such as `pyproject.toml`, use the already prepared environment for this workspace or restore the full LeRobot project metadata before running the editable install command.

Quick dependency check:

```bash
.venv/bin/python - <<'PY'
import gymnasium
import gym_hil
import mujoco
import torch

print("gymnasium:", gymnasium.__version__)
print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
PY
```

## Reproduce the Demos

Run all commands from the repository root.

### 1. Keyboard Smoke Demo

This starts the Franka Panda pick-cube simulation using keyboard end-effector intervention. The smoke config keeps the original HIL-SERL style behavior where automatic/random actions continue when there is no manual intervention.

```bash
.venv/bin/python -m lerobot.scripts.rl.gym_manipulator \
  --config_path configs/hilserl_sim/gym_hil_keyboard_smoke.json
```

Useful config values:

- `task`: `PandaPickCubeKeyboard-v0`
- `control_mode`: `keyboard_ee`
- `idle_behavior`: `random`
- `device`: `cuda`
- `fps`: `10`
- observations:
  - `observation.images.front`: `3 x 128 x 128`
  - `observation.images.wrist`: `3 x 128 x 128`
  - `observation.state`: `18`
- action:
  - `action`: `3`

Use this demo to verify that the environment, rendering, keyboard control path, and LeRobot observation/action mapping work.

## Keyboard Intervention Controls

Keyboard teleoperation in `gym_manipulator.py` is **intervention-oriented**, not always-on manual control. In the smoke config, the environment keeps running automatic/random actions until you explicitly enable intervention.

### Before You Start

1. Wait for the MuJoCo viewer window to open.
2. Press **`i`** once and confirm the log line `Intervention ENABLED`.
3. Only then do the movement and gripper keys below take effect.
4. Press **`i`** again to return to automatic control (`Intervention DISABLED`).

If you skip step 2, arrow keys and Shift/Ctrl will **not** move the robot even though the simulation is running.

### Key Map

| Key | Action |
| --- | --- |
| `i` | Enable / disable human intervention |
| `↑` `↓` `←` `→` | Move end-effector in the X-Y plane |
| `Left Shift` (hold) | Move down along Z axis (Z-) |
| `Right Shift` (hold) | Move up along Z axis (Z+) |
| `Left Ctrl` (hold) | Close gripper |
| `Right Ctrl` (hold) | Open gripper |
| `s` | End episode as success |
| `f` | End episode as failure |
| `r` | Re-record the current episode |
| `c` | Confirm re-arm to AUTO after a timeout-triggered safe state (hold/retreat demos only) |

### Action Format

Each intervention step sends a discrete end-effector delta:

- `dx`, `dy`, `dz`: each is `-1`, `0`, or `+1`
- `gripper`: `0 = close`, `1 = hold`, `2 = open`

Example log line while intervening:

```text
Intervention input: teleop=[dx=+0, dy=-1, dz=+0, gripper=1(hold)] applied=[...] state=manual
```

### Notes

- **Z axis:** use `Left Shift` for downward motion and `Right Shift` for upward motion. Keep the key held while moving.
- **Gripper:** hold `Left Ctrl` to close and `Right Ctrl` to open. Releasing both returns to hold (`gripper=1`).
- **MuJoCo shortcut conflict:** MuJoCo's viewer also binds `I` to inertia-box visualization. This project hides that overlay automatically after each step so it does not block teleoperation.
- **Clean exit:** the runner calls `env.close()` on shutdown. You should see `Closing environment...` at the end instead of a segmentation fault.

For safer manual demos, use `gym_hil_keyboard_hold_demo.json` or `gym_hil_keyboard_retreat_demo.json`, which add manual timeout, safe hold/retreat, and optional re-arm confirmation.

### 2. Record One Demonstration Episode

This records a one-episode local dataset from the keyboard simulation path.

```bash
.venv/bin/python -m lerobot.scripts.rl.gym_manipulator \
  --config_path configs/hilserl_sim/gym_hil_keyboard_record_1ep.json
```

The dataset is written under the `dataset_root` declared in the config, currently:

```text
outputs/hilserl_sim/demos/gym_hil_keyboard_record_1ep_20260518_210426
```

The dataset includes the configured image streams, robot state, and selected action. During teleoperation, the recorded action prefers the human intervention action when one is present.

### 3. Run Online HIL-SERL Training

The training demo uses a learner process and an actor process. Start the learner first:

```bash
.venv/bin/python -m lerobot.scripts.rl.learner \
  --config_path configs/hilserl_sim/train_gym_hil_keyboard_smoke.json
```

In a second terminal, start the actor:

```bash
.venv/bin/python -m lerobot.scripts.rl.actor \
  --config_path configs/hilserl_sim/train_gym_hil_keyboard_smoke.json
```

The training config uses:

- `output_dir`: `outputs/hilserl_sim/train_keyboard_smoke_live`
- `policy.type`: `sac`
- `dataset.repo_id`: `aractingi/franka_sim_pick_lift_6`
- `learner_host`: `127.0.0.1`
- `learner_port`: `50051`
- `concurrency`: `threads`
- `steps`: `10` for the local smoke config
- checkpoints under `outputs/hilserl_sim/train_keyboard_smoke_live/checkpoints`

The actor collects interactions from the environment and sends transitions to the learner over gRPC. The learner updates policy parameters and can push updated parameters back to the actor.

### 4. Safety Hold Demo

This configuration is closer to a conservative manual-control demo. When manual input times out, the action moves to a safe hold state and requires manual rearm before returning to automatic behavior.

```bash
.venv/bin/python -m lerobot.scripts.rl.gym_manipulator \
  --config_path configs/hilserl_sim/gym_hil_keyboard_hold_demo.json
```

Important config values:

- `idle_behavior`: `hold`
- `manual_input_timeout_s`: `2.0`
- `timeout_behavior`: `hold`
- `require_manual_rearm_after_timeout`: `true`

### 5. Safety Retreat Demo

This configuration retreats for a short fixed number of steps after manual timeout, then falls back to safe hold.

```bash
.venv/bin/python -m lerobot.scripts.rl.gym_manipulator \
  --config_path configs/hilserl_sim/gym_hil_keyboard_retreat_demo.json
```

Important config values:

- `idle_behavior`: `hold`
- `manual_input_timeout_s`: `2.0`
- `timeout_behavior`: `retreat`
- `safe_retreat_steps`: `8`
- `safe_retreat_action`: `[0.0, 0.0, 1.0, 1.0]`
- `require_manual_rearm_after_timeout`: `true`

## Main Config Files

| File | Purpose |
| --- | --- |
| `configs/hilserl_sim/gym_hil_keyboard_smoke.json` | Interactive keyboard smoke demo with original HIL-style random idle behavior. |
| `configs/hilserl_sim/gym_hil_keyboard_record_1ep.json` | One-episode local demonstration recording. |
| `configs/hilserl_sim/train_gym_hil_keyboard_smoke.json` | SAC actor/learner training smoke config. |
| `configs/hilserl_sim/gym_hil_keyboard_hold_demo.json` | Manual timeout enters safe hold. |
| `configs/hilserl_sim/gym_hil_keyboard_retreat_demo.json` | Manual timeout enters short retreat, then hold. |

## How the HIL Control Loop Works

At a high level:

1. `gym_manipulator.py` creates the configured HIL environment.
2. The environment emits image observations, state observations, rewards, and info.
3. An automatic action is sampled or produced by a policy.
4. Keyboard/gamepad intervention can override that automatic action.
5. Recording prefers the intervention action when one exists.
6. In training mode, the actor sends transitions/interactions to the learner.
7. The learner updates SAC networks and periodically provides newer parameters.

The key point is that manual control is intervention-oriented. In the smoke config, no manual input does not necessarily mean "do nothing"; the automatic path can still act. Use the hold or retreat configs when you want a safer manual-control demonstration.

## Tests

Run the focused HIL keyboard tests:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  tests/rl/test_gym_manipulator_recording.py
```

Run the setup-script static tests:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  tests/test_setup_environment_script.py
```

Run the actor/learner transport tests:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  tests/rl/test_actor_learner.py
```

These tests cover action selection, intervention precedence, idle behavior, manual timeout state transitions, safe hold/retreat behavior, and actor/learner data transport.

## Generated Outputs

Runtime outputs are written under `outputs/hilserl_sim`, including:

- logs,
- recorded local datasets,
- offline/online image frames,
- SAC checkpoints,
- policy config snapshots,
- training state files.

These files are useful for local reproduction and debugging but can become large. Treat them as generated artifacts unless you explicitly need to preserve a run.

## Existing Documentation

- `docs/source/hilserl_sim.mdx`: English HIL simulation guide in the LeRobot documentation style.
- `docs/hilserl_sim_notes.html`: local Chinese notes explaining the paper images, demo commands, keyboard intervention key map, safety timeout changes, and validation notes.
- `docs/img/`: images used by the local notes.
- `docs/README.md`: documentation-build instructions for the LeRobot docs site.

## Troubleshooting

### The robot moves without keyboard input

This is expected for `gym_hil_keyboard_smoke.json`. The smoke config uses `idle_behavior: "random"` to demonstrate the original HIL training flow where automatic actions continue and human input intervenes only when needed. Use `gym_hil_keyboard_hold_demo.json` for a hold-by-default behavior.

### Arrow keys do nothing

Intervention is disabled by default. Press **`i`** first and wait for `Intervention ENABLED` in the terminal log.

### Program crashes with `Segmentation fault` at exit

Older runs could exit without closing the MuJoCo viewer. The current `gym_manipulator.py` closes the environment in a `finally` block. Update to the latest code and confirm you see `Closing environment...` before the process exits.

### CUDA is unavailable

The provided configs use `"device": "cuda"`. If you only have CPU available, change the config device values to `"cpu"` and expect slower execution. Some vision or simulation paths may still be impractical without GPU acceleration.

### MuJoCo window does not open

Interactive demos need a valid graphics/display context. On a headless server, configure EGL/OSMesa or run from a machine with display forwarding.

### Editable install fails

This workspace may not include the root packaging metadata in all snapshots. If `pip install -e ".[hilserl]"` fails because `pyproject.toml` or `setup.py` is missing, use the existing `.venv` or restore the full upstream LeRobot checkout metadata.

## Citation

The HIL-SERL simulation guide references:

```bibtex
@article{luo2024precise,
  title={Precise and Dexterous Robotic Manipulation via Human-in-the-Loop Reinforcement Learning},
  author={Luo, Jianlan and Xu, Charles and Wu, Jeffrey and Levine, Sergey},
  journal={arXiv preprint arXiv:2410.21845},
  year={2024}
}
```
