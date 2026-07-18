# ui/core/preset_manager.py
import os
import json


class PresetManager:
    FPS_VALUES = [5.9727, 6.6364, 7.4659, 8.5325, 9.9546, 11.9455, 14.9319]
    ADPCM_NICE_RATES = [6689, 9078, 10512, 11468, 13379, 18157, 20068, 21024, 27236, 31536, 36314, 42048]

    BUILTIN_PRESET_KEYS = [
        "preset_default",
        "preset_balanced",
        "preset_hiq",
        "preset_lofps",
        "preset_fast",
        "preset_noaudio",
    ]

    _BUILTIN_PRESETS = {
        "preset_default": {
            "fps": 9.9546,
            "iframe_interval": 60,
            "diff_threshold": 2.5,
            "variance_threshold": 10.0,
            "color_fallback_threshold": 10.0,
            "force_i_threshold": 0.7,
            "codebook_size": 256,
            "kmeans_iter": 200,
            "iframe_weight": 3,
            "motion_thresh": 6,
            "dither": True,
            "motion": True,
            "audio_format": "PCM",
            "sample_rate": 18157,
            "volume": 100.0,
            "no_audio": False,
            "skip_video_enabled": False,
            "skip_buttons": ["A"],
        },
        "preset_balanced": {
            "fps": 9.9546,
            "iframe_interval": 90,
            "diff_threshold": 3.5,
            "variance_threshold": 12.0,
            "color_fallback_threshold": 12.0,
            "force_i_threshold": 0.65,
            "codebook_size": 192,
            "kmeans_iter": 150,
            "iframe_weight": 3,
            "motion_thresh": 6,
            "dither": True,
            "motion": True,
            "audio_format": "PCM",
            "sample_rate": 18157,
            "volume": 100.0,
            "no_audio": False,
            "skip_video_enabled": False,
            "skip_buttons": ["A"],
        },
        "preset_hiq": {
            "fps": 9.9546,
            "iframe_interval": 45,
            "diff_threshold": 1.5,
            "variance_threshold": 8.0,
            "color_fallback_threshold": 8.0,
            "force_i_threshold": 0.75,
            "codebook_size": 256,
            "kmeans_iter": 400,
            "iframe_weight": 4,
            "motion_thresh": 4,
            "dither": True,
            "motion": True,
            "audio_format": "PCM",
            "sample_rate": 27236,
            "volume": 100.0,
            "no_audio": False,
            "skip_video_enabled": False,
            "skip_buttons": ["A"],
        },
        "preset_lofps": {
            "fps": 5.9727,
            "iframe_interval": 120,
            "diff_threshold": 4.0,
            "variance_threshold": 14.0,
            "color_fallback_threshold": 14.0,
            "force_i_threshold": 0.6,
            "codebook_size": 128,
            "kmeans_iter": 100,
            "iframe_weight": 2,
            "motion_thresh": 8,
            "dither": True,
            "motion": True,
            "audio_format": "ADPCM",
            "sample_rate": 13379,
            "volume": 100.0,
            "no_audio": False,
            "skip_video_enabled": False,
            "skip_buttons": ["A"],
        },
        "preset_fast": {
            "fps": 9.9546,
            "iframe_interval": 120,
            "diff_threshold": 5.0,
            "variance_threshold": 16.0,
            "color_fallback_threshold": 16.0,
            "force_i_threshold": 0.55,
            "codebook_size": 128,
            "kmeans_iter": 50,
            "iframe_weight": 2,
            "motion_thresh": 10,
            "dither": False,
            "motion": False,
            "audio_format": "ADPCM",
            "sample_rate": 13379,
            "volume": 100.0,
            "no_audio": False,
            "skip_video_enabled": False,
            "skip_buttons": ["A"],
        },
        "preset_noaudio": {
            "fps": 14.9319,
            "iframe_interval": 60,
            "diff_threshold": 2.5,
            "variance_threshold": 10.0,
            "color_fallback_threshold": 10.0,
            "force_i_threshold": 0.7,
            "codebook_size": 256,
            "kmeans_iter": 200,
            "iframe_weight": 3,
            "motion_thresh": 6,
            "dither": True,
            "motion": True,
            "audio_format": "PCM",
            "sample_rate": 18157,
            "volume": 100.0,
            "no_audio": True,
            "skip_video_enabled": False,
            "skip_buttons": ["A"],
        },
    }

    def __init__(self, presets_file="presets.json"):
        self.presets_file = presets_file
        self.presets = self.load_presets()

    def get_default_preset(self):
        p = dict(self._BUILTIN_PRESETS["preset_default"])
        p["workers"] = os.cpu_count() or 4
        return p

    def is_builtin(self, key):
        return key in self.BUILTIN_PRESET_KEYS

    def get_builtin_preset(self, key):
        p = dict(self._BUILTIN_PRESETS.get(key, self._BUILTIN_PRESETS["preset_default"]))
        p.setdefault("workers", os.cpu_count() or 4)
        return p

    def load_presets(self):
        user_presets = {}
        if os.path.exists(self.presets_file):
            try:
                with open(self.presets_file, 'r') as f:
                    data = json.load(f)
                    _legacy = {"Default", "Balanced", "High Quality", "Low FPS",
                               "Fast Encode", "No Audio"}
                    for k, v in data.items():
                        if k not in self.BUILTIN_PRESET_KEYS and k not in _legacy:
                            user_presets[k] = v
            except Exception:
                pass
        return user_presets

    def save_presets(self):
        try:
            with open(self.presets_file, 'w') as f:
                json.dump(self.presets, f, indent=4)
            return True
        except Exception:
            return False

    def get_preset(self, name):
        if self.is_builtin(name):
            return self.get_builtin_preset(name)
        return self.presets.get(name)

    def set_preset(self, name, values):
        if self.is_builtin(name):
            return False
        self.presets[name] = values
        return self.save_presets()

    def delete_preset(self, name):
        if self.is_builtin(name):
            return False
        if name in self.presets:
            del self.presets[name]
            return self.save_presets()
        return False

    def get_preset_names(self):
        return list(self.BUILTIN_PRESET_KEYS) + sorted(self.presets.keys())

    def snap_to_adpcm_nice_rate(self, rate):
        return min(self.ADPCM_NICE_RATES, key=lambda x: abs(x - rate))
