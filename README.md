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

## Requirements (Windows)

1. **NVIDIA GPU** with CUDA compute capability 3.5+ (anything RTX 20/30/40 works)
2. **Python 3.10+** — https://python.org (check "Add to PATH" during install)
3. **CUDA Toolkit 12.x** — https://developer.nvidia.com/cuda-downloads
4. **Visual Studio Build Tools** (MSVC compiler — required by CUDA/CuPy)
   - https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - Install workload: "Desktop development with C++"

Verify install:
```cmd
nvcc --version
python --version
```

## Setup

```cmd
git clone https://github.com/<your-user>/pfft-miner-cuda.git
cd pfft-miner-cuda

install.bat
```

Or manually:
```cmd
pip install -r requirements.txt
```

## Run

```cmd
python pfft_miner.py
```

Or double-click `run.bat`.

First run auto-generates `wallet.json` with a fresh Ethereum wallet. Fund it with ~0.001 ETH (enough for ~50 mints) and run again.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ETH_RPC` | `https://ethereum-rpc.publicnode.com` | Ethereum RPC endpoint |
| `PFFT_WALLET` | `./wallet.json` | Wallet JSON path |
| `PFFT_GPU` | `1` | Set `0` to force CPU fallback |
| `PFFT_GPU_BATCH` | `16777216` | GPU batch size (2^24). Raise to `33554432` on 3080+ |

Set via `set` before launch, or create `.env`:
```cmd
set PFFT_GPU_BATCH=33554432
python pfft_miner.py
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

**`nvcc fatal: Cannot find compiler 'cl.exe'`**
→ Install Visual Studio Build Tools with C++ workload. Open "x64 Native Tools Command Prompt for VS" and run from there.

**`CUDA driver version is insufficient`**
→ Update NVIDIA driver. CUDA 12.x needs driver 525+.

**`ModuleNotFoundError: No module named 'cupy'`**
→ Run `pip install cupy-cuda12x`. If you have CUDA 11, use `cupy-cuda11x` instead.

**GPU utilization low (<80%)**
→ Raise `PFFT_GPU_BATCH`. Also close other GPU workloads (games, browsers with hardware accel).

**`ValueError: Insufficient ETH for gas`**
→ Wallet needs ~0.00005 ETH per mint. Send ETH to the address printed on startup.

## License

MIT
