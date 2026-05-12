#!/usr/bin/env bash
set -e

if ! command -v python3 >/dev/null; then
    echo "Python not found. Install: sudo apt install python3 python3-pip python3-venv python3-full"
    exit 1
fi

if ! nvidia-smi >/dev/null 2>&1; then
    echo "ERROR: nvidia-smi not working. NVIDIA driver missing."
    echo "Install driver: sudo ubuntu-drivers autoinstall && sudo reboot"
    exit 1
fi

echo "GPU(s) detected:"
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
fi

VENV_DIR="${VENV_DIR:-.venv}"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating venv at $VENV_DIR..."
    if ! python3 -m venv "$VENV_DIR" 2>/dev/null; then
        echo "venv creation failed. Install python3-venv:"
        echo "  sudo apt install -y python3-venv python3-full"
        exit 1
    fi
fi

source "$VENV_DIR/bin/activate"

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo ""
echo "Installed in $VENV_DIR"
echo ""
echo "Run miner:"
echo "  source $VENV_DIR/bin/activate"
echo "  python3 pfft_miner.py"
