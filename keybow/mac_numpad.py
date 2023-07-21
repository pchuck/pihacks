# Keybow 2040, or similar, control script
# Customizable map, supporting both keycodes and string macros
#
# numpad
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

# text macros
M_1 = "one"
M_2 = "two"
M_3 = "three"
# multi-key toggles (desktop switching)
DT_1 = (Keycode.CONTROL, Keycode.ONE)
DT_2 = (Keycode.CONTROL, Keycode.TWO)
DT_3 = (Keycode.CONTROL, Keycode.THREE)
DT_4 = (Keycode.CONTROL, Keycode.FOUR)
DT_5 = (Keycode.CONTROL, Keycode.FIVE)
SPEAK = (Keycode.ALT, Keycode.ESCAPE)
# single-key codes (mini arrow pad)
LEFT  = Keycode.LEFT_ARROW
RGHT  = Keycode.RIGHT_ARROW
UP    = Keycode.UP_ARROW
DOWN  = Keycode.DOWN_ARROW
PLUS  = Keycode.KEYPAD_PLUS
MINUS = Keycode.KEYPAD_MINUS
DIV   = Keycode.KEYPAD_FORWARD_SLASH
MULT  = Keycode.KEYPAD_ASTERISK
BACK  = Keycode.BACKSPACE
PGUP  = Keycode.PAGE_UP
PGDN  = Keycode.PAGE_DOWN
HOME  = Keycode.HOME
END   = Keycode.END
ENTER = Keycode.ENTER
DOT   = Keycode.KEYPAD_PERIOD

# custom macros (assigned in keyboard shortcuts)
F_13   = Keycode.F13
F_14   = Keycode.F14
F_15   = Keycode.F15
F_16   = Keycode.F16
F_17   = Keycode.F17
F_18   = Keycode.F18
# numeric keypad
ZERO   = Keycode.ZERO
ONE    = Keycode.ONE
TWO    = Keycode.TWO
THREE  = Keycode.THREE
FOUR   = Keycode.FOUR
FIVE   = Keycode.FIVE
SIX    = Keycode.SIX
SEVEN  = Keycode.SEVEN
EIGHT  = Keycode.EIGHT
NINE   = Keycode.NINE

# Sequentially mapped keycodes, associated with keys 0-15.
# Layed out onscreen in array matching 4x4 keypad.
# Replace w/ references to Keycode tuples or strings, as desired
keymap = {
    
    3: SEVEN, 7: EIGHT, 11: NINE,   15: MINUS,

    
    2: FOUR,  6: FIVE,  10:  SIX,   14: PLUS,

    
    1: ONE,   5: TWO,    9: THREE,  13: MULT,

    
    0: ZERO,  4: DIV,    8: DOT,   12: ENTER
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
