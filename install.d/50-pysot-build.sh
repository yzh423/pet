# shellcheck shell=bash

echo "==> PySOT build dependencies and setup.py build_ext --inplace ($PYSOT_ROOT) ..."
if [[ ! -f "$PYSOT_ROOT/setup.py" ]]; then
  echo "Error: PySOT checkout missing at $PYSOT_ROOT (keep bundled pysot-master/ or git clone https://github.com/STVIR/pysot.git pysot)"
  exit 1
fi
pip install pyyaml yacs tqdm colorama matplotlib cython tensorboardX
cd "$PYSOT_ROOT"
python setup.py build_ext --inplace
cd "$REPO_ROOT"
