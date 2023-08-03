# micropython for Raspberry Pi Pico
#
# pico_blink.py - onboard LED flasher. minimal pico app.
#
import machine
import utime
led_onboard = machine.Pin(25, machine.Pin.OUT)
while True:
    led_onboard.toggle()
    utime.sleep(1)
