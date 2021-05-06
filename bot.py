#!/usr/bin/env python3

import os
import re

import mcrcon
import discord
from discord.ext import commands

# Get env vars
from dotenv import load_dotenv
load_dotenv()

# Connect with RCON
rcon = mcrcon.MCRcon()
rcon.connect(os.getenv("HOST"), int(os.getenv("PORT")), os.getenv("RCON_PASSWORD"), False)

# Response string functions
def getTPSString():
    TPSCmd = rcon.command("tps")
    TPSList = re.search(r".*?(\d{1,2}\.\d{1,2}).*?(\d{1,2}\.\d{1,2}).*?(\d{1,2}\.\d{1,2})", TPSCmd).groups()
    return f"The current TPS is {float(TPSList[0]):.2f}. Last 5 minutes, {float(TPSList[1]):.2f}. Last 20 minutes, {float(TPSList[2]):.2f}. 🐇"
def getListString():
    return rcon.command("list") + " 🐇"
def getTimeString():
    return rcon.command("time query daytime") + ". (Day is from 0 to 12000) 🐇"

# Initialize Discord bot
bot = commands.Bot(command_prefix="!")
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Minecraft"))

# Define Discord commands
@bot.command(name="hello")
async def hello(ctx):
    await ctx.send("Hi! 🐇")
@bot.command(name="tps")
async def tps(ctx):
    await ctx.send(getTPSString())
@bot.command(name="list")
async def list(ctx):
    await ctx.send(getListString())
@bot.command(name="time")
async def list(ctx):
    await ctx.send(getTimeString())

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if os.getenv("DISCORD_USER_ID") in message.content:
        if "hi" in message.content.lower() or "hello" in message.content.lower():
            await message.channel.send(f"Hi {message.author.mention}! 🐇")
        if "lag" in message.content.lower():
            await message.channel.send(getTPSString())
        if "list" in message.content.lower() or "play" in message.content.lower():
            await message.channel.send(getListString())
        if "time" in message.content.lower() or "morning" in message.content.lower():
            await message.channel.send(getTimeString())
    elif any(word in message.content.lower() for word in ["owo", "uwu"]):
        await message.channel.send("*nuzzles you*")

    await bot.process_commands(message)

# Application flow
try:
    bot.run(os.getenv("DISCORD_TOKEN"))

except KeyboardInterrupt:
    pass

finally:
    rcon.disconnect()
