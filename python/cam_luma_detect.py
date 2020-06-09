#!/usr/bin/env python3
#
# raspberry pi camera to display renderer with text detection via tesseract
# 
# prerequisites:
#   apt install libtesseract-dev
#   apt install tesseract-ocr
#   pip3 install pytesseract
#   pip3 install luma.core luma.lcd
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
#
import os, sys
import argparse
import pytesseract
from picamera.array import PiRGBArray
from picamera import PiCamera
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.lcd.device import ili9341 as led
from PIL import Image, ImageFont

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
    rkey = 10
    x, y = display.width, display.height
    fp = os.path.dirname(sys.argv[0]) + '/../fonts'
    font = ImageFont.truetype(fp + '/ProggyTiny.ttf', font_size)
    cols = int(x / (font_size / 2 - 1)) # ~106 w/ font_size=8
    raw = PiRGBArray(camera, size=(x, y))

    for i, frame in enumerate(camera.capture_continuous(raw, format="rgb")): 
        nd_image = frame.array
        image = Image.fromarray(nd_image)

        # detect
        if(i % rkey == 0):
            text = pytesseract.image_to_string(nd_image)
            if(text != ''): print(text)

        # display
        image = image.convert('L').convert('RGB')
        display.display(image)
                
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
