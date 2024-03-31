#!/usr/bin/env python3

import os
import re
import time
import json
import datetime
import uuid

import mcrcon
import discord #library is "discord.py"
from discord.ext import commands, tasks

# Get env vars
from dotenv import load_dotenv #library is "python-dotenv"
load_dotenv()

# Connect with RCON
rconConnected = False
rcon = mcrcon.MCRcon()
try:
    rcon.connect(os.getenv("HOST"), int(os.getenv("PORT")), os.getenv("RCON_PASSWORD"), False)
    rconConnected = True
except ConnectionRefusedError:
    pass

# Response string functions
def getTPSString():
    if not rconConnected:
        return "I'm not playing Minecraft right now 🐇"
    TPSCmd = rcon.command("tps")
    TPSList = re.search(r".*?(\d{1,2}\.\d{1,2}).*?(\d{1,2}\.\d{1,2}).*?(\d{1,2}\.\d{1,2})", TPSCmd).groups()
    return f"The current TPS is {float(TPSList[0]):.2f}. Last 5 minutes, {float(TPSList[1]):.2f}. Last 20 minutes, {float(TPSList[2]):.2f}. 🐇"
def getListString():
    if not rconConnected:
        return "I'm not playing Minecraft right now 🐇"
    return rcon.command("list") + " 🐇"
def getTimeString():
    if not rconConnected:
        return "I'm not playing Minecraft right now 🐇"
    return rcon.command("time query daytime") + ". (Day is from 0 to 12000) 🐇"
def getVersionString():
    if not rconConnected:
        return "I'm not playing Minecraft right now 🐇"
    versionLines = []
    while len(versionLines) == 0:
      versionCmd = rcon.command("version")
      versionSearch = re.search(r"^§.(.*)§r$", versionCmd, re.MULTILINE)
      if hasattr(versionSearch, "groups"):
        versionLines = versionSearch.groups()
      else:
        time.sleep(0.5)
    return f"{versionLines[0]} 🐇"

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
@bot.event
async def on_ready():
    if rconConnected:
        await bot.change_presence(activity=discord.Game(name="Minecraft"))
    else:
        await bot.change_presence(activity=None)
    reminders_task.start()

# Reminders background task
@tasks.loop(seconds=60)
async def reminders_task():
    with open("reminders.json", "r") as remindersFile:
        reminders = json.load(remindersFile)
    hasChanged = False
    for reminder in reminders:
        if datetime.datetime.fromisoformat(reminder["time"]) < datetime.datetime.now():
            reminder["time"] = (datetime.datetime.now() + datetime.timedelta(days=int(reminder["interval"]))).isoformat()
            hasChanged = True
            channel = bot.get_channel(reminder["channel"])
            await channel.send(reminder["message"])
    if hasChanged:
        with open("reminders.json", "w") as remindersFile:
            json.dump(reminders, remindersFile)

# Add reminder
def add_reminder(ctx):
    with open("reminders.json", "r") as remindersFile:
        reminders = json.load(remindersFile)
    content = ctx.message.content.split()
    reminders.append({
        "uuid": str(uuid.uuid4()),
        "channel": ctx.channel.id,
        "time": (datetime.datetime.now() + datetime.timedelta(days=int(content[1]))).isoformat(),
        "interval": content[1],
        "message": " ".join(content[2:])
    })
    with open("reminders.json", "w") as remindersFile:
        json.dump(reminders, remindersFile)

# Remove reminder
def remove_reminder(ctx):
    with open("reminders.json", "r") as remindersFile:
        reminders = json.load(remindersFile)
    content = ctx.message.content.split()
    length = len(reminders)
    reminders[:] = [reminder for reminder in reminders if reminder.get('uuid') != content[1]]
    length_changed = length != len(reminders)
    with open("reminders.json", "w") as remindersFile:
        json.dump(reminders, remindersFile)
    return length_changed

# List reminders
async def list_reminders(ctx):
    with open("reminders.json", "r") as remindersFile:
        reminders = json.load(remindersFile)
    if len(reminders) == 0:
        await ctx.send("No reminders set 🐇")
    else:
        for reminder in reminders:
            await ctx.send(reminder["uuid"] + ": " + reminder["message"])

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
async def mctime(ctx):
    await ctx.send(getTimeString())
@bot.command(name="version")
async def version(ctx):
    await ctx.send(getVersionString())
@bot.command(name="remind")
async def reminder(ctx):
    add_reminder(ctx)
    await ctx.send("Got it! 🐇")
@bot.command(name="forget")
async def forget(ctx):
    if remove_reminder(ctx):
        await ctx.send("Forgot it! 🐇")
    else:
        await ctx.send("Huh? 🐇")
@bot.command(name="remindlist")
async def reminder_list(ctx):
    await list_reminders(ctx)

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
        if "version" in message.content.lower() or "1." in message.content.lower():
            await message.channel.send(getVersionString())
        if "reminders" in message.content.lower() in message.content.lower():
            await list_reminders(message.channel)
    if any(word in message.content.lower() for word in ["owo", "uwu"]):
        await message.channel.send("*nuzzles you*")

    await bot.process_commands(message)

# Application flow
try:
    # Create the reminders.json file if it doesn't already exist
    if not os.path.exists("reminders.json"):
        with open("reminders.json", "+w") as remindersFile:
            json.dump([], remindersFile)
    # Run the bot!
    bot.run(os.getenv("DISCORD_TOKEN"))

except KeyboardInterrupt:
    pass

finally:
        rcon.disconnect()