#!/usr/bin/env python3
#
# eink_syslog.py
#
# A python script to continually update an e-ink display from syslog.
#
# Depends on a waveshare custom library, some configuration and fonts.
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
#
import sys
import os
import subprocess
import logging
from PIL import Image, ImageDraw, ImageFont
import textwrap

# custom driver provided by waveshare
import epd2in13_V2


logging.basicConfig(level=logging.DEBUG)
filename = '/var/log/syslog'
font_path = os.path.dirname(os.path.realpath(__file__)) + "/../pylib"
font15 = ImageFont.truetype(os.path.join(font_path, 'Font.ttc'), 15)
font24 = ImageFont.truetype(os.path.join(font_path, 'Font.ttc'), 24)


def draw_multiple_line_text(image, text, font, text_color, text_start_height):
    draw = ImageDraw.Draw(image)
    image_width, image_height = image.size
    y_text = text_start_height
    lines = textwrap.wrap(text, width=36)
    for line in lines:
        line_width, line_height = font.getsize(line)
        draw.text(((image_width - line_width) / 2, y_text), 
                  line, font=font, fill=text_color)
        y_text += line_height

def init_eink():
    logging.info("eink_syslog init")
    epd = epd2in13_V2.EPD()
    epd.init(epd.FULL_UPDATE)
    epd.Clear(0xFF)
    image = Image.new('1', (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)
    epd.init(epd.FULL_UPDATE)
    epd.displayPartBaseImage(epd.getbuffer(image))
    epd.init(epd.PART_UPDATE)
    return(epd, image, draw)

def syslog(epd, image, draw):
    logging.info("eink_syslog monitoring..")
    f = subprocess.Popen(['tail', '-F', filename],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    while (True):
        draw.rectangle((0, 0, epd.height, epd.width), fill = 255)
        line = f.stdout.readline()
        line = str(line)[2:-3] # drop first/last characters
        draw_multiple_line_text(image, str(line), font15, 0, 0)
        epd.displayPartial(epd.getbuffer(image))

try:
    (epd, image, draw) = init_eink()
    syslog(epd, image, draw)

except IOError as e:
    logging.info(e)
    
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    epd2in13_V2.epdconfig.module_exit()
    exit()

