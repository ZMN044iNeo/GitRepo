import json
import os


def import_old_state(jarvis):
    """Load config/habits from the old Jarvis backup and register them."""
    _load_profiles(jarvis)
    _register_old_commands(jarvis)


def _load_profiles(jarvis):
    profile_path = os.path.join(os.path.dirname(__file__), "old_profiles.json")
    if os.path.exists(profile_path):
        with open(profile_path, "r") as f:
            jarvis.state.old_profiles = json.load(f)


def _register_old_commands(jarvis):
    # Re-register any saved command aliases from the old system
    for alias, target in jarvis.state.old_profiles.get("aliases", {}).items():
        jarvis.register_tool(alias, lambda t=target, **_: jarvis.handle_command(t))
