from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "setup_environment.sh"


def test_setup_environment_script_has_valid_bash_syntax():
    result = subprocess.run(["bash", "-n", str(SCRIPT)], cwd=ROOT, text=True, capture_output=True)

    assert result.returncode == 0, result.stderr


def test_setup_environment_script_documents_core_options_and_checks():
    content = SCRIPT.read_text()

    assert "--venv-dir" in content
    assert "--skip-install" in content
    assert "--skip-check" in content
    assert "install -e" in content
    assert '"gym_hil"' in content
    assert '"torch"' in content
    assert "find_spec" in content
