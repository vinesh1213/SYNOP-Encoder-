import os
import json
from typing import Dict, Any

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'synop-config.json')

def load_config() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_PATH):
        create_default_config()
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(config_data: Dict[str, Any]) -> None:
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config_data, f, indent=4)

def create_default_config() -> None:
    default_config = {
        "general": {
            "theme": "dark",
            "colors": {"primary": "#4facfe", "secondary": "#00f2fe"}
        },
        "station": {
            "default_station": "43279",
            "filter_active_only": True
        },
        "units": {
            "wind_unit": "knots",
            "show_section_333": True
        },
        "auto_decoder": {
            "enabled": True,
            "interval_seconds": 60,
            "input_folder": "./incoming_synops",
            "output_folder": "./decoded_synops"
        },
        "storage": {
            "file_naming_format": "{station}_{YYYYMMDD}_{HH}.txt"
        }
    }
    save_config(default_config)

