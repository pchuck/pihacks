#!/usr/bin/env python3
#
# led_swarm.py
#
# A python script for animating a 'swarm' of lights on a raspberry pi
# with max2719 or other similar LED matrix display connected via gpio.
#
# The swarm consists of a specified number of elements, each with its own
# position and velocity. With each iteration, velocities are perturbed
# using brownian motion which randomly increments or decrements the
# velocity of the element, changing its trajectory and position on the display
# to produce a fluid and natural looking animation.
#
# Run with '--help' to see the many options related to your specific
# max2719 panel(s) setup, resolution, orientation, etc.
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
#
import sys, os
import time
from random import randrange
import argparse
from luma.core.interface.serial import spi, noop
from luma.led_matrix.device import max7219 as led
from luma.core.render import canvas


# load Firefly primitives
pathname = os.path.dirname(sys.argv[0])        
fullpath = os.path.abspath(pathname)
exec(compile(source=open(fullpath + '/fireflies.py').read(),
			 filename='fireflies.py', mode='exec'))


# FireflyRenderer
#
# Encapsulates all rendering, including the graphics context and/or canvas.
# When fireflies positions have changed, or the canvas changed,
# render() is called to update the visual representation.
#
# This renderer is specific to the max2719 driver
#
class FireflyRendererLed(object):
	def __init__(self, canvas, device, bounds, fireflies, color, **kwargs):
		self.canvas = canvas
		self.device = device
		self.color = color
		self.ffs = fireflies
		for firefly in self.ffs.flies:
			firefly.p = Point(randrange(bounds.x), randrange(bounds.y))
			
	# render everything on the canvas
	def render(self):
		with self.canvas(self.device) as draw:
			for firefly in self.ffs.flies:
				draw.point(firefly.p, fill=self.color)

			
# swarm
#
# initiate the device and orchestrate the swarm animation 
#
def swarm(n, block_orientation, rotate, inreverse, intensity, bounds,
		  count, maxv, varyv, delay, color, **kwargs):

	# setup the port and LED device 
	serial = spi(port=0, device=0, gpio=noop())
	device = led(serial, cascaded=n, block_orientation=block_orientation,
				 rotate=rotate, blocks_arranged_in_reverse_order=inreverse)
	device.contrast(intensity)
	ffs = Fireflies(bounds, count, maxv, varyv)
	renderer = FireflyRendererLed(canvas, device, bounds, ffs, color, **kwargs)
	while(True):
		for firefly in ffs.flies:
			firefly.move()
		renderer.render()
		time.sleep(delay)
	

## argument parsing
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='led_swarm arguments',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

	# hardware constants
	parser.add_argument('--cascaded', '-n', type=int, default=1,
        help='Number of cascaded MAX7219 LED matrices')
	parser.add_argument('--block-orientation', '-bo', type=int, default=0,
		choices=[0, 90, -90],
		help='Corrects block orientation when wired vertically')
	parser.add_argument('--rotate', '-rot', type=int, default=0,
		choices=[0, 1, 2, 3],
		help='Rotate display 0=0°, 1=90°, 2=180°, 3=270°')
	parser.add_argument('--reverse-order', '-ro', type=bool, default=False,
		help='Set to true if blocks are in reverse order')
	parser.add_argument('--intensity', '-i', type=int, default=128,
		help='The intensity of the LED output (from 0..255)')
	# swarm features
	parser.add_argument('--color', '-c', type=str, default='White',
		help='The color of the swarm members')
	parser.add_argument('--max-x-velocity', '-maxvx', type=int, default=2, 
		help='The maximum member x velocity')
	parser.add_argument('--max-y-velocity', '-maxvy', type=int, default=1, 
		help='The maximum member y velocity')
	parser.add_argument('--vary-v', '-vv', type=bool, default=True,
		help='Set true to allow different max velocities')
	parser.add_argument('--delay','-d', type=float, default=0.1,
		help='The delay (in seconds) between iterations')
	# required positional arguments
	parser.add_argument('x', type=int, # required!
		help='The x resolution of the matrix')
	parser.add_argument('y', type=int, # required!
		help='The y resolution of the matrix')
	parser.add_argument('members', type=int, # required
		help='The number of members in the swarm (try 1..100)')

	args = parser.parse_args()
	
	try:
		swarm(args.cascaded, args.block_orientation,
			 args.rotate, args.reverse_order, args.intensity,
			 Point(args.x, args.y),
			 args.members, 
 			 Point(args.max_x_velocity, args.max_y_velocity),
			 args.vary_v,
		     args.delay,
			 args.color)

	except KeyboardInterrupt:
		pass

##
