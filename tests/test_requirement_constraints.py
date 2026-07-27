from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _exact_pins(path: Path) -> dict[str, str]:
    pins = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith("-") or "==" not in line:
            continue
        name, version = line.split("==", 1)
        pins[name.strip().lower().replace("_", "-")] = version.strip()
    return pins


def test_service_constraint_pins_do_not_conflict():
    api_pins = _exact_pins(ROOT / "biolog_api" / "constraints.txt")
    streamlit_pins = _exact_pins(ROOT / "biolog_streamlit" / "constraints.txt")

    conflicts = {
        name: (api_pins[name], streamlit_pins[name])
        for name in api_pins.keys() & streamlit_pins.keys()
        if api_pins[name] != streamlit_pins[name]
    }

    assert conflicts == {}


def test_combined_test_requirements_include_both_services_and_pytest():
    lines = {
        line.split("#", 1)[0].strip()
        for line in (ROOT / "requirements-test.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.split("#", 1)[0].strip()
    }

    assert "-r biolog_api/requirements.txt" in lines
    assert "-r biolog_streamlit/requirements.txt" in lines
    assert "pytest==8.3.5" in lines
