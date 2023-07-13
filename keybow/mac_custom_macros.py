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
M_1 = "one!"
M_2 = "two"
M_3 = "three!"
# toggle different desktops
DT_1 = (Keycode.CONTROL, Keycode.ONE)
DT_2 = (Keycode.CONTROL, Keycode.TWO)
DT_3 = (Keycode.CONTROL, Keycode.THREE)
DT_4 = (Keycode.CONTROL, Keycode.FOUR)
# mini arrow pad
LEFT  = Keycode.LEFT_ARROW
RGHT = Keycode.RIGHT_ARROW
UP    = Keycode.UP_ARROW
DOWN  = Keycode.DOWN_ARROW
PLUS  = Keycode.KEYPAD_PLUS
# toggle macros
F_13   = Keycode.F13 # stage manager on/off
F_14   = Keycode.F14 # open finder
F_15   = Keycode.F15 # 
F_16   = Keycode.F16 #
F_17   = Keycode.F17 #
F_18   = Keycode.F18 #

# Sequentially mapped keycodes, associated with keys 0-15.
# Layed out onscreen in array matching 4x4 keypad.
# Replace w/ references to Keycode tuples or strings, as desired
keymap = {
    
    3: DT_1,  7: DT_2,  11: DT_3,   15: DT_4,

    
    2: F_14,  6: UP,    10: F_17,   14: M_3,

    
    1: LEFT,  5: F_15,   9: RGHT,   13: PLUS,

    
    0: F_13,  4: DOWN,   8: F_16,   12: M_2
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
        elif isinstance(keycodes, int):
            keyboard.send(keycodes)
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
