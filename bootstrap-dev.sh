#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"

py_ver="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
case "$py_ver" in
  3.11|3.12|3.13) ;;
  *)
    echo "Unsupported Python version ($py_ver). Use Python 3.11, 3.12, or 3.13." >&2
    exit 2
    ;;
esac

if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --only-binary=:all: -r requirements.txt

python ./convertUi.py

echo "Dev environment ready."
