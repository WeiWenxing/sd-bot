import logging
import os
import asyncio

from webuiapi_helper import WebUIApiHelper
from telegram_bot import SDBot
import discord_bot
from config import sdwebuiapi_config
from config import discord_config
from config import telegram_config


def main():
    # Read .env file

    # Setup logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(funcName)s:%(lineno)d] - %(message)s',
        level=logging.INFO
    )

    # Setup and run ChatGPT and Telegram bot
    api_helper = WebUIApiHelper(config=sdwebuiapi_config)
    tel_bot = SDBot(api=api_helper)
    # telegram_bot.run()

    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    loop = asyncio.get_event_loop()

    tasks = []
    discord_token = str(discord_config['token'])
    telegram_token = str(telegram_config['token'])
    logging.info(f'discord token: {discord_token}')
    logging.info(f'telegram token: {telegram_token}')

    if discord_token:
        tasks.append(discord_bot.start_task())

    if telegram_token:
        tasks.append(tel_bot.start_task())

    try:
        loop.run_until_complete(asyncio.gather(*tasks))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


if __name__ == '__main__':
    main()
