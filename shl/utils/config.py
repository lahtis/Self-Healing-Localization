"""
File: config.py - Load config.json
Author: Tuomas Lähteenmäki
Version: 0.4.0
License: MIT
Description:
    Reads SHL's shared config from ~/.config/shl/config.json.
"""
import json
import os

CONFIG_DIR = os.path.expanduser("~/.config/shl")
os.makedirs(CONFIG_DIR, exist_ok=True)

CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


def get_config_value(key: str, default=None):
    if not os.path.exists(CONFIG_PATH):
        return default

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(key, default)
    except Exception:
        return default
