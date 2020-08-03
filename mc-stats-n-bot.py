#!/usr/bin/env python3

import os
import time
import subprocess
import re

import threading

import mcrcon
from discord.ext import commands

import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

# Get env vars
from dotenv import load_dotenv
load_dotenv()

# Connect with RCON
rcon = mcrcon.MCRcon()
rcon.connect("localhost", 25575, os.getenv("RCON_PASSWORD"), False)

# Initialize Discord bot
bot = commands.Bot(command_prefix="!")

# Define Discord commands
@bot.command(name="hello")
async def hello(ctx):
    await ctx.send("Hi! 🐇")
@bot.command(name="tps")
async def tps(ctx):
    await ctx.send(rcon.command("tps") + " 🐇")
@bot.command(name="list")
async def list(ctx):
    await ctx.send(rcon.command("list") + " 🐇")

# bot.run(os.getenv("DISCORD_TOKEN"))

# Initialize 128x64 display
disp = Adafruit_SSD1306.SSD1306_128_64(rst=None)
disp.begin()
disp.clear()
disp.display()
disp.set_contrast(32)

# Create blank image as canvas and drawing object
width = disp.width
height = disp.height
image = Image.new("1", (width, height))
draw = ImageDraw.Draw(image)

# Load font (more available here: http://www.dafont.com/bitmap.php)
# font = ImageFont.load_default()
font = ImageFont.truetype('Minecraftia.ttf', 8)

# Initialize TPS data list
TPSData = [0.0] * 128

# Screen update loop
def updateScreen(running):
    # Pixel shifting variables
    yMaxMovement = 15 # How many pixels to move
    yTimePerMovement = 60 # How long to wait between movements (in updates, about 1s)
    yDirection = True # Which direction we're changing the counter (True is increasing)
    yCounter = 0 # The counter

    while running:
        # Clear the image
        draw.rectangle((0,0,width,height), outline=0, fill=0)

        # CPU load per core
        cmd = "mpstat --dec=1 -P ALL 1 1 | awk 'length($3) == 1 {printf \"%s \", $4}'"
        CPU = subprocess.check_output(cmd, shell = True).decode("utf8").split(" ")
        # Memory
        cmd = "free -m | awk 'NR==2{printf \"M: %.1f%%\", $3*100/$2 }'"
        Mem = subprocess.check_output(cmd, shell = True).decode("utf8")
        # CPU temp
        cmd = "cat /sys/class/thermal/thermal_zone0/temp"
        Temp = "T: " + str(round(int(subprocess.check_output(cmd, shell = True))/1000)) + "C"
        # CPU frequency
        Freq0 = int(subprocess.check_output("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq", shell = True))
        Freq1 = int(subprocess.check_output("cat /sys/devices/system/cpu/cpu1/cpufreq/scaling_cur_freq", shell = True))
        Freq2 = int(subprocess.check_output("cat /sys/devices/system/cpu/cpu2/cpufreq/scaling_cur_freq", shell = True))
        Freq3 = int(subprocess.check_output("cat /sys/devices/system/cpu/cpu3/cpufreq/scaling_cur_freq", shell = True))
        Freq = "F: " + str(round(((Freq0 + Freq1 + Freq2 + Freq3) / 4)/1000000,1)) + "GHz"

        # Player list
        PlayerList = rcon.command("list")[43:].split(", ")
        # Ticks Per Second (
        TPSCmd = rcon.command("tps")
        TPSList = re.search(r".*?(\d{1,2}\.\d{1,2}).*?(\d{1,2}\.\d{1,2}).*?(\d{1,2}\.\d{1,2})", TPSCmd).groups()
        # Update current TPS data
        TPSData.pop(0)
        TPSData.append(float(TPSList[0]))

        y = yCounter/yTimePerMovement
        # Write first line (CPU load per core)
        draw.text((0, y), "% 5.1f" % float(CPU[0]), font=font, fill=255)
        draw.text((32, y), "% 5.1f" % float(CPU[1]), font=font, fill=255)
        draw.text((64, y), "% 5.1f" % float(CPU[2]), font=font, fill=255)
        draw.text((96, y), "% 5.1f" % float(CPU[3]), font=font, fill=255)
        # Write second line (memory, CPU temp, and CPU frequency)
        draw.text((0, y+8), Mem, font=font, fill=255)
        draw.text((46, y+8), Temp, font=font, fill=255)
        draw.text((80, y+8), Freq, font=font, fill=255)
        # Write third through fifth line (player names)
        draw.text((0, y+16), PlayerList[0][:11], font=font, fill=255) if len(PlayerList) > 0 else ""
        draw.text((64, y+16), PlayerList[1][:11], font=font, fill=255) if len(PlayerList) > 1 else ""
        draw.text((0, y+24), PlayerList[2][:11], font=font, fill=255) if len(PlayerList) > 2 else ""
        draw.text((64, y+24), PlayerList[3][:11], font=font, fill=255) if len(PlayerList) > 3 else ""
        draw.text((0, y+32), PlayerList[4][:11], font=font, fill=255) if len(PlayerList) > 4 else ""
        draw.text((64, y+32), PlayerList[5][:11], font=font, fill=255) if len(PlayerList) > 5 else ""
        # Write sixth line (TPS)
        draw.text((0, y+40), "TPS:", font=font, fill=255)
        draw.text((26, y+40), "%.2f" % float(TPSList[0]), font=font, fill=255)
        draw.text((60, y+40), "%.2f" % float(TPSList[1]), font=font, fill=255)
        draw.text((94, y+40), "%.2f" % float(TPSList[2]), font=font, fill=255)

        # Draw TPS graph
        for i in range(len(TPSData)):
            # draw.line((i, 70, i, 70-TPSData[i]), fill=255)
            draw.point((i, y+70-TPSData[i]), fill=255)

        # Display image
        disp.image(image)
        disp.display()
        # time.sleep(.1)

        # Shift image over time
        yCounter = yCounter + (1 if yDirection else -1)
        if yCounter > yMaxMovement * yTimePerMovement or yCounter <= 0:
            yDirection = not yDirection

try:
    running = threading.Semaphore()
    running.acquire()

    thread = threading.Thread(target=updateScreen, args=(running,))
    thread.start()

    bot.run(os.getenv("DISCORD_TOKEN"))


except KeyboardInterrupt:
    running.release()

finally:
    rcon.disconnect()
    disp.clear()
    disp.display()
