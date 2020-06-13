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
import os
import sys
import json
import logging
import socket
from time import sleep
import argparse
import ultrametrics_rpi as umr

logging.basicConfig(level=logging.INFO)

def sense_fifo(w, v, l):
    """ Maintains list of sensor readings for graphical trace display.

        :param w: The width of the fifo.
        :type w: int
        :param v: The value to add to the fifo.
        :type v: int
        :param l: The list of values representing the fifo.
        :type l: int
    """
    if(v is not None):
        if(len(l) > w): l.pop(0)
        l.append(v)
    return l

def update(sl, sensor, l, width, lcd, leds, interval):
    """ Generic display and status light update routine, with graphical trace.

        :param sl: the sensor log.
        :param sensor: the sensor.
        :param l: fifo of sensor readings.
        :param width: the size of the fifo (aka width of the trace display).
        :param lcd: the lcd device.
        :param leds: the status leds.
        :param interval: the update interval in seconds.
    """
    name = sensor['name']
    px = sensor['preferred_index'] if('preferred_index' in sensor) else 0 
    for i in range(sensor['repeat']):
        try:
            # evaluate the functions and store the returned values
            v = list(map(eval, sensor['funcs']))
            # update the graphical trace
            l = sense_fifo(width, v[px], l) if sensor['trace'] else None
        except Exception as e:
            v = [None]
            leds.light('red')
            logging.error('Exception: ' + str(e))
        if(sensor['display']):
            if(None in v):
                lcd.display(name + ':\nNone', trace=None)
            else:
                # display the result from the 'preferred' function 
                lcd.display(name + ':\n' + sensor['formats'][px] % v[px] +
                            ' %s' % sensor['units'][px], trace=l)
                # update the status leds, buzzers and notifier
                if('thresholds' in sensor):
                    t0 = sensor['thresholds'][0] * sensor['baseline']
                    t1 = sensor['thresholds'][1] * sensor['baseline']
                    leds.light_threshold(v[px], t0, t1, buzz=sensor['buzz'])
        sleep(interval)
    leds.clear()

    # log all values
    if(sensor['log'] and v is not None and not None in v):
        sl.write(name, tuple(v), ', '.join(sensor['formats']))
    
    return(l)

