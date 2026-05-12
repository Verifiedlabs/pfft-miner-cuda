#!/usr/bin/env python3
"""
PFFT Miner Bot — Pow Free Fair Token
Ethereum Mainnet | Contract: 0xEFAd2Eab7172dDEbE5Ce7a41f5Ddf8fCcE4Ca0CB

Usage:
  python3 pfft_miner.py                    # Run with default wallet
  PFFT_WALLET=/path/to/wallet.json python3 pfft_miner.py
  ETH_RPC=https://... python3 pfft_miner.py
"""

import os
import sys
import json
import time
import struct
import signal
from pathlib import Path

# Load .env file if present (no external dependency)
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CONTRACT = "0xEFAd2Eab7172dDEbE5Ce7a41f5Ddf8fCcE4Ca0CB"
CHAIN_ID = 1
RPC = os.environ.get("ETH_RPC", "https://ethereum-rpc.publicnode.com")
WALLET_FILE = os.environ.get("PFFT_WALLET", os.path.join(os.path.dirname(os.path.abspath(__file__)), "wallet.json"))
GAS_LIMIT = 200000
PAUSE_BETWEEN_ROUNDS = 5
USE_GPU = os.environ.get("PFFT_GPU", "1") not in ("0", "false", "False", "")
GPU_BATCH = int(os.environ.get("PFFT_GPU_BATCH", 1 << 22))
GPU_IDS = os.environ.get("PFFT_GPU_IDS", "")
AUTO_CREATE_WALLETS = int(os.environ.get("PFFT_AUTO_CREATE_WALLETS", 1))
MIN_ETH_FOR_MINT = 0.00005
WALLET_CAP_PFFT = 10_000

# ---------------------------------------------------------------------------
# Keccak256 (fast, using pycryptodome C extension)
# ---------------------------------------------------------------------------
from Crypto.Hash import keccak as _keccak_mod

def keccak256(data: bytes) -> bytes:
    return _keccak_mod.new(digest_bits=256, data=data).digest()

# ---------------------------------------------------------------------------
# PoW Solver (optimized — pre-compute challenge prefix, pack nonce as bytes)
# ---------------------------------------------------------------------------
def solve_pow(challenge: bytes, target: int, max_hashrate_window: float = 5.0) -> tuple:
    """
    Brute-force PoW. Returns (nonce, hash_bytes) or (None, None).
    """
    nonce = 0
    start = time.time()
    last_report = start
    # Pre-allocate: challenge (32 bytes) + nonce (32 bytes) = 64 bytes
    buf = bytearray(challenge) + bytearray(32)
    challenge_prefix = bytes(buf[:32])

    while running:
        # Pack nonce into last 32 bytes (big-endian)
        struct.pack_into('>QQQQ', buf, 32, 0, 0, 0, nonce)
        h = keccak256(bytes(buf))
        h_int = int.from_bytes(h, 'big')

        if h_int <= target:
            elapsed = time.time() - start
            rate = nonce / elapsed if elapsed > 0 else 0
            print(f"\n  ✅ FOUND nonce={nonce} | {nonce} attempts | {elapsed:.1f}s | {rate:,.0f} H/s")
            return nonce, h

        nonce += 1
        now = time.time()
        if now - last_report >= max_hashrate_window:
            elapsed = now - start
            rate = nonce / elapsed
            remaining = (target.bit_length() and (2**28 / rate)) or 0  # rough ETA
            print(f"  ⛏️  {nonce:,} attempts | {rate:,.0f} H/s | {elapsed:.0f}s elapsed", end='\r')
            last_report = now

    print(f"\n  ⚠️  Mining aborted at nonce={nonce:,}")
    return None, None


