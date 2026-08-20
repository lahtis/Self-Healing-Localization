"""
File: config.py - Load config.json
Author: Tuomas Lähteenmäki
Version: 0.2.4
License: MIT
Description:
    
"""
import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def get_config_value(key: str, default=None):
    if not os.path.exists(CONFIG_PATH):
        return default

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(key, default)
    except Exception:
        return default

