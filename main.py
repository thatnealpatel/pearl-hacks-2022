# Copyright 2022 Google LLC
# Author: Neal Patel (nealpatel@google.com)

import logging
import os
import threading
import time

from dotenv import dotenv_values 
from random import randint
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import Dispatcher
from telegram.ext import Filters
from telegram.ext import Updater

# Define Constants for our Program
# ==============================================================================
# We'll define a few constants that we will use for our project. Since we'll be
# using them all the time, it makes sense to define them once, and use a clever
# name when we need to refer to the value they hold.

CHAT_ID = dotenv_values('.env')['CHAT_ID'] # My personal Telegram Chat ID 
BOT_SECRET = dotenv_values('.env')['BOT_SECRET'] # Secret Sauce for the program
HELP_TEXT = """Here's a list of available commands:
/help    see this menu again.
/start    start the screen time timer.
"""
NOTIFICATION_THRESHOLD = 10 # Seconds between notifications
NOTIFICATION_TIMEOUT = 20 # Seconds until notified
INTERRUPT_PROMPTS = [
        "Hey, it's been a while since you've looked away. Take a moment to stretch!",
        "Ahoy, did you know 5 minutes of sunlight can rejuvinate your focus?!",
        "Hi there, take a moment to walk around and focus on your breathing!",
        "Greetings! Let's recenter; how about a walk?",
]
TOTAL_PROMPTS = len(INTERRUPT_PROMPTS)


# Set up our logger
# ==============================================================================
# This will allow us to see more information about what exactly is happening in
# the background. It really helps when we run into issues. The more information
# we have to solve a problem, the easier it is to solve (hopefully) :]

logger = logging.getLogger('ScreenTimeBuddy')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)15s - %(threadName)-11s - %(name)s - %(levelname)s - %(message)s'
)
ch.setFormatter(formatter)
logger.addHandler(ch)

# Globally Scoped Variables
# ==============================================================================
# In order for our Telegram Bot to successfully work as discussed, we need to
# keep track of some information and make it available to our bot! To keep
# things simple, we are simply defining them as global. This may not be the
# "best" practice, remember: we are learning. Build the MVP!
# 
# Fun Fact: Due to Python's nature, the GIL (Global Interpreter Lock) prevents 
# true multi-threading, as you'd find in languages such as C++ or Go.
#
# For those who are studious, this code implements a naive threading model. This
# is generally "okay" in this case because by not implementing a thread-safe
# screen time buddy, the impact is limited to a few, rare misreads of the clock
# that would be off by 1 second. Most importantly, only one worker updates the
# `timer`, and a different (and only one) worker updates `last_notification`.
#
# As a follow up exercise, you could make modifications to this source code to
# ensure that it is thread-safe. See reading: locks, mutexes, threading, python

timer: int = 0
last_notification: int = 0
clock = threading.Event()
application = threading.Event()

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


def help_handler(update: Update, context: CallbackContext) -> None:
    logger.info(update.message.chat)
    context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=HELP_TEXT
    )


def start_handler(update: Update, context: CallbackContext) -> None:
    global clock
    clock.set()
    context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Started the clock!'
    )


def stop_handler(update: Update, context: CallbackContext) -> None:
    global clock
    clock.clear()
    elapsed = time.strftime('%H:%M:%S', time.gmtime(timer))
    context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'Stopped the clock!\nYou were on your screen for {elapsed}'
    )


def screen_time_clock() -> None:
    global application, clock, timer
    while application.is_set():
        time.sleep(1)
        if clock.is_set():
            timer += 1
            logger.info(f'Updated timer! ({timer=}).')


def screen_time_checker(dispatcher: Dispatcher) -> None:
    global application, clock, timer, last_notification
    while application.is_set():
        time.sleep(0.5)
        exceeded_screen_time = timer > NOTIFICATION_THRESHOLD 
        not_being_annoying = timer - last_notification > NOTIFICATION_TIMEOUT
        if exceeded_screen_time and not_being_annoying:
            logger.info(f'Sent a message!')
            dispatcher.bot.send_message(
                    chat_id=CHAT_ID,
                    # randint(x, y) -> [x, y], we want [x, y) == [x, y - 1]
                    text=INTERRUPT_PROMPTS[randint(0, TOTAL_PROMPTS - 1)]
            )
            last_notification = timer # Simple bit of maths to not be annoying


# Write our main() function 
# ==============================================================================
# Here we will add all of the "helper" functions that our Dispatcher will be
# using when we interact with it.

def main():
    updater = Updater(BOT_SECRET)
    dispatcher = updater.dispatcher

    # Add various handlers
    dispatcher.add_handler(CommandHandler('help', help_handler))
    dispatcher.add_handler(CommandHandler('start', start_handler))
    dispatcher.add_handler(CommandHandler('stop', stop_handler))

    # Create the clock monitor worker (i.e. thread)
    clock_worker = threading.Thread(
            target=screen_time_clock,
            name='ClockWorker'
    )

    # Create the screen monitor worker (i.e. thread)
    screen_monitor_worker = threading.Thread(
            target=screen_time_checker,
            name='SreenMonitorWorker',
            args=(dispatcher,) # The comma is necessary!
    )


    try:
        # Add a welcome message for when you run the program!
        dispatcher.bot.send_message(
                chat_id=CHAT_ID, # This is "sort of" a secret
                text='Hello, my name is STiB, and I am your ScreenTimeBuddy.'
        )

        # Start our application event
        application.set()

        # Start the workers
        clock_worker.start()
        screen_monitor_worker.start()
        updater.start_polling()
        while True: time.sleep(0.1)

    except KeyboardInterrupt:
        # Block until you interrupt on command line
        logger.info('Attempting a graceful exit...')
        
        # python-telegram-bot (the PyPI package) has a special way to stop its
        # worker. It's more sophisticated, which is why we don't need to
        # clear our application (threading.Event) for it to stop working.
        updater.stop()
        logger.info('Exited Telegram.updater.')

        # All of our custom workers now know to stop working!
        application.clear()
        screen_monitor_worker.join()
        logger.info('Exited ScreenMonitorWorker.')
        clock_worker.join()
        logger.info('Exited ClockWorker.')

    except Exception as e:
        logger.error(f'{e.with_traceback()}')
        dispatcher.bot.send_message(
                chat_id=CHAT_ID, # This is "sort of" a secret
                text='STiB ran into a critical internal error!'
        )

    finally:
        logger.info('All cleaned up!')
        dispatcher.bot.send_message(
                chat_id=CHAT_ID, # This is "sort of" a secret
                text='STiB is going offline; keep up those healthy habits!'
        )


if __name__ == "__main__":
    main()
