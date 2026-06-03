#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_MODE="auto"
SKIP_CHECK=0
RECREATE=0
PIP_ARGS=()

usage() {
  cat <<'USAGE'
Usage: scripts/setup_environment.sh [options]

Create or reuse a Python virtual environment for the LeRobot HIL-SERL
simulation workspace.

Options:
  --venv-dir PATH       Virtual environment path. Default: .venv
  --python PATH         Python executable used to create the venv. Default: python3
  --install-mode MODE   auto, editable, minimal, or none. Default: auto
  --skip-install        Same as --install-mode none
  --skip-check          Do not run Python import checks after setup
  --recreate            Remove and recreate the virtual environment
  --pip-arg ARG         Extra argument passed to pip install. Repeatable
  -h, --help            Show this help

Examples:
  scripts/setup_environment.sh
  scripts/setup_environment.sh --venv-dir .venv --python python3.10
  scripts/setup_environment.sh --skip-install
  scripts/setup_environment.sh --install-mode minimal
USAGE
}

log() {
  printf '[setup] %s\n' "$*"
}

die() {
  printf '[setup] error: %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --venv-dir)
      [[ $# -ge 2 ]] || die "--venv-dir requires a path"
      VENV_DIR="$2"
      shift 2
      ;;
    --python)
      [[ $# -ge 2 ]] || die "--python requires an executable"
      PYTHON_BIN="$2"
      shift 2
      ;;
    --install-mode)
      [[ $# -ge 2 ]] || die "--install-mode requires auto, editable, minimal, or none"
      INSTALL_MODE="$2"
      shift 2
      ;;
    --skip-install)
      INSTALL_MODE="none"
      shift
      ;;
    --skip-check)
      SKIP_CHECK=1
      shift
      ;;
    --recreate)
      RECREATE=1
      shift
      ;;
    --pip-arg)
      [[ $# -ge 2 ]] || die "--pip-arg requires an argument"
      PIP_ARGS+=("$2")
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $1"
      ;;
  esac
done

case "$INSTALL_MODE" in
  auto|editable|minimal|none) ;;
  *) die "invalid --install-mode: $INSTALL_MODE" ;;
esac

if [[ "$RECREATE" == "1" && -e "$VENV_DIR" ]]; then
  log "Removing existing virtual environment: $VENV_DIR"
  rm -rf "$VENV_DIR"
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  log "Creating virtual environment: $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  log "Reusing virtual environment: $VENV_DIR"
fi

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

if [[ "$INSTALL_MODE" != "none" ]]; then
  log "Upgrading pip tooling"
  "$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel "${PIP_ARGS[@]}"
else
  log "Skipping pip tooling upgrade"
fi

has_project_metadata() {
  [[ -f "$ROOT_DIR/pyproject.toml" || -f "$ROOT_DIR/setup.py" || -f "$ROOT_DIR/setup.cfg" ]]
}

install_editable() {
  log "Installing project with HIL-SERL extras"
  "$VENV_PIP" install -e "$ROOT_DIR[hilserl]" "${PIP_ARGS[@]}"
}

install_minimal() {
  log "Installing minimal HIL-SERL runtime dependencies"
  "$VENV_PIP" install \
    "gym-hil>=0.1.9" \
    "gymnasium<1.0.0,>=0.29.1" \
    "torch<2.8.0,>=2.2.1" \
    "torchvision<0.23.0,>=0.21.0" \
    "grpcio==1.73.1" \
    "protobuf==6.31.0" \
    "placo>=0.9.6" \
    "transformers<4.52.0,>=4.50.3" \
    "${PIP_ARGS[@]}"
}

case "$INSTALL_MODE" in
  editable)
    has_project_metadata || die "editable install requested, but no pyproject.toml/setup.py/setup.cfg was found"
    install_editable
    ;;
  minimal)
    install_minimal
    ;;
  none)
    log "Skipping dependency installation"
    ;;
  auto)
    if has_project_metadata; then
      install_editable
    else
      log "No project packaging metadata found; installing minimal runtime dependencies"
      install_minimal
      log "Editable LeRobot install was skipped because pyproject.toml/setup.py/setup.cfg is absent"
    fi
    ;;
esac

if [[ "$SKIP_CHECK" == "0" ]]; then
  log "Running import checks"
  "$VENV_PYTHON" - <<'PY'
import importlib.util
import sys

required_modules = [
    "gymnasium",
    "gym_hil",
    "mujoco",
    "torch",
    "torchvision",
    "grpc",
    "google.protobuf",
]

missing = [name for name in required_modules if importlib.util.find_spec(name) is None]
if missing:
    print("Missing modules:", ", ".join(missing), file=sys.stderr)
    raise SystemExit(1)

import torch

print("Python:", sys.version.split()[0])
print("Torch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
PY
fi

cat <<EOF

Environment setup finished.

Activate it with:
  source "$VENV_DIR/bin/activate"

Try the keyboard smoke demo with:
  "$VENV_PYTHON" -m lerobot.scripts.rl.gym_manipulator \\
    --config_path configs/hilserl_sim/gym_hil_keyboard_smoke.json
EOF
