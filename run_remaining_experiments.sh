#!/bin/bash
# Run remaining experiments:
# - cyber_intrusion_data: without_xai only (with_xai already complete)
# - NSL_KDD: all experiments (both with_xai and without_xai)

set -e

cd /home/beloin/Documents/pos-grad/masters/soc_xai

echo "=========================================="
echo "Running Remaining Experiments"
echo "=========================================="
echo ""

# Function to run experiment
run_experiment() {
	dataset=$1
	script=$2
	input=$3
	logname=$4

	echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting: $dataset/$script $input"

	cd "/home/beloin/Documents/pos-grad/masters/soc_xai/$dataset"

	../venv/bin/python -u "$script" "$input" >"outputs/${logname}.log" 2>&1

	echo "[$(date '+%Y-%m-%d %H:%M:%S')] Completed: $dataset/$script $input"
	echo ""
}

# ============================================
# cyber_intrusion_data: without_xai only
# ============================================

echo "========== CYBER_INTRUSION_DATA (without_xai) =========="
echo ""

cd /home/beloin/Documents/pos-grad/masters/soc_xai/cyber_intrusion_data

run_experiment "cyber_intrusion_data" "without_xai.py" "inputs/system_prompt_without_xai.input.json" "system_prompt_without_xai" &
wait

run_experiment "cyber_intrusion_data" "without_xai.py" "inputs/context_prompt_without_xai.input.json" "context_prompt_without_xai" &
wait

run_experiment "cyber_intrusion_data" "without_xai.py" "inputs/role_based_without_xai.input.json" "role_based_without_xai" &
wait

run_experiment "cyber_intrusion_data" "without_xai.py" "inputs/few_shot_without_xai.input.json" "few_shot_without_xai" &
wait

run_experiment "cyber_intrusion_data" "without_xai.py" "inputs/cot_without_xai.input.json" "cot_without_xai" &
wait

# self_consistency already done, but included for completeness
run_experiment "cyber_intrusion_data" "without_xai.py" "inputs/self_consistency.input.json" "self_consistency_without_xai" &
wait

# ============================================
# NSL_KDD: all experiments
# ============================================

echo "========== NSL_KDD (with_xai + without_xai) =========="
echo ""

cd /home/beloin/Documents/pos-grad/masters/soc_xai/NSL_KDD

# with_xai experiments (resume from role_based)
run_experiment "NSL_KDD" "with_xai.py" "inputs/role_based_with_xai.input.json" "role_based_with_xai" &
wait

run_experiment "NSL_KDD" "with_xai.py" "inputs/few_shot_with_xai.input.json" "few_shot_with_xai" &
wait

run_experiment "NSL_KDD" "with_xai.py" "inputs/cot_with_xai.input.json" "cot_with_xai" &
wait

# without_xai experiments
run_experiment "NSL_KDD" "without_xai.py" "inputs/system_prompt_without_xai.input.json" "system_prompt_without_xai" &
wait

run_experiment "NSL_KDD" "without_xai.py" "inputs/context_prompt_without_xai.input.json" "context_prompt_without_xai" &
wait

run_experiment "NSL_KDD" "without_xai.py" "inputs/role_based_without_xai.input.json" "role_based_without_xai" &
wait

run_experiment "NSL_KDD" "without_xai.py" "inputs/few_shot_without_xai.input.json" "few_shot_without_xai" &
wait

run_experiment "NSL_KDD" "without_xai.py" "inputs/cot_without_xai.input.json" "cot_without_xai" &
wait

run_experiment "NSL_KDD" "without_xai.py" "inputs/self_consistency.input.json" "self_consistency_without_xai" &
wait

echo "=========================================="
echo "All experiments completed!"
echo "=========================================="
