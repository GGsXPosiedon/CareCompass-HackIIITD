# One-shot runner for Windows + NVIDIA RTX 4060 (the Intel UHD adapter is never used: CUDA cannot see it, and the
# script refuses any device whose name does not contain "4060").
# Usage (PowerShell, from anywhere):   powershell -ExecutionPolicy Bypass -File scripts\run_gpu_windows.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (-not (Test-Path .venv-gpu)) { python -m venv .venv-gpu }
& .\.venv-gpu\Scripts\Activate.ps1
python -m pip install --upgrade pip
# CUDA 12.8 wheels; if this index fails for your driver, try cu126 or cu130.
pip install torch --index-url https://download.pytorch.org/whl/cu128
pip install transformers sentence-transformers scikit-learn scipy pandas pyyaml pydantic indic-transliteration
$env:PYTHONPATH = "src"
$env:HF_HUB_OFFLINE = "1"   # models come from pipeline\models\<repo-name>, nothing is downloaded
python -c "import torch; print('torch', torch.__version__, [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())])"
python scripts\gpu_encoder_eval.py --mode frozen   --gpu-name 4060 --models-dir ..\models
python scripts\gpu_encoder_eval.py --mode finetune --gpu-name 4060 --seeds 3 --models-dir ..\models
Write-Host "Done. Results: pipeline\reports\06b_encoders_*.md and pipeline\data\processed\triage_encoders_*.csv"
