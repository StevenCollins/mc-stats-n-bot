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

# Initialize emoji map array
emojiNumber = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔢"]
regexPattern = r"^([0️⃣,1️⃣,2️⃣,3️⃣,4️⃣,5️⃣,6️⃣,7️⃣,8️⃣,9️⃣]).*\|\|(.*)\|\|$"

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

# Set the no_category text to make the bot help look nice
help_command = commands.DefaultHelpCommand(
    no_category = 'Commands'
)

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=help_command)
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
            if not channel:
                channel = await bot.fetch_user(reminder["user"])
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
        "user": ctx.author.id,
        "time": (datetime.datetime.now() + datetime.timedelta(days=int(content[1]))).isoformat(),
        "interval": content[1],
        "message": " ".join(content[2:])
    })
    with open("reminders.json", "w") as remindersFile:
        json.dump(reminders, remindersFile)

# Remove reminder
def remove_reminder(uuid):
    with open("reminders.json", "r") as remindersFile:
        reminders = json.load(remindersFile)
    length = len(reminders)
    reminders[:] = [reminder for reminder in reminders if reminder.get('uuid') != uuid]
    length_changed = length != len(reminders)
    with open("reminders.json", "w") as remindersFile:
        json.dump(reminders, remindersFile)
    return length_changed

# List reminders
async def list_reminders(ctx):
    with open("reminders.json", "r") as remindersFile:
        reminders = json.load(remindersFile)
    channelReminders = [reminder for reminder in reminders if reminder["channel"] == ctx.channel.id]
    if len(channelReminders) == 0:
        await ctx.send("No reminders set 🐇")
    else:
        message = "I'm keeping track of these reminders:\n"
        for (i, reminder) in enumerate(channelReminders):
            if reminder["channel"] == ctx.channel.id:
                if i > 10: i = 10
                message += emojiNumber[i] + " " + reminder["time"][:16].replace("T", " ") + " " + reminder["message"] + " ||" + reminder["uuid"] + "||\n"
        message += "Respond with an emoji to erase that message 🐇\n"
        await ctx.send(message)

# Remove events via "List reminders" message
@bot.event
async def on_raw_reaction_add(payload):
    # Stop here if it's not an emoji we care about
    if payload.emoji.name not in emojiNumber[:-1]:
        return
    # Get the message
    channel = bot.get_channel(payload.channel_id)
    if not channel:
        channel = await bot.fetch_user(payload.user_id)
    message = await channel.fetch_message(payload.message_id)
    # Stop here if this message isn't from the bot or valid
    if message.author.id != bot.user.id or not message.content.startswith("I'm keeping track of these reminders:"):
        return
    # Parse the message, determine the correct reminder, and remove it
    reminders = re.findall(regexPattern, message.content, re.M)
    index = emojiNumber.index(payload.emoji.name)
    if index < len(reminders) and remove_reminder(reminders[index][1]):
        await channel.send("Forgot reminder " + payload.emoji.name + "! 🐇")
    else:
        await channel.send("Huh? 🐇")

# Define Discord commands
@bot.command(name="hello", hidden=True)
async def hello(ctx):
    await ctx.send("Hi! 🐇")
@bot.command(name="tps", brief="Check how well the Minecraft server is running")
async def tps(ctx):
    await ctx.send(getTPSString())
@bot.command(name="list", brief="List who's on the Minecraft server")
async def list(ctx):
    await ctx.send(getListString())
@bot.command(name="time", brief="Find out what time it is on the Minecraft server")
async def mctime(ctx):
    await ctx.send(getTimeString())
@bot.command(name="version", brief="See the current Minecraft server version")
async def version(ctx):
    await ctx.send(getVersionString())
@bot.command(name="remind", brief="Set a reminder", description="To set a reminder, type `!remind [number of days from now] [your message]`\nLike `!remind 7 give the bun a treat!`! 🐇")
async def reminder(ctx):
    add_reminder(ctx)
    await ctx.send("Got it! 🐇")
@bot.command(name="forget", brief="Forget a reminder")
async def forget(ctx):
    if remove_reminder(ctx.message.content.split()[1]):
        await ctx.send("Forgot it! 🐇")
    else:
        await ctx.send("Huh? 🐇")
@bot.command(name="remindlist", brief="List all reminders")
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