# ---------------------------------------------------------------------------
# Contract interaction
# ---------------------------------------------------------------------------
def load_contract(w3):
    ABI = [
        {"inputs":[],"name":"currentPowHexZeros","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[],"name":"totalMinted","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[],"name":"MAX_SUPPLY","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"name":"requested","type":"uint256"}],"name":"calculateActualMint","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"name":"user","type":"address"}],"name":"currentPowChallenge","outputs":[{"type":"bytes32"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"name":"user","type":"address"},{"name":"powNonce","type":"uint256"}],"name":"isValidPow","outputs":[{"type":"bool"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"name":"powNonce","type":"uint256"}],"name":"freeMint","outputs":[],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[{"name":"user","type":"address"}],"name":"mintedByAddress","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[],"name":"getInfo","outputs":[{"type":"uint256"},{"type":"uint256"},{"type":"uint256"},{"type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[],"name":"balanceOf","outputs":[{"type":"uint256"}],"inputs":[{"name":"account","type":"address"}],"stateMutability":"view","type":"function"},
    ]
    # Fix: balanceOf needs proper format
    ABI_CORRECT = []
    for item in ABI:
        fixed = {"type": item["type"], "name": item["name"], "stateMutability": item.get("stateMutability","view")}
        if "inputs" in item:
            fixed["inputs"] = item["inputs"]
        if "outputs" in item:
            fixed["outputs"] = item["outputs"]
        ABI_CORRECT.append(fixed)
    # Add balanceOf properly
    ABI_CORRECT = [x for x in ABI_CORRECT if x["name"] != "balanceOf"]
    ABI_CORRECT.append({
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    })
    return w3.eth.contract(address=w3.to_checksum_address(CONTRACT), abi=ABI_CORRECT)


def get_status(contract, wallet_addr):
    """Get current contract + wallet status."""
    hex_zeros = contract.functions.currentPowHexZeros().call()
    total_minted = contract.functions.totalMinted().call()
    max_supply = contract.functions.MAX_SUPPLY().call()
    next_mint = contract.functions.calculateActualMint(w3.to_wei(1000, 'ether')).call()
    wallet_minted = contract.functions.mintedByAddress(wallet_addr).call()
    wallet_bal = contract.functions.balanceOf(wallet_addr).call()
    target = (2**256 - 1) >> (hex_zeros * 4)
    progress = total_minted * 10000 / max_supply / 100

    return {
        "hex_zeros": hex_zeros,
        "difficulty_bits": hex_zeros * 4,
        "total_minted": total_minted,
        "max_supply": max_supply,
        "next_mint": next_mint,
        "wallet_minted": wallet_minted,
        "wallet_bal": wallet_bal,
        "target": target,
        "progress": progress,
    }


def get_challenge(contract, wallet_addr):
    """Get current PoW challenge for wallet."""
    c = contract.functions.currentPowChallenge(wallet_addr).call()
    return c if isinstance(c, bytes) else c.to_bytes(32, 'big')


