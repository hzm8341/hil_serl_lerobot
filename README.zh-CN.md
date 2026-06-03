# LeRobot HIL-SERL 仿真工作区

[English](README.md) | 中文

本项目是一个基于 LeRobot 的 Human-in-the-Loop Soft Actor-Critic 强化学习仿真工作区。当前重点是通过 `gym_hil` 和 MuJoCo 运行 Franka Panda 机械臂拾取方块任务，支持键盘/手柄接管、示范数据录制、在线 actor/learner 训练，以及更接近工业安全直觉的键盘超时保持/退让策略。

英文版 `README.md` 是主文档，中文版本保留主要复现信息，方便快速上手。

## 项目功能

- 通过 LeRobot 运行 Gymnasium 兼容的机器人操作环境。
- 支持 `gym_hil` Franka Panda MuJoCo 任务：
  - `PandaPickCubeKeyboard-v0`
  - `PandaPickCubeGamepad-v0`
  - `PandaPickCubeBase-v0`
- 支持 HIL 强化学习流程：
  - actor 产生自动动作；
  - 人可以通过键盘或手柄接管；
  - learner 消费 transition 并更新 SAC 策略。
- 支持从仿真中录制 LeRobot 格式本地数据集。
- 使用前视角、腕部相机和机器人状态训练 SAC 策略。
- 提供安全演示配置：
  - 原始 smoke 随机 idle 行为；
  - 人工输入超时后保持；
  - 人工输入超时后先退让再保持；
  - 超时后要求人工重新确认再恢复自动控制。

## 目录结构

```text
configs/hilserl_sim/
  gym_hil_keyboard_smoke.json          # 键盘 smoke/机制演示
  gym_hil_keyboard_record_1ep.json     # 单 episode 录制 demo
  gym_hil_keyboard_hold_demo.json      # 超时后安全保持
  gym_hil_keyboard_retreat_demo.json   # 超时后安全退让
  train_gym_hil_keyboard_smoke.json    # SAC actor/learner 训练配置
  upstream/                            # 上游参考配置

src/lerobot/
  scripts/rl/gym_manipulator.py        # HIL 仿真运行与录制入口
  scripts/rl/actor.py                  # 在线 actor
  scripts/rl/learner.py                # learner
  policies/sac/                        # SAC 策略实现
  transport/                           # actor/learner 的 gRPC 通信

tests/rl/
  test_gym_manipulator_recording.py    # 键盘接管与安全状态测试
  test_actor_learner.py                # actor/learner 通信测试

docs/
  source/hilserl_sim.mdx               # 英文 HIL 仿真教程
  hilserl_sim_notes.html               # 中文分析与复现笔记
  img/                                 # 说明图片

outputs/
  hilserl_sim/                         # 本地生成的数据、日志和 checkpoint
```

## 环境要求

推荐环境：

- Linux；
- Python 3.10 或兼容 LeRobot 的 Python 环境；
- NVIDIA GPU；
- 可打开 MuJoCo 图形窗口的显示环境；
- 键盘或手柄；
- LeRobot 依赖和 `hilserl` extra，主要包括 `gym-hil>=0.1.9`、`torch`、`torchvision`、`grpcio`、`placo` 等。

如果当前工作区已有 `.venv`，优先使用它：

```bash
source .venv/bin/activate
```

新环境安装方式：

```bash
pip install -e ".[hilserl]"
```

如果当前快照没有 `pyproject.toml` 或 `setup.py`，说明这个工作区可能不是完整打包快照，请使用已有 `.venv`，或恢复完整 LeRobot 项目元数据后再执行 editable install。

快速检查：

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

## 复现 Demo

所有命令都在项目根目录执行。

### 1. 键盘 Smoke Demo

运行 Franka Panda 拾取方块仿真，使用键盘末端控制进行人工接管。

```bash
.venv/bin/python -m lerobot.scripts.rl.gym_manipulator \
  --config_path configs/hilserl_sim/gym_hil_keyboard_smoke.json
```

关键配置：

- `task`: `PandaPickCubeKeyboard-v0`
- `control_mode`: `keyboard_ee`
- `idle_behavior`: `random`
- `device`: `cuda`
- `fps`: `10`

注意：这个配置保留原始 HIL-SERL smoke 风格，没有人工接管时自动动作仍可能继续执行。它适合看“自动策略 + 人工接管”的机制，不适合作为默认安全手动控制示例。

