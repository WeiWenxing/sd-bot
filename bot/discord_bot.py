import logging

import discord
from discord.ext import commands
from webuiapi_helper import WebUIApiHelper, byteBufferOfImage, saveImage
from config import discord_config

description = '''An bot to change clothes.'''

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='/', description=description, intents=intents)


@bot.command()
async def trip(ctx):
    await ctx.send(f'trip')


async def start_task():
    token = discord_config['discord_token']
    logging.info(f'{token}')
    return await bot.start(token)