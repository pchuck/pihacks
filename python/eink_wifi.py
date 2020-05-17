#!/usr/bin/env python3
#
# eink_syslog.py
#
# A python script to continually update an e-ink display with wifi
# stats and info.
#
# Depends on a waveshare custom library, some configuration and fonts.
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
#
import time
import os
import sys
import subprocess
import logging
import textwrap
from PIL import Image, ImageDraw, ImageFont

# custom driver provided by waveshare
import epd2in13_V2


logging.basicConfig(level=logging.DEBUG)
font_path = os.path.dirname(os.path.realpath(__file__)) + "/../pylib"
font15 = ImageFont.truetype(os.path.join(font_path, 'Font.ttc'), 15)
font24 = ImageFont.truetype(os.path.join(font_path, 'Font.ttc'), 24)
white = 255
black = 0

def init_eink():
    logging.info("eink_wifi init")
    epd = epd2in13_V2.EPD()
    epd.init(epd.FULL_UPDATE)
    epd.Clear(0xFF)
    image = Image.new('1', (epd.height, epd.width), white)
    draw = ImageDraw.Draw(image)
    epd.init(epd.FULL_UPDATE)
    epd.displayPartBaseImage(epd.getbuffer(image))
    epd.init(epd.PART_UPDATE)
    return(epd, image, draw)

def find_value(iwc, key, units=False, trunc=False):
    i = iwc.find(key) + len(key)
    s = iwc[i:]
    if(units == False): e = s.find(' ') + i
    else:               e = s.find(' ', s.find(' ') + 1) + i
    if(trunc == False): value = iwc[i:e]
    else:               value = iwc[i:e-1]
        
    return(value)

def iwconfig_todict(iwc):
    d = {}
    d['essid'] = find_value(iwc, 'ESSID:', trunc=True)
    d['speed'] = find_value(iwc, 'Bit Rate=', units=True)
    d['quality'] = find_value(iwc, 'Link Quality=')
    d['signal'] = find_value(iwc, 'Signal level=', units=True)
    #    d['ap'] = find_value(iwc, 'Access Point: ', trunc=True)
    #    d['txp'] = find_value(iwc, 'Tx-power=', units=True)

    return(d)

def wifi_info(epd, image, draw):
    logging.info("eink_wifi monitoring..")
    iwc_out = os.popen('iwconfig').read()
    d = iwconfig_todict(iwc_out)
    l = []
    for k,v in d.items():
        l.append(k + ": " + v)

    while (True):
        draw.rectangle((0, 0, epd.height, epd.width), fill=white)
        y = 0 # text y-position
        for stat in l:
            draw.text((1, y), stat, font=font24, fill=black)
            y += 26
        draw.text((epd.height-60, epd.width-16),
                  time.strftime('%H:%M:%S'), font=font15, fill=black)
        epd.displayPartial(epd.getbuffer(image))
        time.sleep(1)

try:
    (epd, image, draw) = init_eink()
    wifi_info(epd, image, draw)

except IOError as e:
    logging.info(e)
    
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    epd2in13_V2.epdconfig.module_exit()
    exit()
