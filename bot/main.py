import logging
import os
import asyncio

from webuiapi_helper import WebUIApiHelper
from telegram_bot import SDBot
from discord_bot import start_task
from config import sdwebuiapi_config


def main():
    # Read .env file

    # Setup logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(funcName)s:%(lineno)d] - %(message)s',
        level=logging.INFO
    )

    # Setup and run ChatGPT and Telegram bot
    api_helper = WebUIApiHelper(config=sdwebuiapi_config)
    telegram_bot = SDBot(api=api_helper)
    # telegram_bot.run()

    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    loop = asyncio.get_event_loop()

    tasks = [
        start_task(),
        telegram_bot.start_task(),
    ]
    try:
        loop.run_until_complete(asyncio.gather(*tasks))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


if __name__ == '__main__':
    main()
