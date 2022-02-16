import logging
import os

from dotenv import dotenv_values 
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import Dispatcher
from telegram.ext import Filters
from telegram.ext import Updater

# Load of Environment Secrets (.env) into our Python script
# ==============================================================================
BOT_SECRET = dotenv_values('.env')['BOT_SECRET']


# Set up our logger
# ==============================================================================
# This will allow us to see more information about what exactly is happening in
# the background. It really helps when we run into issues. The more information
# we have to solve a problem, the easier it is to solve (hopefully) :]

logger = logging.getLogger('ScreenTimeBuddy')
logger.setLevel(logging.DEBUG)
logger.propagate = False
ch = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)15s - %(threadName)-11s - %(name)s - %(levelname)s - %(message)s'
)
ch.setFormatter(formatter)
logger.addHandler(ch)


# Telegram Bot Functions
# ==============================================================================
# Here we will place all of the "helper" functions that our Dispatcher will be
# responsible for adding to the Updater. We define these functions here for a
# few reasons:
#
# (1) It is easier to read and follow what is happening
# (2) It is good practice to make small chucks, unique (atomic) chunks of
# functionality their own block of logic.
# (3) It keeps our code modular and clean

def echo_handler(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(update.message.text)


# Write our main() function 
# ==============================================================================
# Here we will add all of the "helper" functions that our Dispatcher will be
# using when we interact with it.

def main():
    updater = Updater(BOT_SECRET)
    dispatcher = updater.dispatcher

    # Add various handlers
    dispatcher.add_handler(CommandHandler('echo', echo_handler))

    # Start the bot
    updater.start_polling()
    
    # Block until you interrupt on command line
    updater.idle()


if __name__ == "__main__":
    main()
