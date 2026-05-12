import os
import json
import time
from pathlib import Path
from typing import List, Optional


class Wallet:
    def __init__(self, account, source: str):
        self.account = account
        self.address = account.address
        self.source = source
        self.mints_this_session = 0
        self.pfft_earned = 0.0
        self.skip_until = 0.0
        self.skip_reason = ""

    def is_available(self) -> bool:
        return time.time() >= self.skip_until

    def skip(self, seconds: float, reason: str):
        self.skip_until = time.time() + seconds
        self.skip_reason = reason


class WalletPool:
    def __init__(self, wallets: List[Wallet]):
        self.wallets = wallets
        self._cursor = 0

    def __len__(self):
        return len(self.wallets)

    def available(self) -> List[Wallet]:
        return [w for w in self.wallets if w.is_available()]

    def next_available(self) -> Optional[Wallet]:
        n = len(self.wallets)
        if n == 0:
            return None
        for _ in range(n):
            w = self.wallets[self._cursor % n]
            self._cursor += 1
            if w.is_available():
                return w
        return None


def _load_single_wallet_file(Account, path: Path) -> Wallet:
    with open(path) as f:
        data = json.load(f)
    pk = data.get("private_key_hex") or data.get("private_key")
    if not pk.startswith("0x"):
        pk = "0x" + pk
    return Wallet(Account.from_key(pk), source=str(path))


def _save_wallet_json(wallet, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "address": wallet.address,
        "private_key_hex": wallet.key.hex(),
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": "PFFT miner wallet — KEEP SECRET",
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load_wallets(Account, default_path: str, wallets_dir_env: str = "PFFT_WALLETS_DIR",
                 auto_create_count: int = 1) -> WalletPool:
    dir_path = os.environ.get(wallets_dir_env)
    wallets: List[Wallet] = []

    if dir_path:
        d = Path(dir_path)
        d.mkdir(parents=True, exist_ok=True)
        files = sorted(d.glob("*.json"))
        for f in files:
            try:
                wallets.append(_load_single_wallet_file(Account, f))
            except Exception as e:
                print(f"  ⚠️  Skip {f.name}: {e}")

        if not wallets:
            print(f"  No wallets in {d}, creating {auto_create_count}...")
            for i in range(auto_create_count):
                acc = Account.create()
                path = d / f"wallet_{i+1}.json"
                _save_wallet_json(acc, path)
                wallets.append(Wallet(acc, source=str(path)))
                print(f"  ✅ Created: {acc.address} → {path.name}")
        return WalletPool(wallets)

    single_path = Path(default_path)
    if single_path.exists():
        wallets.append(_load_single_wallet_file(Account, single_path))
    else:
        acc = Account.create()
        _save_wallet_json(acc, single_path)
        print(f"  ✅ New wallet: {acc.address} → {single_path}")
        wallets.append(Wallet(acc, source=str(single_path)))

    return WalletPool(wallets)
