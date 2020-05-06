#!/usr/bin/env python3
#
# led_swarm_af.py
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
# Typical max2719 to RPi GPIO wiring:
#   p1 VCC -> RPi p2 5V0
#   p2 GND -> RPi p6 GND
#   p3 DIN -> RPi p19 GPIO 10 (MOSI)
#   p4 CS ->  RPi p24 GPIO 8 (SPI CE0)
#   p5 CLK -> RPi p23 GPIO 11 (SPI CLK)
#
# This version uses the adafruit libraries:
#   adafruit-circuitpython-max7219, adafruit-circuitpython-framebuf
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
#
import sys, os
import time
from random import randrange
import argparse
from collections import deque
from adafruit_max7219 import matrices
from board import SCLK, CE0, MOSI
import busio
import digitalio

clk = SCLK
din = MOSI
cs = digitalio.DigitalInOut(CE0)


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
class FireflyRendererLed_AF(object):
	def __init__(self, canvas, device, bounds, fireflies, color, **kwargs):
		self.canvas = canvas
		self.device = device
		self.color = color
		self.ffs = fireflies
		for firefly in self.ffs.flies:
			firefly.p = Point(randrange(bounds.x), randrange(bounds.y))
			
	# render everything on the canvas
	def render(self):
		self.device.fill(0)
		for firefly in self.ffs.flies:
			self.device.pixel(firefly.p.x, firefly.p.y, 1)
		self.device.show()

			
# swarm
#
# initiate the device and orchestrate the swarm animation 
#
def swarm(intensity, bounds, count, maxv, varyv, delay, color, **kwargs):

	# setup the port and LED device
	serial = busio.SPI(clk, MOSI=din)
	device = matrices.Matrix8x8(serial, cs)
	device.brightness(intensity)
	device.fill(0)
        
	ffs = Fireflies(bounds, count, maxv, varyv)
	canvas = None
	renderer = FireflyRendererLed_AF(canvas, device, bounds, ffs, color,
                                         **kwargs)
	while(True):
		deque(map(lambda firefly: firefly.move(), ffs.flies))
		renderer.render()
		time.sleep(delay)
	

## argument parsing
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='led_swarm arguments',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

	# hardware constants
	parser.add_argument('--intensity', '-i', type=int, default=5,
		help='The intensity of the LED output (from 0..10)')
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
		swarm(args.intensity,
			  Point(args.x, args.y),
			  args.members, 
 			  Point(args.max_x_velocity, args.max_y_velocity),
			  args.vary_v,
		      args.delay,
			  args.color)

	except KeyboardInterrupt:
		pass

##
