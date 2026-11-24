import base64
import os
import subprocess
import tempfile
from pathlib import Path

KEYS_DIR = Path(os.getenv("OPENSSL_KEYS_DIR", "/app/keys"))
PRIV_KEY = KEYS_DIR / "ec_keypair.pem"
PUB_KEY = KEYS_DIR / "ec_public_key.pem"


def build_task_payload(title: str, description: str | None, completed: bool) -> str:
    desc = description if description is not None else ""
    flag = "1" if completed else "0"
    return f"{title}|{desc}|{flag}"


def ensure_keys() -> None:
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    if not PRIV_KEY.exists():
        subprocess.run(
            [
                "openssl", "genpkey",
                "-algorithm", "EC",
                "-pkeyopt", "ec_paramgen_curve:secp521r1",
                "-out", str(PRIV_KEY),
            ],
            check=True,
        )
    if not PUB_KEY.exists():
        subprocess.run(
            [
                "openssl", "pkey",
                "-in", str(PRIV_KEY),
                "-pubout",
                "-out", str(PUB_KEY),
            ],
            check=True,
        )


def sign_payload(payload: str) -> str:
    ensure_keys()
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as data_f:
        data_f.write(payload)
        data_path = data_f.name
    sig_path = data_path + ".sig"
    try:
        subprocess.run(
            [
                "openssl", "pkeyutl",
                "-sign", "-digest", "sha3-512",
                "-inkey", str(PRIV_KEY),
                "-in", data_path,
                "-rawin",
                "-out", sig_path,
            ],
            check=True,
        )
        sig_bytes = Path(sig_path).read_bytes()
        return base64.b64encode(sig_bytes).decode("ascii")
    finally:
        for p in (data_path, sig_path):
            if os.path.exists(p):
                os.remove(p)


def verify_payload(payload: str, signature_b64: str | None) -> bool:
    if not signature_b64 or not PUB_KEY.exists():
        return False
    try:
        sig_bytes = base64.b64decode(signature_b64.encode("ascii"))
    except Exception:
        return False

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as data_f:
        data_f.write(payload)
        data_path = data_f.name
    with tempfile.NamedTemporaryFile("wb", delete=False) as sig_f:
        sig_f.write(sig_bytes)
        sig_path = sig_f.name

    try:
        res = subprocess.run(
            [
                "openssl", "pkeyutl",
                "-verify", "-digest", "sha3-512",
                "-pubin", "-inkey", str(PUB_KEY),
                "-in", data_path,
                "-rawin",
                "-sigfile", sig_path,
            ],
            capture_output=True,
            text=True,
        )
        return res.returncode == 0
    finally:
        for p in (data_path, sig_path):
            if os.path.exists(p):
                os.remove(p)