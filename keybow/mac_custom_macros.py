# Keybow 2040, or similar, control script
# Customizable map, supporting both keycodes and string macros
#
# derived from:
#   SPDX-FileCopyrightText: 2021 Sandy Macdonald
#   SPDX-License-Identifier: MIT
#
# prerequisites: 
#   requires the adafruit_hid CircuitPython, in CIRCUITPY/lib/
#
# installation: 
#   replace the contents of CIRCUITPY/code.py with this file
#
import board
from keybow2040 import Keybow2040

import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode

# setup
i2c = board.I2C()
keybow = Keybow2040(i2c)
keys = keybow.keys

# keyboard and layout
keyboard = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(keyboard)

# macros
MESSAGE = "test!"
# toggle different desktops
DESKTOP_1 = (Keycode.CONTROL, Keycode.ONE)
DESKTOP_2 = (Keycode.CONTROL, Keycode.TWO)
DESKTOP_3 = (Keycode.CONTROL, Keycode.THREE)
DESKTOP_4 = (Keycode.CONTROL, Keycode.FOUR)

# Sequentially mapped keycodes, associated with keys 0-15
# Replace these with Keycode tuples or strings
keymap = {
    0: MESSAGE,
    1: "one",
    2: "two",
    3: DESKTOP_1,
    4: "four",
    5: "five",
    6: "six",
    7: DESKTOP_2,
    8: "eight",
    9: "nine",
   10: "ten",
   11: DESKTOP_3,
   12: "twelve",
   13: "thirteen",
   14: "fourteen",
   15: DESKTOP_4
}

# default colour to set the keys when pressed
rgb = (255, 255, 0)

# key press handler
for key in keys:
    @keybow.on_press(key)
    def press_handler(key):
        keycodes = keymap[key.number]
        # send as keycodes or a string, depending on the type
        if isinstance(keycodes, tuple):
            keyboard.send(*keycodes)
        else:
            layout.write(keycodes)
        # set the color
        key.set_led(*rgb)

    # release handler - turn off the LED
    @keybow.on_release(key)
    def release_handler(key):
        key.led_off()

# update
while True:
    keybow.update()
