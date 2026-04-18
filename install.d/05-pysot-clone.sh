# shellcheck shell=bash
# Optional clone of https://github.com/STVIR/pysot only when no checkout exists.
# This repo ships PySOT under pysot-master/; clone fills pysot/ as a fallback.

_pysot_ok() {
  [[ -d "$1/pysot" ]] && [[ -f "$1/setup.py" ]]
}

if [[ "${SKIP_PYSOT_CLONE:-0}" == "1" ]]; then
  echo "==> SKIP_PYSOT_CLONE=1: not cloning"
elif _pysot_ok "$REPO_ROOT/pysot-master"; then
  echo "==> Using bundled PySOT: $REPO_ROOT/pysot-master"
elif _pysot_ok "$REPO_ROOT/pysot"; then
  echo "==> Using separate clone: $REPO_ROOT/pysot"
elif ! command -v git >/dev/null 2>&1; then
  echo "Warning: git not found; cannot clone. Use bundled pysot-master/ or install git."
else
  echo "==> No PySOT checkout found; cloning STVIR/pysot → $REPO_ROOT/pysot ..."
  git clone --depth 1 https://github.com/STVIR/pysot.git "$REPO_ROOT/pysot"
fi
