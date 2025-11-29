import json
import os

class ConfigManager:
    def __init__(self, filename="settings.json"):
        self.filename = filename
        self.defaults = {
            "machine_size_x": 300.0,
            "machine_size_y": 200.0,
            "machine_size_z": 100.0,
            "rapid_feed": 3000.0,
            "default_tool_dia": 10.0,
            "theme": "dark",
            # NOVO: Biblioteka alata (T broj : Precnik)
            "tool_library": {
                "1": 10.0,
                "2": 5.0,
                "3": 2.0,
                "4": 20.0
            }
        }

    def load_config(self):
        if not os.path.exists(self.filename):
            return self.defaults.copy()
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
                config = self.defaults.copy()
                config.update(data)
                # Osiguraj da tool_library postoji (za stare korisnike)
                if "tool_library" not in config:
                    config["tool_library"] = self.defaults["tool_library"]
                return config
        except:
            return self.defaults.copy()

    def save_config(self, config_data):
        try:
            with open(self.filename, 'w') as f:
                json.dump(config_data, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")