def main(width, height, sl, lcd, leds, buzzer, sensors, interval):
    """ Main control: generic display, status lights and graphical trace.
    """
    traces = [[] for x in range(len(sensors))]
    while(True):
        for i, a in enumerate(sensors):
            traces[i] = update(sl, sensors[a], traces[i], width,
                               lcd, leds, interval)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='sensor_panel arguments',
                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    # arguments
    parser.add_argument('--sensor-config', type=str, 
                        help='The file to read sensor configuration from')
    parser.add_argument('--display', type=str, default='dummy',
        choices=['ssd1306', 'lcd1602', 'ili9341', 'max7219', 'dummy'],
                        help='The type of device for displaying info messages')
    parser.add_argument('--rotate', type=int, default=0,
                        choices=[0, 1, 2, 3],
                        help='The amount to rotate the display.')
    parser.add_argument('--width', type=int, default=128,
                        help='The width of the display in pixels')
    parser.add_argument('--height', type=int, default=32,
                        help='The height of the display in pixels')
    parser.add_argument('--trace-height', type=int, default=16,
                        help='The height of the data trace in pixels')
    parser.add_argument('--trace-color', type=str, default='yellow',
                        help='The color of the data trace')
    parser.add_argument('--color', type=str, default='white',
                        help='The color of text')
    parser.add_argument('--interval', type=float, default=1.0,
                        help='The display update interval in seconds.')
    parser.add_argument('--adc-addr', type=str, 
                        help='Hex I2C address of the a/d converter, e.g. 0x48')
    parser.add_argument('--dht11', type=int, 
                        help='The data pin of the dht11 in BCM')
    parser.add_argument('--bme280-addr', type=str, 
                        help='Hex I2C address of the bme280. e.g. 0x76')
    parser.add_argument('--buzzer-type', type=str, 
                        choices=['active', 'passive'],
                        help='The type of buzzer.')
    parser.add_argument('--buzzer-pin', type=int,
                        help='The control pin for the buzzer.')
    parser.add_argument('b', type=int, 
                        help='The signal pin to the first status led in BCM')
    parser.add_argument('g', type=int, 
                        help='The signal pin to the second status led in BCM')
    parser.add_argument('y', type=int, 
                        help='The signal pin to the third status led in BCM')
    parser.add_argument('r', type=int, 
                        help='The signal pin to the last status led in BCM')

    args = parser.parse_args()

    # buzzer
    if(args.buzzer_type == 'passive'):
        buzzer = umr.PassiveBuzzer(args.buzzer_pin)
    elif(args.buzzer_type == 'active'):
        buzzer = umr.ActiveBuzzer(args.buzzer_pin)
    else:
        buzzer = umr.DummyBuzzer()

    # LED wiring - colors and their associated pins
    # status_leds() expects the pins to be in order of increasing 'severity'
    colorpins = { 'blue': args.b, 'green': args.g,
                  'yellow': args.y, 'red': args.r }
    leds = umr.StatusLeds(colorpins, buzzer=buzzer)

    # display
    width, height, rotate = args.width, args.height, args.rotate
    tr_h, tr_c = args.trace_height, args.trace_color
    display_type = args.display.lower()
    if(display_type == 'lcd1602'):
        lcd = umr.LCD1602Display(echo=False)
    elif(display_type == 'ssd1306'):
        from PIL import ImageFont
        text_h = int((height - tr_h) / 3)
        font = None
        fp = os.path.dirname(sys.argv[0]) + '/../fonts'
        font = ImageFont.truetype(fp + '/pixelmix.ttf', text_h)
        lcd = umr.SSD1306Display(width, height, rotate=rotate,
                                 font=font, echo=False)
    elif(display_type == 'ili9341'):
        from PIL import ImageFont
        color = args.color      
        fp = os.path.dirname(sys.argv[0]) + '/../fonts'
        font = ImageFont.truetype(fp + '/Volter__28Goldfish_29.ttf', 32)
        lcd = umr.ILI9341Display(width, height, rotate=rotate,
                                 trace_height=tr_h, trace_color=tr_c,
                                 color=color,
                                 font=font,
                                 echo=False)
    elif(display_type =='max7219'):
        from PIL import ImageFont
        fp = os.path.dirname(sys.argv[0]) + '/../fonts'
        font = ImageFont.truetype(fp + '/ProggyTiny.ttf', 8)
        lcd = umr.MAX7219Display(width, height, rotate=rotate,
                                 font=font,
                                 echo=False)
    else:
        lcd = umr.DummyDisplay()

    lcd.display('initializing.. ')
    
    # write sensor readings to file
    sl = umr.SensorLog('sensor_panel_%s.out' % umr.System.get_hostname())

    # a/d converter, if attached
    # note: ads is used dynamically, if referenced in sensor_config*.json
    if(args.adc_addr is not None):
        ads = umr.ADS1115(args.adc_addr)
    
    # DHT11 or BME280, if attached
    # note: tsense is used dynamically, if referenced sensor_config*.json
    if(args.dht11 is not None):
        tsense = umr.DHT11(args.dht11)
    elif(args.bme280_addr is not None):
        tsense = umr.BME280(int(args.bme280_addr, 16))

    # the sensor panel
    try:
        interval = args.interval
        lcd.display('running.. ')
        with open(args.sensor_config) as jsonfile:
            sensors = json.load(jsonfile)
        main(width, height, sl, lcd, leds, buzzer, sensors, interval)
    except KeyboardInterrupt:
        leds.clear()
        lcd.destroy()
        leds.destroy()
        buzzer.destroy()


