#!/usr/bin/python3
#
# led_swarm.py
#
# A python script for animating a 'swarm' of lights on a raspberry pi
# with max2719 or other similar LED matrix display connected via gpio.
#
# Requires a Raspberry pi with an LED matrix/matrices addressed via GPIO.
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
import time
import argparse
from random import randrange
from collections import namedtuple
from luma.core.interface.serial import spi, noop
from luma.led_matrix.device import max7219 as led
from luma.core.render import canvas

# points have an x/y location or component (used for coordinates, dimensions)
Point = namedtuple('point', 'x y')
# vpoints have a location and a velocity (used for moving swarm elements)
VPoint = namedtuple('vpoint', 'x y dx dy')

# generate an array containing count random point x/y and dx/dy velocity tuples,
# within the bounds of the canvas dimensions 'dim'
def generate_vpoints(dim, count):
	vpoints = []
	for i in range(count):
		# random locations on the canvas with zero initial velocity
		vp = VPoint(randrange(dim.x), randrange(dim.y), 0, 0)
		vpoints.append(vp)

	return(vpoints)

# fix provided point 'p' so that it is within min and max bounds
# works on 'point' objects that have an x/y component (position, velocity, etc)
def bound_velocity(minp, maxp, p):
	if(p.x < minp.x): p = Point(minp.x, p.y)
	if(p.x > maxp.x): p = Point(maxp.x, p.y)
	if(p.y < minp.y): p = Point(p.x, minp.y)
	if(p.y > maxp.y): p = Point(p.x, maxp.y)

	return p

# fix provided vpoint 'vp' so that it is within min and max bounds.
# prevents the x and y coordinates from leaving the bounded region, and
# inverts v when outside the boundary, so points 'bounce' rather than stick.
# note: since screen coordinates are 0..max-1, adjusts accordingly.
def bound_vpoint(minp, maxp, vp):
	if(vp.x <  minp.x): vp = VPoint(minp.x,     vp.y,      -vp.dx,  vp.dy)
	if(vp.x >= maxp.x): vp = VPoint(maxp.x - 1, vp.y,      -vp.dx,  vp.dy)
	if(vp.y <  minp.y): vp = VPoint(vp.x,       minp.y,     vp.dx, -vp.dy)
	if(vp.y >= maxp.y): vp = VPoint(vp.x,       maxp.y - 1, vp.dx, -vp.dy)

	return vp

# given canvas dimensions, maximum allowed velocity and a vpoint
# (including its position and velocity components)
# randomly perturb the point's velocity, calculate its new location
# and return the new updated vpoint
def update_vpoint(dim, maxv, vp):
	zero = Point(0, 0)
	d = Point(randrange(3) - 1, randrange(3) - 1) # random delta
	v = Point(vp.dx + d.x, vp.dy + d.y) # apply random delta to current velocity
	nmaxv = Point(-maxv.x, -maxv.y) # maximum negative velocity
	v = bound_velocity(nmaxv, maxv, v) # bound velocity between neg and pos max
	vp = VPoint(vp.x + v.x, vp.y + v.y, v.x, v.y) # apply the velocity
	vp = bound_vpoint(zero, dim, vp) # bound the position component

	return(vp)

# given canvas dimensions, maximum allowed velocity and a set of vpoints,
# update all the points and velocities (see update_vpoint())
def update_vpoints(dim, maxv, vpoints):
	new_vpoints = []
	for vp in vpoints:
		new_vpoints.append(update_vpoint(dim, maxv, vp))
		
	return(new_vpoints)


##
## swarm
##
def swarm(n, block_orientation, rotate, inreverse, intensity,
		  x, y, maxvx, maxvy, 
		  members, color, delay):
	
	dimensions = Point(x, y) # max canvas dimensions, x and y
	maxv = Point(maxvx, maxvy) # maximum member velocity, x and y components
	
	# setup the LED port and device
	serial = spi(port=0, device=0, gpio=noop())
	device = led(serial,
			     cascaded=n,
				 block_orientation=block_orientation,
				 rotate=rotate,
				 blocks_arranged_in_reverse_order=inreverse)
	device.contrast(intensity)

	# generate intial points/velocities
	vpoints = generate_vpoints(dimensions, members)

	# continuously update and animate
	while(True):
		vpoints = update_vpoints(dimensions, maxv, vpoints)
		with canvas(device) as draw:
			for vp in vpoints:
				# extract only the current position for drawing
				p = Point(vp.x, vp.y) 
				draw.point(p, fill=color)
		time.sleep(delay)

# line version
#	while(True):
#		vps_new = update_vpoints(dimensions, maxv, vpoints)
#		with canvas(device) as draw:
#			for i in range(len(vpoints)):
#				v1 = Point(vpoints[i].x, vpoints[i].y) # old position
#				v2 = Point(vps_new[i].x, vps_new[i].y) # new position
#				draw.line([v1, v2], fill='White') # fill='color')
#			vpoints = vps_new
#		time.sleep(delay)


## argument parsing
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='led_swarm arguments',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

	# hardware constants
	parser.add_argument('--cascaded', '-n', type=int, default=1,
        help='Number of cascaded MAX7219 LED matrices')
	parser.add_argument('--block-orientation', type=int, default=0,
		choices=[0, 90, -90],
		help='Corrects block orientation when wired vertically')
	parser.add_argument('--rotate', type=int, default=0,
		choices=[0, 1, 2, 3],
		help='Rotate display 0=0°, 1=90°, 2=180°, 3=270°')
	parser.add_argument('--reverse-order', type=bool, default=False,
		help='Set to true if blocks are in reverse order')
	parser.add_argument('--intensity', type=int, default=128,
		help='The intensity of the LED output (from 0..255)')
	parser.add_argument('--max-x-velocity', '-maxvx', type=int, default=2, 
		help='The maximum member x velocity')
	parser.add_argument('--max-y-velocity', '-maxvy', type=int, default=1, 
		help='The maximum member y velocity')
	parser.add_argument('x', type=int, # required!
		help='The x resolution of the matrix')
	parser.add_argument('y', type=int, # required!
		help='The y resolution of the matrix')

	# feature arguments
	parser.add_argument('members', type=int, 
		help='The number of members in the swarm (try 1..100)')
	parser.add_argument('--color', type=str, default='White',
		help='The color to use')
	parser.add_argument('--delay', type=float, default=0.1,
		help='The delay (in seconds) between iterations')

	args = parser.parse_args()
	
	try:
		swarm(args.cascaded, args.block_orientation,
			 args.rotate, args.reverse_order, args.intensity,
			 args.x, args.y, args.max_x_velocity, args.max_y_velocity,
			 args.members, args.color, args.delay)
		
	except KeyboardInterrupt:
		pass

##
