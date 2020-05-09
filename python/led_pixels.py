#!/usr/bin/env python3
#
# led_pixels.py
#
# A simpler version of led_swarm.
# Requires a Raspberry pi with MAX7219 LED wired to GPIO contacts.
#
# This script applies brownian motion to element positions.
# Parameters are configurable in the block 'constants' below.
#
# See led_swarm.py for the more generic, and complex, script
# that is parameterized and uses brownian motion to vary element velocity.
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
#
import time
from random import randrange
from collections import namedtuple
from luma.core.interface.serial import spi, noop
from luma.led_matrix.device import max7219 as led
from luma.core.render import canvas

# Points have an x/y component (used for coordinates, dimensions)
Point = namedtuple('point', 'x y') 


## constants

n = 4 # number of led panels/blocks
rotate = 0 # rotation of individual blocks (0=0°, 1=90°, 2=180°, 3=270°)
block_orientation = 90 # in degrees, for horiz vs. vert arrangement of blocks
inreverse = True # if blocks are wired in reverse
intensity = 16 # led intensity, scale of 0..255
delay = 0.05 # refresh delay (in seconds)
dimensions = Point(32, 8) # canvas dimensions
zero = Point(0, 0) # canvas min/zero point
point_count = 12 # number of elements to animate


# functions

# Generate an array containing count random point x/y tuples
# within the bounds of the canvas dimensions 'dim'.
def generate_points(dim, count):
    points = []
    for i in range(count):
        p = Point(randrange(dim.x), randrange(dim.y))
        points.append(p)

    return(points)

# Fix provided point 'p' so that it is with min and max bounds.
def bound_point(minp, maxp, p):
    if(p.x < minp.x):  p = Point(minp.x, p.y)
    if(p.x >= maxp.x): p = Point(maxp.x - 1, p.y)
    if(p.y < minp.y):  p = Point(p.x, minp.y)
    if(p.y >= maxp.y): p = Point(p.x, maxp.y - 1)

    return p

# Given canvas dimensions and a point, perturb the point's x/y location.
def update_point(dim, p):
    delta = Point(randrange(3) - 1, randrange(3) - 1)
    p = bound_point(zero, dim, Point(p.x + delta.x, p.y + delta.y))

    return(p)

# Given canvas dimensions and a set of points, generate a new set of points.
def update_points(dim, points):
    new_points = []
    for p in points:
        new_points.append(update_point(dim, p))

    return(new_points)


## main
def main():
    # setup the LED port and device
    serial = spi(port=0, device=0, gpio=noop())
    device = led(serial, cascaded=n,
                 block_orientation=block_orientation,
                 rotate=rotate,
                 blocks_arranged_in_reverse_order=inreverse)
    device.contrast(intensity)

    # generate points
    points = generate_points(dimensions, point_count)

    # animate
    while(True):
        points = update_points(dimensions, points)
        with canvas(device) as draw:
            for p in points:
                draw.point(p, fill='White') # fill='color')

        time.sleep(delay)

main()

