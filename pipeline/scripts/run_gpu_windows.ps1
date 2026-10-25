# One-shot runner for Windows + NVIDIA RTX 4060 (the Intel UHD adapter is never used: CUDA cannot see it, and the
# script refuses any device whose name does not contain "4060").
# Usage: run it from PowerShell (NOT cmd.exe, and do not paste its lines one by one):
#   powershell -ExecutionPolicy Bypass -File pipeline\scripts\run_gpu_windows.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (-not (Test-Path .venv-gpu)) { python -m venv .venv-gpu }
& .\.venv-gpu\Scripts\Activate.ps1
python -m pip install --upgrade pip
# Install CUDA torch only when this venv has none (a working cu126/cu128 build is kept as is).
$ErrorActionPreference = "Continue"   # a failed import writes to stderr, which Stop would turn into a crash
python -c "import torch" 2>&1 | Out-Null
$haveTorch = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = "Stop"
if (-not $haveTorch) { pip install torch --index-url https://download.pytorch.org/whl/cu128 }
pip install transformers sentence-transformers scikit-learn scipy pandas pyyaml pydantic indic-transliteration
$env:PYTHONPATH = "src"
$env:HF_HUB_OFFLINE = "1"   # models come from pipeline\models\<repo-name>, nothing is downloaded
python -c "import torch; print('torch', torch.__version__, [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())])"
# Models live in <prototype>\models (next to <prototype>\datasets), NOT inside the repo. Override: $env:CC_MODELS_DIR
$models = if ($env:CC_MODELS_DIR) { $env:CC_MODELS_DIR } else { Join-Path $PSScriptRoot "..\..\..\models" }
$models = (Resolve-Path $models -ErrorAction Stop).Path
foreach ($m in "multilingual-e5-base", "muril-base-cased", "xlm-roberta-base") {
    if (-not (Test-Path (Join-Path $models "$m\config.json"))) { throw "Missing model folder: $models\$m (needs config.json)" }
}
Write-Host "models dir: $models"
function Run { & python @args; if ($LASTEXITCODE -ne 0) { throw "FAILED (exit $LASTEXITCODE): python $args" } }   # stop at the first failing step
# 1) data-prep for the external multilingual dataset (CPU; also rewrites backend\app\rules\dataset_vocab.json)
$csv = Join-Path $PSScriptRoot "..\..\..\datasets\multilingual_triage\multilingual_medical_symptom_triage.csv"
if (-not (Test-Path $csv)) { $csv = Read-Host "Path to multilingual_medical_symptom_triage.csv" }
Run scripts\prepare_multilingual_triage.py --csv $csv
# 2) baseline: frozen then fine-tuned encoders on the 66 CareCompass texts (reports 06b)
Run scripts\gpu_encoder_eval.py --mode frozen   --gpu-name 4060 --models-dir $models --models intfloat/multilingual-e5-base google/muril-base-cased xlm-roberta-base
Run scripts\gpu_encoder_eval.py --mode finetune --gpu-name 4060 --seeds 3 --models-dir $models
# 3) two-stage: adapt each encoder on the external dataset (disease naming), then LOFO on CareCompass (report 10)
$env:PYTHONPATH = "src;scripts"
Run scripts\gpu_finetune_multilingual.py --gpu-name 4060 --models-dir $models --seeds 3
Write-Host "COMMIT these small files (not models_ft): pipeline\results\*, pipeline\reports\06b_*.md, pipeline\reports\09_*.md, pipeline\reports\10_*.md, backend\app\rules\dataset_vocab.json"
Write-Host "Done. Results: pipeline\reports\06b_encoders_*.md, pipeline\reports\10_gpu_multilingual.md, pipeline\results\"
