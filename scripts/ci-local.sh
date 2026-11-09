#!/usr/bin/env bash
# Local equivalent of the manually triggered Source checks workflow.
set -euo pipefail
cd "$(dirname "$0")/.."
ci_venv="${OPENWORLD_CI_VENV:-.venv-ci}"
python3.13 -m venv "$ci_venv"
ci_python="$ci_venv/bin/python"
"$ci_python" -m pip install --disable-pip-version-check -r app/requirements.txt
"$ci_python" -m pip check
"$ci_python" -m compileall -q app/backend ops
"$ci_python" -m unittest discover -s tests -v
