from core.state import JarvisState


class JarvisRouter:
    def __init__(self):
        self.state = JarvisState()
        self.tools: dict = {}

    def register_tool(self, name: str, func):
        self.tools[name] = func

    def handle_command(self, command: str, **kwargs) -> str:
        command = command.strip().lower()

        # Exact match
        if command in self.tools:
            return str(self.tools[command](**kwargs))

        # Prefix match — allows "search cats" to hit the "search" tool
        for key, func in self.tools.items():
            if command.startswith(key + " "):
                remainder = command[len(key):].strip()
                return str(func(query=remainder, **kwargs))

        return f"Unknown command: {command}"
