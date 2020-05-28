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
from datetime import datetime
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import ultrametrics_rpi as umr

logging.basicConfig(level=logging.INFO)

# log file prefix for sensor data logging
LOG_PREFIX='aq_hat'

# ADS1115 addr pin addresses (specify via --adc-addr)
#   0v - 0x48
#   5v - 0x49
# number of bits precision of the ADC converter
ADR_BITS=16

# factor of v_baseline (see below) warranting a warning, alert or alarm
warn_factor = 1.5
alert_factor = 2.0
alarm_factor = 3.0
# for testing
#warn_factor = 1.2; alert_factor = 1.5;  alarm_factor = 2.0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='aq hat',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # required arguments, the bcm pin numbers of...
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
    parser.add_argument('--basev', type=float, default='0.2',
                        help='The baseline (clean air) voltage for the sensor')
    parser.add_argument('--buzzer-type', type=str, default='passive',
                        choices=['active', 'passive', 'none'],
                        help='The type of buzzer.')
    parser.add_argument('d', type=int,
                        help='The data pin of the dht11. -1 if none attached.')
    parser.add_argument('b', type=int,
                        help='The signal pin to the first status led')
    parser.add_argument('g', type=int,
                        help='The signal pin to the second status led')
    parser.add_argument('y', type=int,
                        help='The signal pin to the third status led')
    parser.add_argument('r', type=int,
                        help='The signal pin to the last status led')
    parser.add_argument('z', type=int,
                        help='The signal pin to the buzzer')

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

    if(args.d != -1):
        dht = umr.DHT11(args.d)
    
    leds = umr.StatusLeds(colorpins)
    leds.light('green')

    if(args.buzzer_type == 'passive'):
        buzzer = umr.PassiveBuzzer(args.z)
    else:
        buzzer = umr.ActiveBuzzer(args.z)
    buzzer.stop()
    logging.info("buzzer test (0.1s)..")
    leds.clear(); leds.light('red')
    buzzer.start(); time.sleep(0.1)
    logging.info("stop")
    buzzer.stop()
    leds.clear(); leds.light('green')

    display_type = args.display.lower()
    if(display_type == 'lcd1602'):
        lcd = umr.LCD1602Display(echo=False)
    elif(display_type == 'ssd1306'):
        lcd = umr.SSD1306Display(echo=False,
                                 width=args.width, height=args.height,
                                 rotate=0)
    else:
        lcd = umr.DummyDisplay()

    # create the i2c bus and adc object
    mq = umr.MQSensor(args.sensor)
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c, address=int(args.adc_addr, 16))
    adc = AnalogIn(ads, ADS.P0)
    v_baseline = args.basev # baseline voltage

    # sensor data log
    fld = umr.FileDisplay(LOG_PREFIX + "_" + mq.sensor_type.lower() + ".out")

    values = []
    i = 0
    trigger_level = 0
    try:
        i += 1
        lcd.display('initializing.. ')
        #fld.display('datetime, type, raw, voltage')
        while True:
            if(args.d != -1):
                (tc, tf, h) = dht.sense_data() # read dht sensor
                if(tf is not None): fld.display('ambient, %.1f' % tf)
                if(h is not None): fld.display('humidity, %.1f' % h)
                
            r, v = adc.value, adc.voltage # read aq sensor
            if(len(values) > args.width): values.pop(0) # update trace
            values.append(r)
            fld.display('%s, %d, %f' % (mq.sensor_type, r, v))
            if(args.height == 32): # two line display
                lcd.display('AQ=%+.2f%% (%.3fv)' %
                            (-v * 100.0 / v_baseline + 100.0, v), values)
            else: # 4 line text display
                lcd.display('AQ=%+.2f%%\nv=%.4fv/5v\nr=%d/2^%d' %
                            (-v * 100.0 / v_baseline + 100.0, v, r, ADR_BITS),
                            values)
            leds.clear()
            if(v > v_baseline * alarm_factor): # update lights/buzzer
                if(trigger_level != 4):
                    Client().send_message(
                        "%s: > %.1fx %s levels detected! (%.2fv)" % (
                        host, alarm_factor, mq.sensor_type, v),
                        title="%s: alarm" % host)
                leds.light('red')
                buzzer.start();
                trigger_level = 4
            elif(v > v_baseline * alert_factor):
                if(trigger_level != 3):
                    Client().send_message(
                        "%s: > %.1fx %s levels detected (%.2fv)" % (
                        host, alert_factor, mq.sensor_type, v),
                        title="%s: alert" % host)
                leds.light('red')
                buzzer.stop();
                trigger_level = 3
            elif(v > v_baseline * warn_factor):
                if(trigger_level != 2):
                    Client().send_message(
                        "%s: > %.1fx %s levels detected (%.2fv)" % (
                        host, warn_factor, mq.sensor_type, v),
                        title="%s: warn" % host)
                leds.light('yellow')
                buzzer.stop();
                trigger_level = 2
            else:
                if(trigger_level != 1):
                    Client().send_message(
                        "%s: %s levels cleared (%.2fv)" % (
                        host, mq.sensor_type, v),
                        title="%s: ok" % host)

                if(i % 10 == 0):
                    leds.light('green')
                buzzer.stop();
                trigger_level = 1 # reset the trigger
            time.sleep(1)

    except KeyboardInterrupt:
        leds.clear()
        lcd.destroy()
