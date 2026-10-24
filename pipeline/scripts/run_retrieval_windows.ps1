# Stage 7a on the RTX 4060: checks CUDA first, then runs retrieval (BM25 / dense / hybrid) with each local encoder.
# Usage (PowerShell):   powershell -ExecutionPolicy Bypass -File scripts\run_retrieval_windows.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (-not (Test-Path .venv-gpu)) { python -m venv .venv-gpu }
& .\.venv-gpu\Scripts\Activate.ps1
python -m pip install --upgrade pip
$ErrorActionPreference = "Continue"   # a failed import writes to stderr, which Stop would turn into a crash
python -c "import torch" 2>&1 | Out-Null
$haveTorch = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = "Stop"
if (-not $haveTorch) { pip install torch --index-url https://download.pytorch.org/whl/cu128 }
pip install transformers sentence-transformers scikit-learn scipy pandas pyyaml pydantic indic-transliteration
$env:PYTHONPATH = "src"
$env:HF_HUB_OFFLINE = "1"
python -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())])"
python scripts\gpu_retrieval_eval.py --gpu-name 4060 --models-dir ..\models --models intfloat/multilingual-e5-base google/muril-base-cased xlm-roberta-base
Write-Host "Done. See pipeline\reports\07_retrieval.md"
