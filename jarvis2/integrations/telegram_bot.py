from telegram.ext import ApplicationBuilder, CommandHandler
from core.router import JarvisRouter
from core.config import TELEGRAM_TOKEN


def start_telegram_bot(jarvis: JarvisRouter):
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    async def jarvis_cmd(update, context):
        text = " ".join(context.args)
        result = jarvis.handle_command(text)
        await update.message.reply_text(str(result))

    app.add_handler(CommandHandler("jarvis", jarvis_cmd))
    # run_polling blocks — call from a thread if running alongside other services
    app.run_polling()
