#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

source venv/bin/activate

NOTEBOOKS=(
    "without_XAI/without_xai.ipynb"
    "with_XAI/with_xai.ipynb"
    "enforce_knowledge/enforce_knowledge.ipynb"
)

SCRIPTS=()

for nb in "${NOTEBOOKS[@]}"; do
    echo "========================================"
    echo "Converting: $nb"
    echo "========================================"
    jupyter nbconvert --to python "$nb"

    py_file="${nb%.ipynb}.py"
    SCRIPTS+=("$py_file")

    nb_dir="$(dirname "$py_file")"
    nb_base="$(basename "$py_file")"

    echo "Running: $py_file (cwd: $nb_dir) - $nb_base"
    echo "----------------------------------------"
    (cd "$nb_dir" && ipython "$nb_base")
    echo ""
done

echo "========================================"
echo "Cleaning up generated scripts..."
echo "========================================"
for py_file in "${SCRIPTS[@]}"; do
    rm -f "$py_file"
    echo "  Removed $py_file"
done

echo ""
echo "All done."
