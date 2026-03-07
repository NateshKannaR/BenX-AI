"""
Example plugin: time tools.
"""
from datetime import datetime


def register(manager):
    def _get_time(_obj, _ai_engine, _user_input):
        return f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    manager.register_command("get_time", _get_time)
