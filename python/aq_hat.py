#!/usr/bin/env python3
#
# first pass at control code for custom built air quality sensor hat
# 
# Incorporates an MQ-series air quality sensor, an ADS1115 for A/D conversion,
# led lights for status, an oled such as SSD1306 for visual display,
# and a piezo-electric buzzer for alarm.
#
# prerequisites:
#   pip3 install adafruit-circuitpython-ads1x15
#   pip3 install python-pushover
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
#
import logging
import argparse
import time
import board
import busio
from pushover import Client
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import ultrametrics_rpi as umr

logging.basicConfig(level=logging.INFO)

# log file prefix for sensor data logging
LOG_PREFIX='aq_hat'

# number of bits precision of the ADC converter
ADR_BITS=16
# ADS1115 addresses (specify via --adc-addr)
#   addr @ 0v - 0x48, @ 5v - 0x49


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='aq hat',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--log-interval', type=int, default=5,
                        help='The interval in seconds between log writes')
    parser.add_argument('--sensor-info', type=str, 
                        help='The file to read sensor info from')
    parser.add_argument('--display', type=str, default='dummy',
                        choices=['ssd1306', 'lcd1602', 'dummy'],
                        help='The type of device for displaying info messages')
    parser.add_argument('--width', type=int, default=128,
                        help='The width of the display in pixels')
    parser.add_argument('--height', type=int, default=32,
                        help='The height of the display in pixels')
    parser.add_argument('--sensor', type=str, default='MQX',
                        help='The type/name of the sensor')
    parser.add_argument('--adc-addr', type=str, default="0x48",
                        help='The I2C address of the a/d converter')
    parser.add_argument('--buzzer-type', type=str, default='passive',
                        choices=['active', 'passive', 'none'],
                        help='The type of buzzer.')
    parser.add_argument('--buzzer-pin', type=int,
                        help='The signal pin to the buzzer')
    parser.add_argument('--dht-type', type=str, default='11',
                        choices=['11', '22'],
                        help='The type of DHT sensor.')
    parser.add_argument('--dht-pin', type=int, default=-1,
                        help='The data pin of the dht in BCM. -1 if none.')
    parser.add_argument('--led-brightness', type=int, default=100,
                        help='The brightness of the status leds.')
    parser.add_argument('b', type=int,
                        help='The signal pin to the first status led')
    parser.add_argument('g', type=int,
                        help='The signal pin to the second status led')
    parser.add_argument('y', type=int,
                        help='The signal pin to the third status led')
    parser.add_argument('r', type=int,
                        help='The signal pin to the last status led')

    args = parser.parse_args()
    host = umr.System.get_hostname()

    # LED wiring - colors and their associated pins
    # status_leds() expects the pins to be in order of increasing 'severity'
    colorpins = {
        'blue': args.b,
        'green': args.g,
        'yellow': args.y,
        'red': args.r
    }
    if(args.led_brightness == 100):
        leds = umr.StatusLeds(colorpins)
    else:
        leds = umr.StatusLedsPwm(colorpins, args.led_brightness)

    # DHT sensor
    if(args.dht_pin != -1):
        dht = umr.DHT(args.dht_pin, type=args.dht_type)
        logging.info('DHT%s on pin %d' % (args.dht_type, args.dht_pin))

    # buzzer
    if(args.buzzer_type == 'passive'):
        buzzer = umr.PassiveBuzzer(args.buzzer_pin)
    elif(args.buzzer_type == 'active'):
        buzzer = umr.ActiveBuzzer(args.buzzer_pin)
    else:
        buzzer = umr.DummyBuzzer()
    logging.info(str(type(buzzer)) + ": test (0.1s)")
    leds.clear_all(); leds.light('red')
    buzzer.start(); time.sleep(0.1); buzzer.stop()
    leds.clear_all(); leds.light('green')

    # display
    display_type = args.display.lower()
    if(display_type == 'lcd1602'):
        lcd = umr.LCD1602Display(echo=False)
    elif(display_type == 'ssd1306'):
        lcd = umr.SSD1306Display(echo=False,
                                 width=args.width, height=args.height,
                                 rotate=0)
    else:
        lcd = umr.DummyDisplay()

    # create the sensor
    sensor = umr.Sensor(args.sensor_info, args.sensor)
    logging.info('sensor: ' + sensor.name)
    logging.info('warn/alert/alarm thresholds: ' + str(sensor.thresholds))

    # create the i2c bus and adc object
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c, address=int(args.adc_addr, 16))
    adc = AnalogIn(ads, ADS.P0)

    # notifier
    notifier = umr.Notifier(sensor, 1, True, True,  buzzer=buzzer)

    # sensor data log
    sl = umr.SensorLog(LOG_PREFIX + "_" + sensor.name + ".out")

    values = []
    i = 0
    try:
        lcd.display('initializing.. ')
        #sl.write('datetime, type, raw, voltage') # don't rewrite the header
        while True:
            # stop the buzzer before reading the dht/adc. interferes w/ read
            buzzer.stop()

            # read dht sensor and log
            if(args.dht_pin != -1):
                (tc, tf, h, p) = dht.sense_data() 
                if(i % args.log_interval == 0):
                    if(tf is not None): sl.write('ambient', tf, vformat='%.1f')
                    if(h is not None): sl.write('humidity', h, vformat='%.1f')

            # read aq sensor and log
            try:
                r, v = adc.value, adc.voltage 
                if(i % args.log_interval == 0):
                    sl.write_message('%s, %d, %f' %
                                     (sensor.name.upper(), r, v))

                # update graphical trace buffer
                if(len(values) > args.width): values.pop(0)
                values.append(r)

                # calculate a relative percentage of air-quality, for display
                v_rel = v * 100.0 / sensor.baseline_v - 100.0
                if(args.height == 32): # two line display
                    lcd.display('%s=%+.1f%% (%.2fv)' %
                                (sensor.short, v_rel, v), values)
                else: # 4 line text display
                    lcd.display('%s=%+.2f%%\nv=%.4fv/5v\nr=%d/2^%d' %
                                (sensor.short, v_rel, v, r, ADR_BITS), values)

                # calculate thresholds, test and take action
                v_baseline = sensor.baseline[1]
                t1 = sensor.thresholds[0] * sensor.baseline_v
                t2 = sensor.thresholds[1] * sensor.baseline_v
                leds.clear_all(); leds.light_threshold(v, t1, t2)
                notifier.test_threshold(v)
            except OSError:
                logging.error('ADC Read failed!')

            # wait and iterate
            time.sleep(1)
            i += 1

    except KeyboardInterrupt:
        leds.clear_all()
        lcd.destroy()
