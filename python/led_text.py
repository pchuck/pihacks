#!/usr/bin/env python3
#
import argparse
from luma.led_matrix.device import max7219 as led
from luma.core.interface.serial import spi, noop
from luma.core.legacy.font import proportional, CP437_FONT, TINY_FONT, SINCLAIR_FONT, LCD_FONT
from luma.core.legacy import text, show_message

n = 4 # number of led blocks
rotate = 0 # rotation in degrees of text
block_orientation=90 # rotation in degrees of blocks
inreverse=True # if blocks are wired in reverse
intensity = 128 # led intensity, scale of 0..255
delay = 0.1 # scroll delay

font=LCD_FONT
serial = spi(port=0, device=0, gpio=noop())
device = led(serial, cascaded=n, block_orientation=block_orientation, rotate=rotate, blocks_arranged_in_reverse_order=inreverse)
device.contrast(intensity)

parser = argparse.ArgumentParser(description='led_display arguments',
             formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument("msg", help="display the string you use here")
args = parser.parse_args()
msg = args.msg

show_message(device,
             msg,
             fill='White', # or fill='color'
             font=proportional(font),
             scroll_delay=delay)
