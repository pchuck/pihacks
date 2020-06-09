#!/usr/bin/env python3
#
# raspberry pi camera to display renderer, including 'ascii' mode
# 
# prerequisites:
#   pip3 install luma.core luma.lcd
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
#
import os, sys
import argparse
from picamera.array import PiRGBArray
from picamera import PiCamera
from luma.core.interface.serial import spi, noop
from luma.lcd.device import ili9341 as led
from PIL import Image, ImageFont
from luma.core.render import canvas

import ultrametrics_rpi
from image_ascii_converter import image_to_ascii

def setup_display(speed=32000000, rotate=0):
    serial = spi(port=0, device=0, gpio_DC=23, gpio_RST=24, bus_speed_hz=speed)
    device = led(serial, gpio_LIGHT=25, active_low=False, rotate=rotate)
    device.backlight(True)
    return device

def setup_camera(x, y, framerate=30):
    camera = PiCamera()
    camera.resolution = (x, y)
    camera.framerate = framerate
    return camera

def main(display, camera, scale=0.40, font_size=8, mode='color'):
    threshold = 128
    x, y = display.width, display.height
    fp = os.path.dirname(sys.argv[0]) + '/../fonts'
    font = ImageFont.truetype(fp + '/ProggyTiny.ttf', font_size)
    cols = int(x / (font_size / 2 - 1)) # ~106 w/ font_size=8
    raw = PiRGBArray(camera, size=(x, y))

    for frame in camera.capture_continuous(raw, format="rgb"): 
        nd_image = frame.array
        image = Image.fromarray(nd_image)

        if(mode == 'color'): # rgb color
            display.display(image)
        if(mode == 'dithered'): # b/w dithered
            image = image.convert('1').convert('RGB')
            display.display(image)
        if(mode == 'mono'): # true mono
            fn = lambda x : 255 if x > threshold else 0
            image = image.convert('L').point(fn, mode='1').convert('RGB')
            display.display(image)
        if(mode == 'grayscale'):
            # 8-bit grayscale, matte
            image = image.convert('L').convert('RGB')
            display.display(image)
        if(mode == 'ascii'):
            a_image = image_to_ascii(image, cols, scale, False)
            with canvas(display) as draw:
                for i, line in enumerate(a_image):
                    draw.text((0, font_size*i), line, fill='White', font=font)
                
        raw.truncate(0)

try:
    parser = argparse.ArgumentParser(description='sensor_panel arguments',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--mode', type=str, default='ascii',
                        choices=['color', 'dithered', 'mono',
                                 'grayscale', 'ascii'],
                        help='The type of image rendition')
    args = parser.parse_args()
    
    display = setup_display()
    camera = setup_camera(display.width, display.height)
    main(display, camera, mode=args.mode)
except KeyboardInterrupt:
    print('interrupted')