### 2. 录制一个 Episode

```bash
.venv/bin/python -m lerobot.scripts.rl.gym_manipulator \
  --config_path configs/hilserl_sim/gym_hil_keyboard_record_1ep.json
```

数据会写入配置中的 `dataset_root`，当前为：

```text
outputs/hilserl_sim/demos/gym_hil_keyboard_record_1ep_20260518_210426
```

录制内容包括前视角图像、腕部图像、机器人状态和动作。存在人工接管动作时，录制逻辑优先保存人工接管动作。

### 3. 在线 HIL-SERL 训练

先启动 learner：

```bash
.venv/bin/python -m lerobot.scripts.rl.learner \
  --config_path configs/hilserl_sim/train_gym_hil_keyboard_smoke.json
```

另开一个终端启动 actor：

```bash
.venv/bin/python -m lerobot.scripts.rl.actor \
  --config_path configs/hilserl_sim/train_gym_hil_keyboard_smoke.json
```

训练配置要点：

- `output_dir`: `outputs/hilserl_sim/train_keyboard_smoke_live`
- `policy.type`: `sac`
- `dataset.repo_id`: `aractingi/franka_sim_pick_lift_6`
- `learner_host`: `127.0.0.1`
- `learner_port`: `50051`
- `steps`: `10`

actor 从环境采集交互并通过 gRPC 发给 learner；learner 更新 SAC 策略并可把新参数传回 actor。

### 4. 超时保持 Demo

更接近安全手动控制：人工输入超时后进入保持状态，并要求人工重新确认后才能恢复自动。

```bash
.venv/bin/python -m lerobot.scripts.rl.gym_manipulator \
  --config_path configs/hilserl_sim/gym_hil_keyboard_hold_demo.json
```

关键配置：

- `idle_behavior`: `hold`
- `manual_input_timeout_s`: `2.0`
- `timeout_behavior`: `hold`
- `require_manual_rearm_after_timeout`: `true`

### 5. 超时退让 Demo

人工输入超时后先执行固定步数的退让动作，然后进入保持。

```bash
.venv/bin/python -m lerobot.scripts.rl.gym_manipulator \
  --config_path configs/hilserl_sim/gym_hil_keyboard_retreat_demo.json
```

关键配置：

- `idle_behavior`: `hold`
- `manual_input_timeout_s`: `2.0`
- `timeout_behavior`: `retreat`
- `safe_retreat_steps`: `8`
- `safe_retreat_action`: `[0.0, 0.0, 1.0, 1.0]`
- `require_manual_rearm_after_timeout`: `true`

## 测试

键盘接管与安全状态测试：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  tests/rl/test_gym_manipulator_recording.py
```

actor/learner 通信测试：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  tests/rl/test_actor_learner.py
```

## 常见问题

### 为什么不按键机械臂也会动？

`gym_hil_keyboard_smoke.json` 使用 `idle_behavior: "random"`，这是为了展示原始 HIL 训练流程：自动策略持续运行，人类只在需要时接管。如果希望不输入时保持静止，请使用 `gym_hil_keyboard_hold_demo.json`。

### CUDA 不可用怎么办？

当前配置默认 `"device": "cuda"`。如果只能使用 CPU，可以把配置里的 device 改为 `"cpu"`，但仿真和视觉策略会明显变慢。

### MuJoCo 窗口打不开怎么办？

交互 demo 需要图形显示环境。无头服务器需要配置 EGL/OSMesa，或使用带显示转发的机器运行。

### 输出文件在哪里？

本地运行产生的数据、日志和 checkpoint 通常在：

```text
outputs/hilserl_sim/
```

这些是运行产物，体积可能较大，通常不应作为源码文档的一部分提交。

## 相关文档

- `docs/source/hilserl_sim.mdx`：英文 HIL 仿真教程。
- `docs/hilserl_sim_notes.html`：中文复现和分析笔记。
- `docs/img/`：说明图片。
- `docs/README.md`：LeRobot 文档站构建说明。

## 引用

```bibtex
@article{luo2024precise,
  title={Precise and Dexterous Robotic Manipulation via Human-in-the-Loop Reinforcement Learning},
  author={Luo, Jianlan and Xu, Charles and Wu, Jeffrey and Levine, Sergey},
  journal={arXiv preprint arXiv:2410.21845},
  year={2024}
}
```

