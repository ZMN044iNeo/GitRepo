import threading
from jarvis2.core.router import JarvisRouter
from jarvis2.integrations import (
    elegoo_printer,
    browser_duckduckgo,
    vpn_control,
    steam_vr,
)
from jarvis2.integrations.matrix_ui import start_matrix_ui
from jarvis2.integrations.telegram_bot import start_telegram_bot
from jarvis2.old_jarvis.import_old import import_old_state


def main():
    jarvis = JarvisRouter()

    # Absorb old Jarvis config, aliases, habits
    import_old_state(jarvis)

    # Register all integration tools
    elegoo_printer.register(jarvis)
    browser_duckduckgo.register(jarvis)
    vpn_control.register(jarvis)
    steam_vr.register(jarvis)

    # Start the matrix UI (non-blocking placeholder)
    start_matrix_ui(jarvis)

    # Run Telegram bot in a background thread so it doesn't block
    t = threading.Thread(target=start_telegram_bot, args=(jarvis,), daemon=True)
    t.start()

    # Interactive console fallback
    print("Jarvis 2.0 online. Type a command (Ctrl+C to exit).")
    while True:
        try:
            cmd = input("> ").strip()
            if cmd:
                print(jarvis.handle_command(cmd))
        except (KeyboardInterrupt, EOFError):
            print("\nJarvis shutting down.")
            break


if __name__ == "__main__":
    main()
