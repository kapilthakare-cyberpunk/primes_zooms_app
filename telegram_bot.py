import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from csv_processor import load_inventory
from ai_agents import RentalConsultant, PricingAssistant

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PRICELIST_PATH = os.path.join(os.path.dirname(__file__), "Pricelist_20260702.csv")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

inventory_df = None


def load_pricelist():
    global inventory_df
    inventory_df = load_inventory(PRICELIST_PATH)
    if inventory_df is not None:
        logging.info("Loaded %d items from pricelist", len(inventory_df))
    else:
        logging.error("Failed to load pricelist from %s", PRICELIST_PATH)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Primes & Zooms AI Assistant! 📷\n\n"
        "Ask me anything about our rental inventory — cameras, lenses, "
        "lighting, audio, accessories, and more.\n\n"
        "Examples:\n"
        "• \"What's the rent for Sony A7S III for 5 days?\"\n"
        "• \"Do you have any Canon lenses?\"\n"
        "• \"Suggest a camera for wedding photography\"\n\n"
        "Type /help for commands."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/start — Welcome message\n"
        "/help — This help\n"
        "/search <query> — Search inventory\n"
        "/price <item> — Get pricing for an item\n\n"
        "Or just type your question in natural language!"
    )


async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search <query>\nExample: /search Sony lens")
        return
    query = " ".join(context.args)
    await handle_query(update, context, query)


async def price_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /price <item name>\nExample: /price Canon 5D Mark IV")
        return
    query = " ".join(context.args)
    await handle_query(update, context, f"What is the rent for {query}?")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_query(update, context, update.message.text)


async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    if inventory_df is None:
        await update.message.reply_text("⚠️ Pricelist not loaded. Please restart the bot.")
        return
    if not GROQ_API_KEY:
        await update.message.reply_text("⚠️ GROQ_API_KEY not configured.")
        return

    await update.message.chat.send_action("typing")

    try:
        consultant = RentalConsultant(GROQ_API_KEY, inventory_df)
        response = consultant.consult(query)
        await update.message.reply_text(response, disable_web_page_preview=True)
    except Exception as e:
        logging.error("Error handling query: %s", e)
        await update.message.reply_text(f"⚠️ Error: {e}")


def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN not set in .env")
        return

    load_pricelist()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("Telegram bot started. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
