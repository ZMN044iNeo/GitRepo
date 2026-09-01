from dataclasses import dataclass, field
from typing import Any


@dataclass
class JarvisState:
    matrix_mode:  str            = "DEFAULT"
    vpn_active:   bool           = False
    printer_last: dict           = field(default_factory=dict)
    old_profiles: dict           = field(default_factory=dict)
    custom:       dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any):
        self.custom[key] = value

    def get(self, key: str, default=None):
        return self.custom.get(key, default)
