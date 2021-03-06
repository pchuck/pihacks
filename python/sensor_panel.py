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
#   reads from system metrics and configured sensors
#   supports a variety of display devices for sensor output and traces.
#   updates status LED's and sends alerts based on sensor readings/ thresholds.
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

def update(sl, sensor, sconfig, l, width, lcd, leds, notifiers, interval, lb):
    """ Generic display and status light update routine, with graphical trace.

        :param sl: the sensor log.
        :param sensor: the sensor 
        :param sconfig: the sensor (panel/display) config.
        :param l: fifo of sensor readings.
        :param width: the size of the fifo (aka width of the trace display).
        :param lcd: the lcd device.
        :param leds: the status leds.
        :param notifiers: notifiers for the sensors
        :param interval: the update interval in seconds.
        :param lb: the line-break character (or '', for single-line display)
    """
    name = sconfig['name']
    # for sensors with both raw and voltage value, px controls which is used
    px = sconfig['preferred_index'] if('preferred_index' in sconfig) else 0
    # repeat controls how long each sensor's info is displayed
    for i in range(sconfig['repeat']):
        try:
            # evaluate the functions and store the returned values
            v = list(map(eval, sconfig['funcs']))
            # update the graphical trace, if it is configured
            if('trace' in sconfig and sconfig['trace']):
                l = sense_fifo(width, v[px], l)
        except Exception as e:
        # if a value can't be retrieved, light led, set value 'None' & continue
            v = [None]
            leds.clear_all(); leds.light('red')
            logging.error('Exception: ' + str(e))
        # if the 'display' is configured, update the display device..
        if(sconfig['display']):
            # short-circuit complex logic and display 'None' if no value
            if(None in v):
                leds.clear_all(); leds.light('red')
                lcd.display(name + (':%sNone' % lb), trace=None)
            else:
                if('percent' in sconfig and sconfig['percent']):
                    # display sensor reading as a percent above/below base
                    # e.g. 'mq135: -17.25% (1.37V)'
                    v_rel = v[px] * 100.0 / sensor.baseline[px] - 100.0
                    lcd.display(sensor.short + ': %+.1f%%%s' % (v_rel, lb) + 
                                sconfig['formats'][px] % v[px] + 
                                ' %s' % sconfig['units'][px], trace=l)
                else:
                    # display sensor reading, e.g. 'mcpu: 63.38 C'
                    # for analog sensors, px selects raw or voltage value.
                    lcd.display(name + ':%s' % lb +
                                sconfig['formats'][px] % v[px] +
                                ' %s' % sconfig['units'][px], trace=l)

                # if aux, display trace there
                if(aux is not None):
                    aux.display_trace(trace=l)
                
                # update the status leds, buzzers and notifier
                if(sensor is not None and sensor.thresholds is not None):
                    ts = [t * sensor.baseline[px] for t in sensor.thresholds]
                    if(sconfig['leds']):
                        leds.clear_all(); leds.light_threshold(v[px], *ts[:2])
                    if(sensor.name in notifiers):
                        notifiers[sensor.name].test_threshold(v[px])
        sleep(interval)

    # log all values
    if('log' in sconfig and sconfig['log'] and
       v is not None and not None in v):
        sl.write(name, tuple(v), ', '.join(sconfig['formats']))
    
    return(l)

