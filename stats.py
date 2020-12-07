#!/usr/bin/env python3

import os
import time
import subprocess
import re

import mcrcon

from board import SCL, SDA
import busio
import adafruit_ssd1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

# Get env vars
from dotenv import load_dotenv
load_dotenv()

# Connect with RCON
rcon = mcrcon.MCRcon()
rcon.connect("localhost", 25575, os.getenv("RCON_PASSWORD"), False)

# Initialize 128x64 display
i2c = busio.I2C(SCL, SDA)
disp = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)
disp.fill(0)
disp.show()
disp.contrast(32)

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
def updateScreen():
    # Pixel shifting variables
    yMaxMovement = 15 # How many pixels to move
    yTimePerMovement = 60 # How long to wait between movements (in updates, about 1s)
    yDirection = True # Which direction we're changing the counter (True is increasing)
    yCounter = 0 # The counter

    while True:
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
        disp.show()
        # time.sleep(.1)

        # Shift image over time
        yCounter = yCounter + (1 if yDirection else -1)
        if yCounter > yMaxMovement * yTimePerMovement or yCounter <= 0:
            yDirection = not yDirection

# Application flow
try:
    updateScreen()

except KeyboardInterrupt:
    pass

finally:
    rcon.disconnect()
    disp.fill(0)
    disp.show()