def submit_mint(w3, wallet, contract, nonce: int) -> bool:
    """Submit freeMint tx."""
    try:
        fn = contract.functions.freeMint(nonce)
        tx = fn.build_transaction({
            'from': wallet.address,
            'nonce': w3.eth.get_transaction_count(wallet.address),
            'chainId': CHAIN_ID,
            'gas': GAS_LIMIT,
        })
        if 'maxFeePerGas' not in tx and 'maxPriorityFeePerGas' not in tx:
            tx['gasPrice'] = w3.eth.gas_price

        signed = wallet.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"  📤 TX: https://etherscan.io/tx/0x{tx_hash.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        if receipt.status == 1:
            print(f"  ✅ MINT OK | Block {receipt.blockNumber} | Gas {receipt.gasUsed}")
            return True
        else:
            print(f"  ❌ REVERTED | Gas {receipt.gasUsed}")
            return False
    except Exception as e:
        print(f"  ❌ TX error: {e}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
running = True
def handle_signal(sig, frame):
    global running
    print("\n  ⚠️  Stopping miner...")
    running = False

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


def _setup_cuda_libs():
    import os
    import ctypes
    import glob
    try:
        import importlib.util
        spec = importlib.util.find_spec("nvidia.cuda_nvrtc")
        if not spec or not spec.submodule_search_locations:
            return
        lib_dir = os.path.join(spec.submodule_search_locations[0], "lib")
        if not os.path.isdir(lib_dir):
            return

        existing = os.environ.get("LD_LIBRARY_PATH", "")
        if lib_dir not in existing.split(":"):
            os.environ["LD_LIBRARY_PATH"] = f"{lib_dir}:{existing}" if existing else lib_dir

        for pattern in ("libnvrtc-builtins.so*", "libnvrtc.so*"):
            for f in sorted(glob.glob(os.path.join(lib_dir, pattern)), reverse=True):
                try:
                    ctypes.CDLL(f, mode=ctypes.RTLD_GLOBAL)
                    break
                except OSError:
                    continue
    except Exception:
        pass


def _worker_mine(gpu_id: int, wallet_keys: list, gpu_batch: int, use_gpu: bool, log_prefix: str):
    import signal as _signal
    _setup_cuda_libs()
    from web3 import Web3
    from eth_account import Account
    from wallets import Wallet, WalletPool

    worker_running = {"v": True}

    def _stop(sig, frame):
        worker_running["v"] = False

    _signal.signal(_signal.SIGINT, _stop)
    _signal.signal(_signal.SIGTERM, _stop)

    w3_local = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": 30}))
    globals()["w3"] = w3_local
    contract = load_contract(w3_local)

    wallets_obj = [Wallet(Account.from_key(k), source=f"worker-{gpu_id}") for k in wallet_keys]
    pool = WalletPool(wallets_obj)

    gpu = None
    if use_gpu:
        try:
            from gpu_solver import GPUSolver
            gpu = GPUSolver(batch_size=gpu_batch, device_id=gpu_id)
            print(f"{log_prefix} GPU #{gpu_id} ({gpu.gpu_name}) ready, batch={gpu_batch:,}")
        except Exception as e:
            print(f"{log_prefix} GPU #{gpu_id} init failed: {e}")
            return

    round_num = 0
    mints = 0
    pfft_total = 0.0
    start = time.time()

    while worker_running["v"]:
        round_num += 1
        wo = pool.next_available()
        if wo is None:
            if not pool.available():
                print(f"{log_prefix} All wallets exhausted, worker done.")
                break
            time.sleep(5)
            continue

        wallet = wo.account
        try:
            s = get_status(contract, wallet.address)
            if s['total_minted'] >= s['max_supply']:
                print(f"{log_prefix} Max supply reached.")
                break
            if s['wallet_minted'] >= WALLET_CAP_PFFT * 1e18:
                print(f"{log_prefix} {wallet.address[:10]}... capped.")
                wo.skip(10**9, "capped")
                continue
            eth_bal = w3_local.eth.get_balance(wallet.address) / 1e18
            if eth_bal < MIN_ETH_FOR_MINT:
                print(f"{log_prefix} {wallet.address[:10]}... low ETH ({eth_bal:.6f}), skip 5min")
                wo.skip(300, "no_eth")
                continue
        except Exception as e:
            print(f"{log_prefix} Status error: {e}")
            time.sleep(15)
            continue

        print(f"{log_prefix} Round #{round_num} | {wallet.address[:10]}... | {s['difficulty_bits']}-bit")
        challenge = get_challenge(contract, wallet.address)

        if gpu is not None:
            nonce, _ = gpu.solve(challenge, s['target'], lambda: worker_running["v"])
        else:
            nonce, _ = solve_pow(challenge, s['target'])

        if nonce is None:
            continue

        try:
            if not contract.functions.isValidPow(wallet.address, nonce).call():
                print(f"{log_prefix} Nonce stale, re-mining...")
                continue
        except Exception:
            pass

        if submit_mint(w3_local, wallet, contract, nonce):
            mints += 1
            earned = s['next_mint'] / 1e18
            pfft_total += earned
            wo.mints_this_session += 1
            wo.pfft_earned += earned
            print(f"{log_prefix} +{earned:,.2f} PFFT (worker total: {pfft_total:,.2f}, {mints} mints)")

        if worker_running["v"]:
            time.sleep(PAUSE_BETWEEN_ROUNDS)

    elapsed = time.time() - start
    print(f"{log_prefix} DONE: {mints} mints, {pfft_total:,.2f} PFFT in {elapsed/60:.1f} min")


def _coop_gpu_worker(gpu_id: int, gpu_batch: int, cmd_q, result_q, log_prefix: str):
    import signal as _signal
    _setup_cuda_libs()
    _signal.signal(_signal.SIGINT, _signal.SIG_IGN)

    try:
        from gpu_solver import GPUSolver
        gpu = GPUSolver(batch_size=gpu_batch, device_id=gpu_id)
        print(f"{log_prefix} ready ({gpu.gpu_name})", flush=True)
    except Exception as e:
        print(f"{log_prefix} init failed: {e}", flush=True)
        result_q.put(("init_fail", gpu_id, str(e)))
        return

    while True:
        cmd = cmd_q.get()
        if cmd is None or cmd[0] == "stop":
            return

        if cmd[0] == "solve":
            _, job_id, challenge, target, nonce_base, stop_event = cmd
            start = time.time()

            def should_stop():
                return stop_event.is_set()

            nonce, hashes = gpu.solve_range(challenge, target, nonce_base, should_stop)
            elapsed = time.time() - start
            if nonce is not None:
                result_q.put(("found", job_id, gpu_id, nonce, hashes, elapsed))
            else:
                result_q.put(("done", job_id, gpu_id, hashes, elapsed))


def _run_cooperative(gpu_ids, wallet_keys, gpu_batch):
    import multiprocessing as mp
    from web3 import Web3
    from eth_account import Account
    from wallets import Wallet, WalletPool

    w3_local = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": 30}))
    globals()["w3"] = w3_local
    contract = load_contract(w3_local)

    wallets_obj = [Wallet(Account.from_key(k), source=f"coop-{i}") for i, k in enumerate(wallet_keys)]
    pool = WalletPool(wallets_obj)

    ctx = mp.get_context("spawn")
    cmd_qs = [ctx.Queue() for _ in gpu_ids]
    result_q = ctx.Queue()
    stop_events = [ctx.Event() for _ in gpu_ids]

    procs = []
    for i, gid in enumerate(gpu_ids):
        prefix = f"[GPU#{gid}]"
        p = ctx.Process(target=_coop_gpu_worker, args=(gid, gpu_batch, cmd_qs[i], result_q, prefix), daemon=False)
        p.start()
        procs.append(p)

    print(f"🤝 Cooperative mode: {len(gpu_ids)} GPUs on 1 wallet per round", flush=True)

    import random
    coordinator_running = {"v": True}

    def _stop(sig, frame):
        coordinator_running["v"] = False
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    round_num = 0
    mints = 0
    pfft_total = 0.0
    start_session = time.time()

    try:
        while coordinator_running["v"]:
            round_num += 1
            wo = pool.next_available()
            if wo is None:
                if not pool.available():
                    print("All wallets exhausted. Stopping.")
                    break
                time.sleep(5)
                continue

            wallet = wo.account
            try:
                s = get_status(contract, wallet.address)
                if s['total_minted'] >= s['max_supply']:
                    print("Max supply reached.")
                    break
                if s['wallet_minted'] >= WALLET_CAP_PFFT * 1e18:
                    print(f"Wallet {wallet.address[:10]}... capped.")
                    wo.skip(10**9, "capped")
                    continue
                eth_bal = w3_local.eth.get_balance(wallet.address) / 1e18
                if eth_bal < MIN_ETH_FOR_MINT:
                    print(f"{wallet.address[:10]}... low ETH ({eth_bal:.6f}), skip 5min")
                    wo.skip(300, "no_eth")
                    continue
            except Exception as e:
                print(f"Status error: {e}")
                time.sleep(15)
                continue

            challenge = get_challenge(contract, wallet.address)
            print(f"\n🎯 Round #{round_num} | wallet {wallet.address[:10]}... | {s['difficulty_bits']}-bit | ALL {len(gpu_ids)} GPUs")

            stride = 1 << 56
            base = random.randint(0, (1 << 63) - 1)

            for ev in stop_events:
                ev.clear()

            job_id = round_num
            for i, gid in enumerate(gpu_ids):
                nb = (base + i * stride) & ((1 << 64) - 1)
                cmd_qs[i].put(("solve", job_id, challenge, s['target'], nb, stop_events[i]))

            found_nonce = None
            winner_gpu = None
            finished = 0
            t_start = time.time()
            last_report = t_start

            while finished < len(gpu_ids):
                try:
                    msg = result_q.get(timeout=2.0)
                except Exception:
                    now = time.time()
                    if now - last_report >= 3.0:
                        print(f"  ⏳ mining... {now - t_start:.0f}s", end="\r", flush=True)
                        last_report = now
                    continue

                kind = msg[0]
                if kind == "found" and msg[1] == job_id and found_nonce is None:
                    _, _, winner_gpu, nonce, hashes, el = msg
                    found_nonce = nonce
                    print(f"\n  ✅ GPU#{winner_gpu} found nonce={nonce} in {el:.1f}s ({hashes:,} hashes)")
                    for ev in stop_events:
                        ev.set()
                elif kind == "done" and msg[1] == job_id:
                    finished += 1
                elif kind == "found" and msg[1] == job_id:
                    finished += 1

            if found_nonce is None:
                print("  ⚠️  No nonce found this round (aborted?)")
                continue

            try:
                if not contract.functions.isValidPow(wallet.address, found_nonce).call():
                    print("  ⚠️  Nonce stale, retrying round")
                    continue
            except Exception:
                pass

            if submit_mint(w3_local, wallet, contract, found_nonce):
                mints += 1
                earned = s['next_mint'] / 1e18
                pfft_total += earned
                wo.mints_this_session += 1
                wo.pfft_earned += earned
                print(f"  💰 +{earned:,.2f} PFFT | Session total: {pfft_total:,.2f} ({mints} mints)")

            if coordinator_running["v"]:
                time.sleep(PAUSE_BETWEEN_ROUNDS)
    finally:
        for q in cmd_qs:
            q.put(("stop",))
        for p in procs:
            p.join(timeout=5)
        for p in procs:
            if p.is_alive():
                p.terminate()

    elapsed = time.time() - start_session
    print(f"\n{'='*60}")
    print(f"  Cooperative session done: {mints} mints, {pfft_total:,.2f} PFFT in {elapsed/60:.1f} min")
    print(f"{'='*60}")


def _detect_gpus():
    import subprocess
    try:
        out = subprocess.check_output(["nvidia-smi", "-L"], text=True, timeout=10)
    except Exception as e:
        print(f"⚠️  nvidia-smi failed: {e}")
        return [], []

    ids = []
    names = []
    for line in out.strip().splitlines():
        line = line.strip()
        if not line.startswith("GPU "):
            continue
        try:
            head, rest = line.split(":", 1)
            idx = int(head.replace("GPU", "").strip())
            name = rest.split("(UUID:")[0].strip()
            ids.append(idx)
            names.append(name)
        except Exception:
            continue
    return ids, names


def main():
    import multiprocessing as mp
    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    from web3 import Web3
    from eth_account import Account

    print("=" * 60)
    print("  ⛏️  PFFT Miner Bot — Pow Free Fair Token")
    print(f"  Contract: {CONTRACT}")
    print(f"  RPC: {RPC}")
    print("=" * 60)

    if GPU_IDS.strip():
        gpu_ids = [int(x.strip()) for x in GPU_IDS.split(",") if x.strip()]
        gpu_names = [f"#{i}" for i in gpu_ids]
        print(f"🎯 Using GPUs: {gpu_ids} (from PFFT_GPU_IDS)")
    elif USE_GPU:
        gpu_ids, gpu_names = _detect_gpus()
        if gpu_ids:
            print(f"🎯 Auto-detected {len(gpu_ids)} GPU(s):")
            for i, n in zip(gpu_ids, gpu_names):
                print(f"   [{i}] {n}")
        else:
            print("⚠️  No CUDA GPUs found, will run CPU-only worker.")
    else:
        gpu_ids, gpu_names = [], []
        print("ℹ️  GPU disabled (PFFT_GPU=0), using CPU")

    w3_main = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": 30}))
    if not w3_main.is_connected():
        print("❌ Cannot connect to RPC")
        sys.exit(1)
    print(f"✅ Connected | Block #{w3_main.eth.block_number}")

    from wallets import load_wallets
    pool = load_wallets(Account, WALLET_FILE, auto_create_count=AUTO_CREATE_WALLETS)
    print(f"\n👛 Loaded {len(pool)} wallet(s):")
    for w in pool.wallets:
        eth_bal = w3_main.eth.get_balance(w.address) / 1e18
        marker = "⚠️ " if eth_bal < MIN_ETH_FOR_MINT else "  "
        print(f"   {marker}{w.address}  ETH: {eth_bal:.6f}")

    globals()["w3"] = w3_main
    contract = load_contract(w3_main)
    head = pool.wallets[0]
    s = get_status(contract, head.address)
    print(f"\n📊 Contract:")
    print(f"   Minted: {s['total_minted']/1e18:,.0f} / {s['max_supply']/1e18:,.0f} PFFT ({s['progress']:.1f}%)")
    print(f"   Next mint: ~{s['next_mint']/1e18:,.2f} PFFT")
    print(f"   Difficulty: {s['hex_zeros']} hex zeros ({s['difficulty_bits']}-bit)")

    num_gpus = len(gpu_ids) if gpu_ids else 0
    num_wallets = len(pool)
    all_keys = ["0x" + w.account.key.hex() if not w.account.key.hex().startswith("0x") else w.account.key.hex()
                for w in pool.wallets]

    if num_gpus > 0 and num_wallets < num_gpus:
        print(f"\n🤝 Cooperative mode: {num_wallets} wallet(s) < {num_gpus} GPUs")
        print(f"   All GPUs will mine the same challenge in parallel (first-to-find wins)")
        _run_cooperative(gpu_ids, all_keys, GPU_BATCH)
        return

    num_workers = num_gpus if num_gpus else 1
    buckets = [[] for _ in range(num_workers)]
    for idx, k in enumerate(all_keys):
        buckets[idx % num_workers].append(k)

    print(f"\n🔧 Parallel mode: spawning {num_workers} worker process(es):")
    for i, b in enumerate(buckets):
        gid = gpu_ids[i] if gpu_ids else -1
        tag = f"GPU#{gid}" if gid >= 0 else "CPU"
        print(f"   Worker {i} [{tag}]: {len(b)} wallet(s)")

    procs = []
    for i in range(num_workers):
        gid = gpu_ids[i] if gpu_ids else -1
        prefix = f"[GPU#{gid}]" if gid >= 0 else "[CPU]"
        use_gpu_flag = USE_GPU and gid >= 0
        p = mp.Process(
            target=_worker_mine,
            args=(max(gid, 0), buckets[i], GPU_BATCH, use_gpu_flag, prefix),
            daemon=False,
        )
        p.start()
        procs.append(p)

    global_start = time.time()
    try:
        for p in procs:
            p.join()
    except KeyboardInterrupt:
        print("\n⚠️  Stopping all workers...")
        for p in procs:
            if p.is_alive():
                p.terminate()
        for p in procs:
            p.join(timeout=10)

    print(f"\n{'='*60}")
    print(f"  Session done in {(time.time()-global_start)/60:.1f} min")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
