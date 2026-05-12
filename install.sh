#!/usr/bin/env bash
set -e

if ! command -v python3 >/dev/null; then
    echo "Python not found. Install: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

if ! command -v nvcc >/dev/null; then
    echo "WARNING: nvcc not found."
    echo "Install CUDA Toolkit 12.x:"
    echo "  https://developer.nvidia.com/cuda-downloads"
    echo ""
    echo "Then add to ~/.bashrc:"
    echo "  export PATH=/usr/local/cuda/bin:\$PATH"
    echo "  export LD_LIBRARY_PATH=/usr/local/cuda/lib64:\$LD_LIBRARY_PATH"
    exit 1
fi

if ! nvidia-smi >/dev/null 2>&1; then
    echo "nvidia-smi not working. Install NVIDIA driver:"
    echo "  sudo ubuntu-drivers autoinstall"
    exit 1
fi

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo ""
echo "Installed. Run: python3 pfft_miner.py"