def main(width, height, sl, lcd, leds, notifiers, buzzer,
         sensors, sconfigs, interval, lb):
    """ Main control: generic display, status lights and graphical trace.
    """
    traces = [[] for x in range(len(sconfigs))]
    # continually update all configured sensors
    while(True):
        for i, sconfig in enumerate(sconfigs.values()):
            name = sconfig['name']
            sensor = sensors[name] if name in sensors else None
            traces[i] = update(sl, sensor, sconfig, traces[i], width,
                               lcd, leds, notifiers, interval, lb)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='sensor_panel arguments',
                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    # arguments
    parser.add_argument('--sensor-config', type=str, 
        help='The file to read sensor configuration from')
    parser.add_argument('--sensor-info', type=str, 
        help='The file to read sensor info from')
    parser.add_argument('--device-id', '-di', type=int, default=0,
        help='The SPI device id (e.g. CE0, CE1) to address.')
    parser.add_argument('--display', type=str, default='dummy',
        choices=['ssd1306', 'lcd1602', 'ili9341', 'max7219', 'sevenseg', 'dummy'],
        help='The type of device for displaying info messages')
    parser.add_argument('--aux-id', type=int, default=-1,
        help='The SPI device id for displaying aux graphs. Must be max7219.')
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
    parser.add_argument('--line-break', type=str, default='\n',
        help='The line-break character. Tiny display override')
    parser.add_argument('--adc-addr', type=str, 
        help='Hex I2C address of the a/d converter, e.g. 0x48')
    parser.add_argument('--dht-type', type=str, default='11',
        choices=['11', '22'],
        help='The type of DHT sensor.')
    parser.add_argument('--dht-pin', type=int, 
        help='The data pin of the dht device in BCM')
    parser.add_argument('--bme280-addr', type=str, 
        help='Hex I2C address of the bme280. e.g. 0x76')
    parser.add_argument('--buzzer-type', type=str, 
        choices=['active', 'passive'],
        help='The type of buzzer.')
    parser.add_argument('--buzzer-pin', type=int,
        help='The control pin for the buzzer.')
    parser.add_argument('--led-brightness', type=int, default=100, 
        help='The brightness of the status leds.')
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
    if(args.led_brightness == 100):
        leds = umr.StatusLeds(colorpins)
    else:
        leds = umr.StatusLedsPwm(colorpins, args.led_brightness)

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
        lcd = umr.ILI9341Display(width, height,
                                 device=args.device_id, rotate=rotate,
                                 trace_height=tr_h, trace_color=tr_c,
                                 color=color,
                                 font=font,
                                 echo=False)
    elif(display_type =='max7219'):
        from PIL import ImageFont
        fp = os.path.dirname(sys.argv[0]) + '/../fonts'
        font = ImageFont.truetype(fp + '/ProggyTiny.ttf', 8)
        lcd = umr.MAX7219Display(width, height,
                                 device=args.device_id, rotate=rotate,
                                 trace_height=tr_h,
                                 font=font,
                                 echo=False)
    elif(display_type =='sevenseg'):
        lcd = umr.MAX7219SevenSegDisplay(device=args.device_id)
    else:
        lcd = umr.DummyDisplay()

    aux = None
    if(args.aux_id != -1):
        aux = umr.MAX7219Display(width, height,
                                 device=args.aux_id, rotate=rotate,
                                 trace_height=tr_h,
                                 font=None,
                                 echo=False)

    lcd.display('initializing.. ')
    
    # write sensor readings to file
    sl = umr.SensorLog('sensor_panel_%s.out' % umr.System.get_hostname())

    # a/d converter, if attached
    # note: ads is used dynamically, if referenced in sensor_config*.json
    if(args.adc_addr is not None):
        ads = umr.ADS1115(args.adc_addr)
    
    # DHT11, DHT22 or BME280, if attached
    # note: tsense is used dynamically, if referenced sensor_config*.json
    if(args.dht_pin is not None):
        tsense = umr.DHT(args.dht_pin, type=args.dht_type)
        logging.info('DHT%s on pin %d' % (args.dht_type, args.dht_pin))
    elif(args.bme280_addr is not None):
        tsense = umr.BME280(int(args.bme280_addr, 16))
        logging.info('BME280 on i2c address %s' % args.bme280_addr)
    else:
        logging.info('No temperature/humidity/pressure sensor.')

    # the sensor panel
    try:
        interval = args.interval
        lb = args.line_break
        lcd.display('running..')
        with open(args.sensor_config) as jsonfile:
            sconfigs = json.load(jsonfile)

        # sensors, notifiers
        sensors, notifiers = {}, {}
        for key, sc in sconfigs.items():
            px = sc['preferred_index'] if('preferred_index' in sc) else 0
            try:
                sensor = umr.Sensor(args.sensor_info, key)
                sensors[key] = sensor
                if('notify' in sc):
                    notifiers[sensor.name] = umr.Notifier(sensor, px,
                        sc['buzz'] if 'buzz' in sc else None,
                        sc['notify'],
                        buzzer=buzzer)
            except json.decoder.JSONDecodeError as e:
                logging.error(e)
                sys.exit(1)

        main(width, height, sl, lcd, leds, notifiers, buzzer,
             sensors, sconfigs, interval, lb)
    except KeyboardInterrupt:
        leds.clear_all()
        lcd.destroy()
        leds.destroy()
        buzzer.destroy()


