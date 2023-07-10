from telegram import ForceReply, Update
import cryptocompare
import firebase_admin
from firebase_admin import firestore, credentials
from datetime import datetime, time, date, timedelta
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from typing import Final
import constants

TELEGRAM_API_KEY: Final = constants.TELEGRAM_KEY
USERNAME: Final = "@WorkRelatedTestBot"
CURRENCY: Final = "USD"

top = ["BTC", "ETH", "BNB", "XRP", "ADA", "DOGE", "SOL", "LTC", "TRX", "MATIC", "DOT"]

cred = credentials.Certificate("./key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def get_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gets the current price and 24h change in price of specified coin"""
    arg = update.message.text.split()[1].upper()
    if len(words) <= 1:
        await update.message.reply_text("Usage: /get <COIN TOKEN>")
        return

    resp = cryptocompare.get_price(arg, currency=CURRENCY)
    if resp != None:
        price = resp[arg][CURRENCY]
        timestamp = datetime.now() - timedelta(days=-1)
        old_resp = cryptocompare.get_historical_price(arg, CURRENCY, timestamp)
        old_price = old_resp[arg][CURRENCY]
        change = (price - old_price) / price * 100
        await update.message.reply_text(
            f"{arg} Price: ${price}\nChange in 24h: {change:.2f}%"
        )


async def gettop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows the price and the 24h price change of large marketcap coins"""
    resp = cryptocompare.get_price(top, currency=CURRENCY)
    timestamp = datetime.now() - timedelta(days=-1)
    old_resp = {}
    for token in top:
        old_resp[token] = cryptocompare.get_historical_price(
            token, CURRENCY, timestamp
        )[token]
    finalmsg = []
    zipped = zip(resp, old_resp)
    for key, _ in zipped:
        price = resp[key][CURRENCY]
        old_price = old_resp[key][CURRENCY]
        change = (price - old_price) / price * 100
        msg = f"{key}:  ${price}  ({change:.2f}%)\n"
        finalmsg.append(msg)
    await update.message.reply_text(
        "Current price of High marketcap coins with change in 24h: \n\n"
        + "".join(finalmsg)
    )


async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows the current price and the 24h price change of all watchlisted coins"""
    words = update.message.text.split()
    username = update.message.from_user.username
    if username == None:
        await update.message.reply_text("You need a username to use this command.")
        return
    docref = db.document(f"users/{username}")
    doc = docref.get()
    if not doc.exists:
        await update.message.reply_text(
            "You don't have a watchlist. Use /addcoin to start one."
        )
        return
    data = doc.to_dict()
    tokens = data["tokens"]
    if len(tokens) == 0:
        await update.message.reply_text(
            "You don't have a watchlist. Use /addcoin to start one."
        )
        return
    resp = cryptocompare.get_price(tokens, currency=CURRENCY)
    timestamp = datetime.now() - timedelta(days=-1)
    old_resp = {}
    for token in tokens:
        old_resp[token] = cryptocompare.get_historical_price(
            token, CURRENCY, timestamp
        )[token]
    finalmsg = []
    zipped = zip(resp, old_resp)
    for key, _ in zipped:
        price = resp[key][CURRENCY]
        old_price = old_resp[key][CURRENCY]
        change = (price - old_price) / price * 100
        msg = f"{key}:  ${price}  ({change:.2f}%)\n"
        finalmsg.append(msg)
    await update.message.reply_text(
        "Current price of watchlisted coins with change in 24h: \n\n"
        + "".join(finalmsg)
    )


async def addcoin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adds specified coin to users watchlist"""
    words = update.message.text.split()
    if len(words) <= 1:
        await update.message.reply_text("Usage: /addcoin <COIN TOKEN>")
        return
    username = update.message.from_user.username
    if username == None:
        await update.message.reply_text("You need a username to use this command.")
        return
    arg = words[1].upper()
    resp = cryptocompare.get_price(arg, currency=CURRENCY)
    if resp != None:
        docref = db.document(f"users/{username}")
        docref.set({"tokens": firestore.ArrayUnion([arg])}, merge=True)
        await update.message.reply_text(f"{arg} added to watchlist.")
    else:
        await update.message.reply_text(f"{arg} not found.")


async def removecoin_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Removes specified coin from users watchlist"""
    words = update.message.text.split()
    if len(words) <= 1:
        await update.message.reply_text("Usage: /removecoin <COIN TOKEN>")
        return
    username = update.message.from_user.username
    if username == None:
        await update.message.reply_text("You need a username to use this command.")
        return
    docref = db.document(f"users/{username}")
    doc = docref.get()
    if not doc.exists:
        await update.message.reply_text(
            "You don't have a watchlist. Use /addcoin to start one."
        )
        return
    arg = words[1].upper()
    data = doc.to_dict()
    if arg in data["tokens"]:
        docref.update({"tokens": firestore.ArrayRemove([arg])})
        await update.message.reply_text(f"{arg} removed from watchlist.")
    else:
        await update.message.reply_text(f"You do not have {arg} in your watchlist.")


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Update {update} caused error: {context.error}")


def main() -> None:
    """Start the bot."""
    print("starting bot")
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_API_KEY).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("get", get_command))
    application.add_handler(CommandHandler("gettop", gettop_command))
    application.add_handler(CommandHandler("addcoin", addcoin_command))
    application.add_handler(CommandHandler("removecoin", removecoin_command))
    application.add_handler(CommandHandler("watchlist", watchlist_command))

    application.add_error_handler(error)

    print("polling")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
