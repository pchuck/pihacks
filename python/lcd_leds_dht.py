#!/usr/bin/env python3
#
# Status panel using LCD1602 (w/PCF8574 i2c), GPIO driven LED's and
# DHT humidity temperature sensor to continually display information
# about the system, health and its ambient environment.
#
# note: requires adafruit-circuitpython-dht, not Adafruit_DHT, also libgpiod2
# (pin numbering is BOARD not BCM, one of the included libs is overriding)
#
import logging
from time import sleep
import socket
import argparse
import ultrametrics_rpi as umr

DTIME=1 # number of seconds between sensor readings
PTIME=10 # number of dtimes to persist each sensor screen

logging.basicConfig(level=logging.INFO)

# get current ip for later comparison in runtime checks
def get_ip():
    return socket.gethostbyname(socket.gethostname())

# update time display and status lights
def update_time():
    lcd.display(umr.System.get_time())
    leds.light('blue')
    sleep(PTIME * DTIME) ; leds.clear()

# update hostname and ip display
def update_hostname():
    hostname = umr.System.get_hostname()
    try:
        ip = umr.System.get_ip()
        if(ip == expected_ip):
            leds.light('green')
        else:
            leds.light('red') # flag red if ip unexpected
        lcd.display('host: ' + hostname + 'ip: ' + ip)
    except socket.gaierror: 
        leds.light('red') # flag red if gethostbyname fails
        lcd.display('host: ' + hostname + '\nip: (gaierror)')
    sleep(PTIME * DTIME) ; leds.clear()

# update system uptime display and status lights
def update_uptime():
    (d, h, m, s) = umr.System.get_uptime()
    lcd.display('uptime: \n%dd %02d:%02d:%02d' % (d, h, m, s))
    leds.light('blue'); sleep(PTIME * DTIME) ; leds.clear()

# update temperature and humidity display and status lights
def update_th(tf, h):
    if(tf is not None and h is not None):
        leds.light_threshold(tf, 85, 95)
        leds.light_threshold(h, 60, 90)
        lcd.display('ambient: %.1f F\nhumidity: %.1f' % (tf, h))
    else:
        leds.light('red')
        lcd.display('ambient: Err\nhumidity: Err')
    sleep(DTIME * PTIME) ; leds.clear()

# maintain list 'l' of sensor readings 'v', always length 'w' for displaying
def sense_fifo(w, v, l):
    if(v is not None):
        if(len(l) > w): l.pop(0)
        l.append(v)
    return l

# generic display and status light update routine, with graphing
def update(func, name, sformat, l, low, high, clear=True):
    for i in range(PTIME):
        v = func()
        l = sense_fifo(args.width, v, l)
        if(v is None):
            lcd.display(name + ': Err')
        else:
            lcd.display(name + ': ' + sformat % v, l)
            leds.light_threshold(v, low, high);
        sleep(DTIME)
        if(clear):
            leds.clear()
            
    return(v, l)

# main
def main(fld, lcd, leds, dht, expected_ip):
    l1s, tcs, tgs, tfs, hs = [], [], [], [], []
    while(True):
        # no graphing, simple update for these
        update_time()
        update_hostname()
        update_uptime()

        # load
        (l1, l1s) = update(umr.System.get_load1, 'load', '%2.2f', l1s,
                           1.5, 3.0, clear=False)
        fld.display_formatted('load', '%2.2f', l1)
        leds.clear()

        # cpu
        (tc, tcs) = update(umr.System.get_cpu_temp, 'cpu', '%.1f C', tcs,
                           60, 75, clear=False)
        fld.display_formatted('cpu', '%.1f', tc)
        leds.clear()

        # gpu
        (tg, tgs) = update(umr.System.get_gpu_temp, 'gpu', '%.1f C', tgs,
                           65, 80, clear=False)
        fld.display_formatted('gpu', '%.1f', tg)
        leds.clear()

        # no graphing for t and h
        (tc, tf, h) = dht.sense_data()
        update_th(tf, h)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='lcd_leds_dht arguments',
                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    # arguments
    parser.add_argument('--display', type=str, default='dummy',
        choices=['ssd1306', 'lcd1602', 'dummy'],
        help='The type of device for displaying info messages')
    parser.add_argument('--width', type=int, default=128,
                        help='The width of the display in pixels')
    parser.add_argument('--height', type=int, default=32,
                        help='The height of the display in pixels')
    parser.add_argument('d', type=int, 
        help='The data pin of the dht11 in BCM')
    parser.add_argument('b', type=int, 
        help='The signal pin to the first status led in BCM')
    parser.add_argument('g', type=int, 
        help='The signal pin to the second status led in BCM')
    parser.add_argument('y', type=int, 
        help='The signal pin to the third status led in BCM')
    parser.add_argument('r', type=int, 
        help='The signal pin to the last status led in BCM')

    args = parser.parse_args()

    # LED wiring - colors and their associated pins
    # status_leds() expects the pins to be in order of increasing 'severity'
    colorpins = {
        'blue': args.b,
        'green': args.g,
        'yellow': args.y,
        'red': args.r
    }

    # DHT wiring - GPIO bcm
    DHT_PIN = args.d

    # set the display output
    display_type = args.display.lower()
    if(display_type == 'lcd1602'):
        lcd = umr.LCD1602Display(echo=False)
    elif(display_type == 'ssd1306'):
        lcd = umr.SSD1306Display(echo=False)
    else:
        lcd = umr.DummyDisplay()

    # write sensor readings to file
    fld = umr.FileDisplay('lcd_leds_dht_sensor.out')
    
    lcd.display('initializing.. ')
    leds = umr.StatusLeds(colorpins)
    dht = umr.DHT11(DHT_PIN)

    try:
        lcd.display('running.. ')
        expected_ip = get_ip()
        main(fld, lcd, leds, dht, expected_ip)
    except KeyboardInterrupt:
        leds.clear()
        lcd.destroy()

