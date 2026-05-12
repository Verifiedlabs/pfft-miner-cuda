# PFFT Miner — CUDA (NVIDIA GPU) Edition

Windows / Linux miner for **Pow Free Fair Token (PFFT)** on Ethereum mainnet, accelerated with NVIDIA CUDA.

Contract: `0xEFAd2Eab7172dDEbE5Ce7a41f5Ddf8fCcE4Ca0CB`

- Max supply: 21,000,000 PFFT
- Per-wallet cap: 10,000 PFFT
- Free mint (0 ETH) — requires Proof-of-Work
- PoW difficulty increases with supply (24→40 bit)

## Performance

| Hardware | Hashrate |
|----------|---------:|
| CPU (Python, single-core) | ~0.5 MH/s |
| RTX 3060 | ~1.5 GH/s |
| RTX 3080 | ~3.0 GH/s |
| RTX 4070 | ~4.0 GH/s |
| RTX 4090 | ~8.0 GH/s |

Numbers are ballpark. Actual depends on clocks, power limit, and batch size.

## Requirements

**Windows:**
1. NVIDIA GPU, compute capability 3.5+ (anything RTX 20/30/40 works)
2. [Python 3.10+](https://python.org) — check "Add to PATH" during install
3. [CUDA Toolkit 12.x](https://developer.nvidia.com/cuda-downloads)
4. [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with "Desktop development with C++" workload

**Ubuntu / Linux:**
1. NVIDIA GPU + NVIDIA driver (`sudo ubuntu-drivers autoinstall`)
2. Python 3.10+ (`sudo apt install python3 python3-pip python3-venv`)
3. CUDA Toolkit 12.x ([official repo instructions](https://developer.nvidia.com/cuda-downloads?target_os=Linux))
4. Build essentials (`sudo apt install build-essential`)

Verify:
```bash
nvidia-smi        # shows GPU
nvcc --version    # shows CUDA 12.x
python3 --version
```

## Setup

### Windows

```cmd
git clone https://github.com/Verifiedlabs/pfft-miner-cuda.git
cd pfft-miner-cuda
install.bat
python pfft_miner.py
```

Or double-click `run.bat`.

### Ubuntu / Linux

```bash
git clone https://github.com/Verifiedlabs/pfft-miner-cuda.git
cd pfft-miner-cuda
chmod +x install.sh
./install.sh
python3 pfft_miner.py
```

First run auto-generates `wallet.json` with a fresh Ethereum wallet. Fund it with ~0.001 ETH (enough for ~50 mints) and run again.

## Multi-wallet support

Run the miner against a pool of wallets — each round rotates to the next wallet. Wallets that run out of ETH or hit the 10,000 PFFT cap are auto-skipped.

### Auto-generate N wallets

```bash
mkdir wallets
PFFT_WALLETS_DIR=./wallets PFFT_AUTO_CREATE_WALLETS=5 python3 pfft_miner.py
```

First run creates `wallets/wallet_1.json` … `wallet_5.json`. Fund each address with ETH, then re-run.

### Import existing wallets

Drop any number of wallet files into the directory:

```
wallets/
├── main.json          # {"private_key_hex": "0xabc..."}
├── alt1.json
└── alt2.json
```

Each file just needs a `private_key_hex` field. The miner picks them all up and rotates.

### Skip rules

| Condition | Action |
|---|---|
| ETH balance < 0.00005 | Skip for 5 min, retry later |
| Wallet minted ≥ 10,000 PFFT | Skip permanently (capped) |
| All wallets skipped | End session |

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ETH_RPC` | `https://ethereum-rpc.publicnode.com` | Ethereum RPC endpoint |
| `PFFT_WALLET` | `./wallet.json` | Single wallet JSON path |
| `PFFT_WALLETS_DIR` | _(unset)_ | **Multi-wallet mode.** Directory containing `*.json` wallet files |
| `PFFT_AUTO_CREATE_WALLETS` | `1` | Auto-create N wallets when `PFFT_WALLETS_DIR` is empty |
| `PFFT_GPU` | `1` | Set `0` to force CPU fallback |
| `PFFT_GPU_BATCH` | `16777216` | GPU batch size (2^24). Raise to `33554432` on 3080+ |

Set via env var before launch, or create `.env`:
```bash
export PFFT_GPU_BATCH=33554432   # Linux
set PFFT_GPU_BATCH=33554432      # Windows cmd
python3 pfft_miner.py
```

## Run as systemd service (Linux)

```bash
sudo cp pfft-miner.service /etc/systemd/system/pfft-miner@$USER.service
sudo systemctl daemon-reload
sudo systemctl enable --now pfft-miner@$USER

sudo journalctl -u pfft-miner@$USER -f
```

## Batch size tuning

Higher batch = better throughput but slower Ctrl+C response.

| GPU tier | Suggested batch |
|---|---|
| GTX 1660 / RTX 3050 | `8388608` (2^23) |
| RTX 3060 / 3070 | `16777216` (2^24) — default |
| RTX 3080 / 4070 | `33554432` (2^25) |
| RTX 3090 / 4080 / 4090 | `67108864` (2^26) |

## Security

- `wallet.json` is **gitignored**. Never commit it.
- Private key is stored in plain JSON locally. Protect your machine.
- First run creates a fresh wallet — no need to import anything.
- Fund only what you need for gas (~0.001 ETH covers dozens of mints).

## Troubleshooting

**Windows: `nvcc fatal: Cannot find compiler 'cl.exe'`**
→ Install Visual Studio Build Tools with C++ workload. Launch from "x64 Native Tools Command Prompt for VS".

**Linux: `nvcc not found`**
→ Add CUDA to PATH in `~/.bashrc`:
```bash
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
```
Then `source ~/.bashrc`.

**`CUDA driver version is insufficient`**
→ Update NVIDIA driver. CUDA 12.x needs driver 525+. On Ubuntu: `sudo ubuntu-drivers autoinstall`.

**`ModuleNotFoundError: No module named 'cupy'`**
→ `pip install cupy-cuda12x`. If you have CUDA 11, use `cupy-cuda11x` instead.

**GPU utilization low (<80%)**
→ Raise `PFFT_GPU_BATCH`. Close other GPU workloads (games, browsers with hardware accel).

**`Insufficient ETH for gas`**
→ Wallet needs ~0.00005 ETH per mint. Send ETH to the address printed on startup.

## License

MIT
