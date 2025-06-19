import os
from datetime import datetime


def load_token(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Token file not found at: {path}")
    with open(path, "r") as f:
        return f.read().strip()


def parse_iso(date_str):
    return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ") if date_str else None
