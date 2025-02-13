import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from history_get import get_current_price
from recent_trades import get_recent_trades
from submit_post import DeSoDexClient, post_to_deso
import os
from datetime import datetime, timezone
import json

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

# Function to load chat IDs from a file
def load_chat_ids():
    try:
        with open('chat_ids.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

# Function to save chat IDs to a file
def save_chat_ids(chat_ids):
    with open('chat_ids.json', 'w') as file:
        json.dump(chat_ids, file)

async def start(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    chat_ids = load_chat_ids()
    
    if chat_id not in chat_ids:
        chat_ids.append(chat_id)
        save_chat_ids(chat_ids)
    
    await update.message.reply_text('Hello! I am your trading bot. Use /bulktrade or /price or /subscribe to get started.')

async def bulktrade(update: Update, context: CallbackContext) -> None:
    trades = get_recent_trades()
    if trades:
        await update.message.reply_text("Last 24 hours Recent Bulk Trades:")
        for trade in trades:
            trade_type = trade.get('tradeType', 'N/A')
            trader_username = trade.get('traderUsername', 'Unknown')
            trade_value_usd = trade.get('tradeValueUsd', 0)
            trade_price_usd = trade.get('tradePriceUsd', 0)
            trade_timestamp = trade.get('tradeTimestamp', 'N/A')
            trade_value_deso = trade.get('tradeValueDeso', 0)

            # Parse the trade timestamp and make it timezone-aware
            trade_time = datetime.fromisoformat(trade_timestamp.replace('Z', '+00:00')).astimezone(timezone.utc)
            now = datetime.now(timezone.utc)
            time_diff = now - trade_time

            # Format the time difference
            if time_diff.seconds >= 3600:
                hours = time_diff.seconds // 3600
                time_ago = f"{hours} hours ago"
            else:
                minutes = time_diff.seconds // 60
                time_ago = f"{minutes} minutes ago"

            message = (
                f"Trade Type: {trade_type}\n"
                f"Trader: {trader_username}\n"
                f"Value (USD): ${trade_value_usd:,.2f}\n"
                f"Price (USD): ${trade_price_usd:,.2f}\n"
                f"Traded (DeSo): {trade_value_deso:,.2f}\n"
                f"Timestamp: {time_ago}\n"
                "---------------------------"
            )
            await update.message.reply_text(message)
    else:
        await update.message.reply_text("No recent trades found.")

async def price(update: Update, context: CallbackContext) -> None:
    price_data = get_current_price()
    if price_data and isinstance(price_data, list) and len(price_data) > 0:
        # Access the first element of the list
        data = price_data[0]
        
        op = data.get('open')
        cp = data.get('close')
        dh = data.get('high')
        dl = data.get('low')
        vol = data.get('volume')
        timestamp = data.get('timestamp')

        await update.message.reply_text(
            f"Current Price Details:\n"
            f"Open Price: {op}\n"
            f"Close Price: {cp}\n"
            f"Day High: {dh}\n"
            f"Day Low: {dl}\n"
            f"Volume: {vol}\n"
            f"Current Time: {timestamp}"
        )
    else:
        await update.message.reply_text("Failed to retrieve price data.")

async def calculate_percentage_change(context: CallbackContext) -> None:
    change_data = get_current_price()
    
    if change_data and isinstance(change_data, list) and len(change_data) > 0:
        # Access the first element of the list
        data = change_data[0]
        
        op = data.get('open')
        cp = data.get('close')
        print(op, cp)
        
        if cp > op:
            change = ((cp - op) / op) * 100
            message = f"🚀 $TOKEN surged by {change:.2f}% in the last 15 minutes! New LTP: {cp} DeSo."
            if change >= 10:
                await post_to_deso(message)  # Await the async function
                print("Posting to DeSo")
            await broadcast_message(context, message)  # Await the async function
            print("Broadcasting message")
        elif cp < op:
            change = ((op - cp) / op) * 100
            message = f"📉 $TOKEN dropped by {change:.2f}% in the last 15 minutes! New LTP: {cp} DeSo."
            if change >= 10:
                await post_to_deso(message)  # Await the async function
                print("Posting to DeSo")
            await broadcast_message(context, message)  # Await the async function
            print("Broadcasting message")
        else:
            message = "No change in price."
            print("No change in price")

    else:
        logger.error("Failed to retrieve 15-minute change data.")

async def broadcast_message(context: CallbackContext, message: str) -> None:
    subscribers = load_chat_ids()  # Load the list of subscribers
    for chat_id in subscribers:
        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")

async def subscribe(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    subscribers = load_chat_ids()  # Load the list of subscribers
    
    if chat_id not in subscribers:
        subscribers.append(chat_id)
        save_chat_ids(subscribers)  # Save the updated list
        await update.message.reply_text('You have subscribed to notifications.')
    else:
        await update.message.reply_text('You are already subscribed.')

def main() -> None:
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("bulktrade", bulktrade))
    application.add_handler(CommandHandler("price", price))
    application.add_handler(CommandHandler("subscribe", subscribe))

    # Add job to check 15-minute change every 15 minutes
    job_queue = application.job_queue
    job_queue.run_repeating(calculate_percentage_change, interval=900, first=0)

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
