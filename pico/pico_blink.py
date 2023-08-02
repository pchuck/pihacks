# micropython for Raspberry Pi Pico
#
# flash the onboard LED
#
import machine
import utime
led_onboard = machine.Pin(25, machine.Pin.OUT)
while True:
    led_onboard.toggle()
    utime.sleep(1)
