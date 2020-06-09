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
import os
import sys
import logging
from time import sleep
import socket
import argparse
import ultrametrics_rpi as umr

DTIME=1 # number of seconds between sensor readings
PTIME=10 # number of dtimes to persist each sensor screen
GPU_ALERT, GPU_ALARM=65, 80 # gpu thresholds
CPU_ALERT, CPU_ALARM=60, 75 # cpu thresholds
LOAD_ALERT, LOAD_ALARM=1.5, 3.0 # load thresholds
T_ALERT, T_ALARM=85, 95 # temperature thresholds in farenheit
# the BME280 board is too close to the cpu, so use a high threshold
# T_ALERT, T_ALARM=90, 110 # temperature thresholds in farenheit
H_ALERT, H_ALARM=60, 90 # humidity thresholds

logging.basicConfig(level=logging.INFO)

def update_time():
    """ Update time display and status lights.
    """
    lcd.display(umr.System.get_time())
    leds.light('blue')
    sleep(PTIME * DTIME) ; leds.clear()

def update_hostname(e_ip):
    """ Update hostname and ip display.
    """
    hostname = umr.System.get_hostname()
    try:
        ip = umr.System.get_ip()
        if(ip == e_ip):
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

def update_th(lcd, leds, tf, h, p, buzz=False):
    """ Update temperature and humidity display and status lights.
    """
    if(tf is not None and h is not None):
        leds.light_threshold(tf, T_ALERT, T_ALARM, buzz=buzz)
        leds.light_threshold(h, H_ALERT, H_ALARM, buzz=buzz)
        if(p is None):
            lcd.display('ambient: %.1f F\nhumidity: %.1f' % (tf, h))
        else:
            lcd.display('ambient: %.1f F\nhumidity: %.1f\npressure: %.1f' %
                        (tf, h, p))
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

def update(width, lcd, leds, func, name, l, low, high, 
           vformat='%s', units='', clear=True, farg=None, buzz=False):
    """ Generic display and status light update routine, with graphical trace.
    """
    for i in range(PTIME):
        if(farg is not None): v = func(farg)
        else: v = func()
        
        l = sense_fifo(width, v, l)
        if(v is None):
            lcd.display(name + ': Err')
        else:
            lcd.display(name + ': ' + vformat % v + '%s' % units, trace=l)
            leds.light_threshold(v, low, high, buzz=buzz);
        sleep(DTIME)
        if(clear):
            leds.clear()
            
    return(v, l)


def main(width, height, sl, lcd, leds, buzzer, thsense, e_ip, ads, sensors):
    """ Main control: generic display, status lights and graphical trace.
    """
    """ sends buzz=True to update routines, where audible alert is desired
    """
    l1s, tcs, tgs, tfs, hs = [], [], [], [], []
    if(sensors):
        svs = [[0 for x in range(len(sensors))] for y in range(width)]
    
    while(True):
        # no graphing, simple update for these
        update_time()
        update_hostname(e_ip)
        update_uptime()

        # air quality sensors
        if(sensors): 
            for i, sensor in enumerate(sensors):
                mq = umr.MQSensor(sensor)
                (mqv, mqvs) = update(width, lcd, leds, ads.read_voltage,
                                     sensor, svs[i],
                                     mq.baseline_v * 1.5, mq.baseline_v * 3,
                                     vformat='%.2f', units=' V',
                                     clear=False, farg=i, buzz=True)
                mqb = ads.read_values(i)
                sl.write(sensor, mqb, vformat='%d, %2f')

        # load
        (l1, l1s) = update(width, lcd, leds,
                           umr.System.get_load1, 'load', l1s,
                           LOAD_ALERT, LOAD_ALARM,
                           vformat='%2.2f', clear=True, buzz=False)
        sl.write('load', l1, vformat='%2.2f')

        # cpu
        (tc, tcs) = update(width, lcd, leds,
                           umr.System.get_cpu_temp, 'cpu', tcs,
                           CPU_ALERT, CPU_ALARM,
                           vformat='%.1f', units=' C', clear=True, buzz=True)
        sl.write('cpu', tc, vformat='%.1f')

        # gpu
        (tg, tgs) = update(width, lcd, leds,
                           umr.System.get_gpu_temp, 'gpu', tgs,
                           GPU_ALERT, GPU_ALARM,
                           vformat='%.1f', units=' C', clear=True, buzz=True)
        sl.write('gpu', tg, vformat='%.1f')

        # no graphing for temperature, humidity and pressure
        if(thsense):
            (tc, tf, h, p) = thsense.sense_data()
            update_th(lcd, leds, tf, h, p, buzz=False)
            if(tf is not None): sl.write('ambient', tf, vformat='%.1f')
            if(h is not None): sl.write('humidity', h, vformat='%.1f')
            if(p is not None): sl.write('pressure', p, vformat='%.1f')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='sensor_panel arguments',
                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    # arguments
    parser.add_argument('--display', type=str, default='dummy',
                        choices=['ssd1306', 'lcd1602', 'ili9341', 'dummy'],
                        help='The type of device for displaying info messages')
    parser.add_argument('--rotate', type=int, default=0,
                        choices=[0, 1, 2, 3],
                        help='The amount to rotate the display.')
    parser.add_argument('--width', type=int, default=128,
                        help='The width of the display in pixels')
    parser.add_argument('--height', type=int, default=32,
                        help='The height of the display in pixels')
    parser.add_argument('--adc-addr', type=str, default="0x48",
                        help='The I2C address of the a/d converter')
    parser.add_argument('--sensors', type=str,
                        help='Comma-delimited name(s) of the analog sensor(s)')
    parser.add_argument('--dht11', type=int, 
                        help='The data pin of the dht11 in BCM')
    parser.add_argument('--bme280', type=str, 
                        help='The hex i2c address of the bme280. e.g. 0x76')
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
    width, height = args.width, args.height
    display_type = args.display.lower()
    if(display_type == 'lcd1602'):
        lcd = umr.LCD1602Display(echo=False)
    elif(display_type == 'ssd1306'):
        lcd = umr.SSD1306Display(echo=False, rotate=args.rotate,
                                 width=width, height=height)
    elif(display_type == 'ili9341'):
        from PIL import ImageFont
        fp = os.path.dirname(sys.argv[0]) + '/../fonts'
        font = ImageFont.truetype(fp + '/Volter__28Goldfish_29.ttf', 32)
        lcd = umr.ILI9341Display(echo=False, rotate=args.rotate,
                                 width=width, height=height, font=font)
    else:
        lcd = umr.DummyDisplay()

    lcd.display('initializing.. ')
       
    # list of attached analog sensors (e.g. mq135, light, etc)
    sensors = ads = None
    if(args.sensors):
        sensors = args.sensors.split(',')
        if(sensors):
            ads = umr.ADS1115(args.adc_addr)

    # write sensor readings to file
    sl = umr.SensorLog('sensor_panel_dht.%s.out' % umr.System.get_hostname())
    
    # DHT11
    if(args.dht11 is not None):
        thsense = umr.DHT11(args.dht11)
    elif(args.bme280 is not None):
        thsense = umr.BME280(int(args.bme280, 16))
    else:
        thsense = None

    # the sensor panel
    try:
        lcd.display('running.. ')
        eip = umr.System.get_ip()
        main(width, height, sl, lcd, leds, buzzer, thsense, eip, ads, sensors)
    except KeyboardInterrupt:
        leds.clear()
        lcd.destroy()
        leds.destroy()
        buzzer.destroy()


