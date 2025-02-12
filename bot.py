import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from history_get import get_current_price, get_1h_change, get_15m_change
from recent_trades import get_recent_trades
from submit_post import DeSoDexClient, post_to_deso
import os

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
SEED_HEX = os.getenv("SEED_HEX")
PUBLIC_KEY = os.getenv("PUBLIC_KEY")
IS_TESTNET = False
NODE_URL = "https://test.deso.org" if IS_TESTNET else "https://node.deso.org"

# Initialize DeSo client
client = DeSoDexClient(is_testnet=IS_TESTNET, seed_phrase_or_hex=SEED_HEX, node_url=NODE_URL)

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hello! I am your trading bot. Use /bulktrade or /price to get started.')

def bulktrade(update: Update, context: CallbackContext) -> None:
    trades = get_recent_trades()
    if trades:
        update.message.reply_text("Recent Trades:")
        for trade in trades:
            update.message.reply_text(f"Trade: {trade}")
    else:
        update.message.reply_text("No recent trades found.")

def price(update: Update, context: CallbackContext) -> None:
    price_data = get_current_price()
    if price_data:
        op, cp, dh, dl, vol, current_unix_time = price_data
        update.message.reply_text(
            f"Current Price Details:\n"
            f"Open Price: {op}\n"
            f"Close Price: {cp}\n"
            f"Day High: {dh}\n"
            f"Day Low: {dl}\n"
            f"Volume: {vol}\n"
            f"Unix Time: {current_unix_time}"
        )
    else:
        update.message.reply_text("Failed to retrieve price data.")

def check_15m_change(context: CallbackContext) -> None:
    change, ltp = get_15m_change()
    if change >= 10:
        message = f"🚀 $TOKEN surged by {change}% in the last 15 minutes! New LTP: {ltp} SOL."
        context.bot.send_message(chat_id=os.getenv("TELEGRAM_CHAT_ID"), text=message)
        post_to_deso(message)  # Post to DeSo blockchain

def main() -> None:
    # Create the Updater and pass it your bot's token.
    updater = Updater(os.getenv("TELEGRAM_TOKEN"))

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Register command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("bulktrade", bulktrade))
    dispatcher.add_handler(CommandHandler("price", price))

    # Add job to check 15-minute change every 15 minutes
    job_queue = updater.job_queue
    job_queue.run_repeating(check_15m_change, interval=900, first=0)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM or SIGABRT
    updater.idle()

if __name__ == '__main__':
    main()
