#!/usr/bin/env python3
#
# led_pixel.py
#
# An even simpler version of led_swarm and led_pixels.
# Requires a Raspberry pi with MAX7219 LED wired to GPIO contacts.
#
# Applies brownian motion to pseudo-randomly move an illuminated
# element around an LED array.
#
# See led_swarm.py for the more generic and sophisticated control script.
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
#
import time

from luma.core.interface.serial import spi, noop
from luma.led_matrix.device import max7219 as led
from luma.core.render import canvas
from random import randrange

n = 4 # number of led panels/blocks
rotate = 0 # rotation of individual blocks (0=0°, 1=90°, 2=180°, 3=270°)
block_orientation = 90 # in degrees, for horiz vs. vert arrangement of blocks
inreverse = True # if blocks are wired in reverse
intensity = 32 # led intensity, scale of 0..255
delay = 0.1 # refresh delay (in seconds)
w = 32 # pixel width
h = 8 # pixel height

# setup the port and LED device
serial = spi(port=0, device=0, gpio=noop())
device = led(serial,
			 cascaded=n,
			 block_orientation=block_orientation,
			 rotate=rotate,
			 blocks_arranged_in_reverse_order=inreverse)
device.contrast(intensity)

# continuosly run the simulation/animation
x = randrange(w); y = randrange(h)
while(True):
	dx = randrange(3) - 1; dy = randrange(3) - 1
	x += dx; y += dy
	if(y < 0):  y = 0
	if(x < 0):  x = 0
	if(x >= w):	x = w - 1
	if(y >= h):	y = h - 1
		
	with canvas(device) as draw:
		draw.point((x, y), fill=True)
		
	time.sleep(delay)
