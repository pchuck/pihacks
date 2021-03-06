#!/usr/bin/env python3
#
# led_swarm_luma.py
#
# A python script for animating a 'swarm' of lights on a raspberry pi
# using luma to drive an LED screen or matrix connected via i2c or spi.
# Examples include the max7219 or ssd1306.
#
# The swarm consists of a specified number of elements, each with its own
# position and velocity. With each iteration, velocities are perturbed
# using brownian motion which randomly increments or decrements the
# velocity of the element, changing its trajectory and position on the display
# to produce a fluid and natural looking animation.
#
# Run with '--help' to see the many options related to your specific panel(s),
# setup, resolution, orientation, etc.
#
# Typical SPI to RPi GPIO matrix wiring (e.g. MAX7219)
#   p1 VCC -> RPi p2 5V0
#   p2 GND -> RPi p6 GND
#   p3 DIN -> RPi p19 GPIO 10 (MOSI)
#   p4 CS  -> RPi p24 GPIO 8 (SPI CE0)
#   p5 CLK -> RPi p23 GPIO 11 (SPI CLK)
#
# Typical SPI to RPi GPIO lcd wiring (e.g. ILI9341)
#   p1 VCC  -> RPi p1 3V3
#   p2 GND  -> RPi p6 GND
#   p3 CS   -> RPi p24 GPIO 8 (SPI CE0)
#   p4 RST  -> RPi p18 GPIO 24 (was 22, but not available via hat)
#   p5 DC   -> RPi p16 GPIO 23
#   p6 MOSI -> RPi p19 GPIO 10 (MOSI)
#   p7 SCK  -> RPi p23 GPIO 11 (SCLK)
#   p8 LED  -> RPi p22 GPIO 25 (was 18, conflicted w/ audio injector)
#   p9 MISO -> RPi p21 GPIO 10 (MISO) 
# note: without support for touchscreen, leave MISO disconnected.
#
# Typical I2C to RPi GPIO wiring (e.g. SSD1306)
#   p1 GND  -> RPi p6 GND
#   p2 VCC  -> RPi p2 5V0
#   p3 SCK  -> RPi p5 SCL.1
#   p4 SDA  -> RPi p3 SDA.1
# 
# This version uses the luma libraries: luma.core, luma.led-matrix
# For the SSD1306, luma.oled is also required.
# For the ILI9341, luma.lcd is also required.
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
# This renderer is specific to the luma max7219 driver, namely
# in the canvas/draw/point primitive syntax.
#
class FireflyRendererLed_Luma(object):
    def __init__(self, device, bounds, fireflies, color):
        self.device = device
        self.color = color
        self.ffs = fireflies
        for firefly in self.ffs.flies:
            firefly.p = Point(randrange(bounds.x), randrange(bounds.y))

    # render everything on the canvas
    def render(self):
        with canvas(self.device) as draw:
            for firefly in self.ffs.flies:
                draw.point(firefly.p, fill=self.color)

# init_device
#
# initialize and return the new device handle
#
def init_device(device, device_id,
                n, block_orientation, rotate, inreverse, intensity):
    # max7219, via SPI
    if(device.lower() == 'max7219'):
        from luma.core.interface.serial import spi, noop
        from luma.led_matrix.device import max7219 as led
        
        serial = spi(port=0, device=device_id, gpio=noop())
        device = led(serial, cascaded=n, block_orientation=block_orientation,
                     rotate=rotate, blocks_arranged_in_reverse_order=inreverse)
        device.contrast(intensity)

    # ili9341, via SPI
    elif(device.lower() == 'ili9341'):
        from luma.core.interface.serial import spi, noop
        from luma.lcd.device import ili9341 as lcd
        serial = spi(port=0, device=device_id, gpio_DC=23, gpio_RST=24,
                     bus_speed_hz=32000000)
        device = lcd(serial, gpio_LIGHT=25, active_low=False)
        # , pwm_frequency=50) # this appears to be broken
        device.backlight(True)
        device.clear()

    # ssd1306, via I2C
    elif(device.lower() == 'ssd1306'): 
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306 as led
       
        serial = i2c(port=1, address=0x3C)
        device = led(serial)

    else:
        sys.exit('unsupported display device: ' + device)

    return device

# swarm
#
# initiate the device and orchestrate the swarm animation 
#
def swarm(device, bounds, count, maxv, varyv, delay, color):
    # create the fireflies and renderer
    ffs = Fireflies(bounds, count, maxv, varyv)
    renderer = FireflyRendererLed_Luma(device, bounds, ffs, color)
    while(True):
        deque(map(lambda firefly: firefly.move(), ffs.flies))
        renderer.render()
        time.sleep(delay)


## argument parsing
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='led_swarm arguments',
                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # hardware constants
    parser.add_argument('--device', '-dv', type=str, default='max7219',
        choices=['max7219', 'ssd1306', 'ili9341'],
        help='The type of device')
    parser.add_argument('--device-id', '-di', type=int, default=0,
        help='The SPI device id (e.g. CE0, CE1) to address.')
    parser.add_argument('--cascaded', '-n', type=int, default=1,
        help='Number of cascaded LED matrices (usu. max7219)')
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
    parser.add_argument('--max-x-velocity', '-mvx', type=int, default=2, 
        help='The maximum member x velocity')
    parser.add_argument('--max-y-velocity', '-mvy', type=int, default=1, 
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
        device = init_device(args.device, args.device_id,
                             args.cascaded, args.block_orientation,
                             args.rotate, args.reverse_order, args.intensity)

        swarm(device, 
              Point(args.x, args.y),
              args.members,
              Point(args.max_x_velocity, args.max_y_velocity),
              args.vary_v,
              args.delay,
              args.color)

    except KeyboardInterrupt:
        pass

##
