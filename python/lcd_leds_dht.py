#!/usr/bin/env python3
#
# lcd_leds_dht.py
#
# Status panel using LCD1602 (w/PCF8574 i2c), GPIO driven LED's and
# DHT humidity temperature sensor to continually display information
# about the system, health and its ambient environment.
#
# note: requires adafruit-circuitpython-dht, not Adafruit_DHT, also libgpiod2
# (pin numbering is BCM, one of the included libs is overriding)
# also, requires PCF8574 and Adafruit_LCD1602 to drive the LCD1602
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
#
import os
import socket
from time import sleep, strftime
from datetime import datetime

import RPi.GPIO as GPIO
from PCF8574 import PCF8574_GPIO
from Adafruit_LCD1602 import Adafruit_CharLCD
import adafruit_dht


# LCD wiring - RPi (physical)
#   1 - GND - GND  (1)
#   2 - VCC - 5V   (4)
#   3 - SDA - SDA1 (3)
#   4 - SCL - SCL1 (5)

# LED wiring - GPIO bcm
led_red = 23
led_ylw = 27
led_grn = 24
led_blu = 22

# DHT wiring - GPIO bcm
DHT_PIN = 4

# other constants
expected_ip = '10.0.2.97'


# dht
def init_dht():
    dht_device = adafruit_dht.DHT11(DHT_PIN)
    return dht_device
    
# lcd
def init_lcd():
    PCF8574_address = 0x27  # I2C address of the PCF8574 chip.
    PCF8574A_address = 0x3F  # I2C address of the PCF8574A chip.

    print('looking for LCD on i2c bus')
    try:
        print('trying address ' + str(PCF8574_address) + '.. ' ,
              end='', flush=True)
        mcp = PCF8574_GPIO(PCF8574_address) # PCF8574 GPIO adapter
    except:
        print('not found')
        try:
            print('trying address ' + str(PCF8574A_address) + '.. ',
                  end='', flush=True)
            mcp = PCF8574_GPIO(PCF8574A_address)
        except:
            print('I2C error')
            exit(1)
    print('found!')

    # create LCD and pass in MCP GPIO adapter
    lcd = Adafruit_CharLCD(pin_rs=0,
                           pin_e=2,
                           pins_db=[4, 5, 6, 7],
                           GPIO=mcp)

    mcp.output(3, 1) # turn on LCD backlight
    lcd.begin(16, 2) # set number of LCD lines and columns
    lcd.message('initializing...')

    return(lcd, mcp)
    
# leds
def init_leds():
    GPIO.setwarnings(False)
    led_pins = [led_red, led_ylw, led_grn, led_blu]
    print('using GPIO pins to drive LEDs: ', end='', flush=True)
    for pin in led_pins: # initialize led pins
        GPIO.setup(pin, GPIO.OUT)
        print('%d ' % pin, end='', flush=True)
        GPIO.output(pin, GPIO.HIGH) ; sleep(0.1)
        GPIO.output(pin, GPIO.LOW)
    print('\n')
    return(led_pins)

# read hostname
def get_hostname():
    cmd = os.popen('hostname').read()
    return cmd

# read GPU temperature
def get_gpu_temp():
    cmd = os.popen('vcgencmd measure_temp').read()
    cmd = cmd.split('\'C')[0] # remove the celcius designator
    l = []
    for t in cmd.split('='):
        try:
            l.append(float(t))
        except ValueError:
            pass
    gpu = l[0]
    return gpu

# read CPU temperature
def get_cpu_temp():
    tmp = open('/sys/class/thermal/thermal_zone0/temp')
    cpu = tmp.read()
    tmp.close()
    return float(cpu) / 1000

# load
def get_load():
    return os.getloadavg() # 1, 5, 15min load

# uptime
def get_uptime():
    with open('/proc/uptime', 'r') as f:
        ts = float(f.readline().split()[0])
    days = int(ts / 86400)
    hours = int((ts - days * 86400) / 3600)
    minutes = int((ts - days * 86400 - hours * 3600) / 60)
    seconds = int(ts - days * 86400 - hours * 3600 - minutes * 60)
    return(days, hours, minutes, seconds)

def get_dht_data(dht):
    try:
        temperature_c = dht.temperature
        temperature_f = temperature_c * (9 / 5) + 32
        humidity = dht.humidity
    except RuntimeError:
        # dht doesn't always succeed. continue.
        return(None, None, None)

    return(temperature_c, temperature_f, humidity)


# read system time and format as a string for display
def get_time_now():
    return datetime.now().strftime('%H:%M:%S %z')

# light leds based on specified thresholds    
def update_leds(v, t1, t2):
    if(v < t1):               GPIO.output(led_grn, GPIO.HIGH)
    elif(v >= t1 and v < t2): GPIO.output(led_ylw, GPIO.HIGH)
    elif(v >= t2):            GPIO.output(led_red, GPIO.HIGH)

# clear all leds
def clear_leds(leds):
    GPIO.output(leds, GPIO.LOW)

# cleanup
def destroy(mcp, lcd):
    mcp.output(3, 0)
    lcd.clear()
    
# main
def main(lcd, mcp, leds, dht):
    while(True):         
        # time
        lcd.message('   ' + get_time_now())
        GPIO.output(led_blu, GPIO.HIGH)
        sleep(5) ; lcd.clear() ; clear_leds(leds)

        # hostname/ip
        hostname = get_hostname()
        try:
            ip = socket.gethostbyname(socket.gethostname())
            if(ip == expected_ip):
                GPIO.output(led_grn, GPIO.HIGH)
            else:
                GPIO.output(led_red, GPIO.HIGH)
            lcd.message('host: ' + hostname + '\nip: ' + ip)
        except socket.gaierror: # flag red if gethostbyname fails
            GPIO.output(led_red, GPIO.HIGH)
            lcd.message('host: ' + hostname + '\nip: (gaierror)')
        sleep(5) ; lcd.clear() ; clear_leds(leds)

        # uptime
        (d, h, m, s) = get_uptime()
        lcd.message('uptime: \n%dd, %02d:%02d:%02d' % (d, h, m, s))
        GPIO.output(led_blu, GPIO.HIGH)
        sleep(5) ; lcd.clear() ; clear_leds(leds)
        
        # load
        (l1, l5, l15) = get_load()
        lcd.message('load 1/5/15min:\n%2.2f/%2.2f/%2.2f' % (l1, l5, l15))
        update_leds(l1, 0.5, 1.0)
        sleep(5) ; lcd.clear() ; clear_leds(leds)

        # cpu / gpu
        tc = get_cpu_temp()
        tg = get_gpu_temp()
        lcd.message('cpu: %.2f C\ngpu: %.2f C' % (tc, tg))
        update_leds(tc, 50, 75)
        update_leds(tg, 55, 80)
        sleep(5) ; lcd.clear() ; clear_leds(leds)

        # dht
        (tc, tf, h) = get_dht_data(dht)
        if((tf is not None) and (h is not None)):
            lcd.message('ambient: %.1f F\nhumidity: %.1f' % (tf, h))
            update_leds(tf, 65, 85)
        else:
            lcd.message('ambient: Err\nhumidity: Err')
            GPIO.output(led_red, GPIO.HIGH)
        sleep(5) ; lcd.clear() ; clear_leds(leds)

if __name__ == '__main__':
    print('initializing.. ')
    lcd, mcp = init_lcd()
    leds = init_leds()
    dht = init_dht()
    try:
        print('running.. ')
        main(lcd, mcp, leds, dht)
    except KeyboardInterrupt:
        clear_leds(leds)
        destroy(mcp, lcd)

