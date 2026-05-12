@echo off
setlocal

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python not found. Install Python 3.10+ from https://python.org
    exit /b 1
)

where nvcc >nul 2>nul
if %errorlevel% neq 0 (
    echo WARNING: nvcc not in PATH. CUDA Toolkit must be installed.
    echo Download: https://developer.nvidia.com/cuda-downloads
    echo Make sure nvcc.exe is in PATH (usually C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x\bin)
    pause
    exit /b 1
)

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Installed. Run: python pfft_miner.py
endlocal
