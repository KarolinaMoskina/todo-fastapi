import base64
import hashlib
import hmac
import json
import os
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
KEYS_DIR = Path(os.getenv("KEYS_DIR", BASE_DIR / "keys"))

PRIV_KEY = KEYS_DIR / "ec_private_key.pem"
PUB_KEY = KEYS_DIR / "ec_public_key.pem"
FALLBACK_SECRET = KEYS_DIR / "fallback_hmac.key"

CURVE = "secp521r1"
DIGEST = "sha3-512"


def build_task_payload(
    task_or_title: Any,
    description: str | None = None,
    completed: bool | None = None,
) -> str:
    if description is None and completed is None and not isinstance(task_or_title, str):
        title = getattr(task_or_title, "title", None)
        desc = getattr(task_or_title, "description", None)
        comp = bool(getattr(task_or_title, "completed", False))
    else:
        title = task_or_title
        desc = description
        comp = bool(completed)

    data = {
        "title": title,
        "description": desc,
        "completed": comp,
    }
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _find_openssl() -> str | None:
    found = shutil.which("openssl")
    if found:
        return found

    candidates = [
        Path(r"C:\Program Files\Git\usr\bin\openssl.exe"),
        Path(r"C:\Program Files\OpenSSL-Win64\bin\openssl.exe"),
        Path(r"C:\Program Files (x86)\OpenSSL-Win64\bin\openssl.exe"),
        Path(r"C:\OpenSSL-Win64\bin\openssl.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def _get_fallback_secret() -> bytes:
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    if not FALLBACK_SECRET.exists():
        FALLBACK_SECRET.write_bytes(secrets.token_bytes(64))
    return FALLBACK_SECRET.read_bytes()


def ensure_keys() -> None:
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    openssl_bin = _find_openssl()
    if openssl_bin and (not PRIV_KEY.exists() or not PUB_KEY.exists()):
        subprocess.run(
            [openssl_bin, "ecparam", "-name", CURVE, "-genkey", "-noout", "-out", str(PRIV_KEY)],
            check=True,
        )
        subprocess.run(
            [openssl_bin, "ec", "-in", str(PRIV_KEY), "-pubout", "-out", str(PUB_KEY)],
            check=True,
        )
        return

    if not openssl_bin:
        _get_fallback_secret()


def sign_payload(payload: str) -> str:
    ensure_keys()
    data_bytes = payload.encode("utf-8")
    openssl_bin = _find_openssl()

    if openssl_bin and PRIV_KEY.exists():
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            data_file = tmp_path / "payload.bin"
            sig_file = tmp_path / "payload.sig"
            data_file.write_bytes(data_bytes)

            subprocess.run(
                [
                    openssl_bin,
                    "pkeyutl",
                    "-sign",
                    "-inkey",
                    str(PRIV_KEY),
                    "-rawin",
                    "-digest",
                    DIGEST,
                    "-in",
                    str(data_file),
                    "-out",
                    str(sig_file),
                ],
                check=True,
            )
            return base64.b64encode(sig_file.read_bytes()).decode("ascii")

    secret = _get_fallback_secret()
    mac = hmac.new(secret, data_bytes, hashlib.sha3_512).digest()
    return base64.b64encode(mac).decode("ascii")


def verify_payload(payload: str, signature_b64: str | None) -> bool:
    if not signature_b64:
        return False

    try:
        sig_bytes = base64.b64decode(signature_b64.encode("ascii"), validate=True)
    except Exception:
        return False

    data_bytes = payload.encode("utf-8")
    openssl_bin = _find_openssl()

    if openssl_bin and PUB_KEY.exists():
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            data_file = tmp_path / "payload.bin"
            sig_file = tmp_path / "payload.sig"
            data_file.write_bytes(data_bytes)
            sig_file.write_bytes(sig_bytes)

            result = subprocess.run(
                [
                    openssl_bin,
                    "pkeyutl",
                    "-verify",
                    "-pubin",
                    "-inkey",
                    str(PUB_KEY),
                    "-rawin",
                    "-digest",
                    DIGEST,
                    "-in",
                    str(data_file),
                    "-sigfile",
                    str(sig_file),
                ],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0

    if not FALLBACK_SECRET.exists():
        return False

    expected = hmac.new(_get_fallback_secret(), data_bytes, hashlib.sha3_512).digest()
    return hmac.compare_digest(expected, sig_bytes)