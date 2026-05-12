#!/usr/bin/env bash
set -e

if ! command -v python3 >/dev/null; then
    echo "Python not found. Install: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

if ! nvidia-smi >/dev/null 2>&1; then
    echo "ERROR: nvidia-smi not working. NVIDIA driver missing."
    echo "Install driver: sudo ubuntu-drivers autoinstall && sudo reboot"
    exit 1
fi

echo "GPU detected:"
nvidia-smi -L

if ! command -v nvcc >/dev/null; then
    echo ""
    echo "INFO: nvcc not in PATH."
    echo "Not strictly required — CuPy uses NVRTC (bundled with driver) to JIT kernels."
    echo "If install fails, install CUDA Toolkit:"
    echo "  wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb"
    echo "  sudo dpkg -i cuda-keyring_1.1-1_all.deb"
    echo "  sudo apt update && sudo apt install -y cuda-toolkit-12-6"
    echo ""
    echo "Continuing install (pip wheels)..."
    echo ""
fi

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo ""
echo "Installed. Run: python3 pfft_miner.py"
