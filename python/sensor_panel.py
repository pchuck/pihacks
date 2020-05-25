#!/usr/bin/env python3
#
# sensor_panel.py
#
# Controller for a continuously updating status panel.
#
# Uses the ultrametrics library to drive components, including
# a set of status LED's and LCD or OLED display, based on readings from
# an array of sensors (system and/or GPIO input driven).
#
# In its current configuration:
#   reads from system metrics and a DHT humidity/temperature sensor
#   outputs text readings and graphical traces an LCD1602 or SSD1306 display
#   updates status LED's based on sensor readings thresholds
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
#
import logging
from time import sleep
import socket
import argparse
import ultrametrics_rpi as umr

DTIME=1 # number of seconds between sensor readings
PTIME=10 # number of dtimes to persist each sensor screen

logging.basicConfig(level=logging.INFO)

def update_time():
    """ Update time display and status lights.
    """
    lcd.display(umr.System.get_time())
    leds.light('blue')
    sleep(PTIME * DTIME) ; leds.clear()

def update_hostname():
    """ Update hostname and ip display.
    """
    hostname = umr.System.get_hostname()
    try:
        ip = umr.System.get_ip()
        if(ip == expected_ip):
            leds.light('green')
        else:
            leds.light('red') # flag red if ip unexpected
        lcd.display('host: ' + hostname + '\nip: ' + ip)
    except socket.gaierror: 
        leds.light('red') # flag red if gethostbyname fails
        lcd.display('host: ' + hostname + '\nip: (gaierror)')
    sleep(PTIME * DTIME) ; leds.clear()

def update_uptime():
    """ Update system uptime display and status lights.
    """
    (d, h, m, s) = umr.System.get_uptime()
    lcd.display('uptime: \n%dd %02d:%02d:%02d' % (d, h, m, s))
    leds.light('blue'); sleep(PTIME * DTIME) ; leds.clear()

def update_th(tf, h):
    """ Update temperature and humidity display and status lights.
    """
    if(tf is not None and h is not None):
        leds.light_threshold(tf, 85, 95)
        leds.light_threshold(h, 60, 90)
        lcd.display('ambient: %.1f F\nhumidity: %.1f' % (tf, h))
    else:
        leds.light('red')
        lcd.display('ambient: Err\nhumidity: Err')
    sleep(DTIME * PTIME) ; leds.clear()

def sense_fifo(w, v, l):
    """ Maintain list of sensor readings for graphical trace display.
    """
    if(v is not None):
        if(len(l) > w): l.pop(0)
        l.append(v)
    return l

def update(func, name, sformat, l, low, high, clear=True):
    """ Generic display and status light update routine, with graphical trace.
    """
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


def main(fld, lcd, leds, dht, expected_ip):
    """ Main control: generic display, status lights and graphical trace.
    """
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
    parser = argparse.ArgumentParser(description='sensor_panel arguments',
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
    fld = umr.FileDisplay('sensor_panel_dht.%s.out' % umr.System.get_hostname())
    
    lcd.display('initializing.. ')
    leds = umr.StatusLeds(colorpins)
    dht = umr.DHT11(DHT_PIN)

    try:
        lcd.display('running.. ')
        expected_ip = umr.System.get_ip()
        main(fld, lcd, leds, dht, expected_ip)
    except KeyboardInterrupt:
        leds.clear()
        lcd.destroy()

