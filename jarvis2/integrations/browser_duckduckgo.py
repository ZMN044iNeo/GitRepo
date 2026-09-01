import webbrowser
from urllib.parse import quote_plus


def open_duckduckgo(query: str = "") -> str:
    url = "https://duckduckgo.com/" + (f"?q={quote_plus(query)}" if query else "")
    webbrowser.open(url)
    return f"Opened DuckDuckGo: {query or '(home)'}"


def register(jarvis):
    jarvis.register_tool("search", lambda query="", **_: open_duckduckgo(query))
