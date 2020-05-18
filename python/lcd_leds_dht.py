#!/usr/bin/env python3
#
# Status panel using LCD1602 (w/PCF8574 i2c), GPIO driven LED's and
# DHT humidity temperature sensor to continually display information
# about the system, health and its ambient environment.
#
# note: requires adafruit-circuitpython-dht, not Adafruit_DHT, also libgpiod2
# (pin numbering is BOARD not BCM, one of the included libs is overriding)
#
import socket
from time import sleep
import argparse
import ultrametrics_rpi as umr


# get current ip for later comparison in runtime checks
def get_ip():
    return socket.gethostbyname(socket.gethostname())

# main
def main(fld, lcd, leds, dht, expected_ip):
    while(True):         
        # time
        lcd.display(umr.get_time_now())
        leds.light('blue')
        sleep(5) ; leds.clear()

        # hostname/ip
        hostname = umr.get_hostname()
        try:
            ip = get_ip()
            if(ip == expected_ip):
                leds.light('green')
            else:
                leds.light('red')
            lcd.display('host: ' + hostname + '\nip: ' + ip)
        except socket.gaierror: 
            leds.light('red') # flag red if gethostbyname fails
            lcd.display('host: ' + hostname + '\nip: (gaierror)')
        sleep(5) ; leds.clear()

        # uptime
        (d, h, m, s) = umr.get_uptime()
        lcd.display('uptime: \n%dd, %02d:%02d:%02d' % (d, h, m, s))
        leds.light('blue'); sleep(5) ; leds.clear()
        
        # load
        (l1, l5, l15) = umr.get_load()
        lcd.display('load 1/5/15min:\n%2.2f/%2.2f/%2.2f' % (l1, l5, l15))
        fld.display('load - %2.2f' % l1)
        fld.display('load5 - %2.2f' % l5)
        fld.display('load15 - %2.2f' % l15)
        leds.light_threshold(l1, 1.5, 3.0); sleep(5) ; leds.clear()

        # cpu / gpu
        tc, tg = umr.get_cpu_temp(), umr.get_gpu_temp()
        lcd.display('cpu: %.2f C\ngpu: %.2f C' % (tc, tg))
        fld.display('cpu - %.2fC' % tc)
        fld.display('gpu - %.2fC' % tg)
        leds.light_threshold(tc, 60, 75)
        leds.light_threshold(tg, 65, 80)
        sleep(5) ; leds.clear()

        # dht
        (tc, tf, h) = dht.sense_data()
        if((tf is not None) and (h is not None)):
            lcd.display('ambient: %.1f F\nhumidity: %.1f' % (tf, h))
            fld.display('ambient - %.1fF' % tf)
            fld.display('humidity - %.1f' % h)
            leds.light_threshold(tf, 85, 95)
            leds.light_threshold(h, 60, 90)
        else:
            lcd.display('ambient: Err\nhumidity: Err')
            leds.light('red')
        sleep(5) ; leds.clear()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='lcd_leds_dht arguments',
                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    # required arguments, the bcm pin numbers of...
    parser.add_argument('d', type=int, 
        help='The data pin of the dht11')
    parser.add_argument('b', type=int, 
        help='The signal pin to the first status led')
    parser.add_argument('g', type=int, 
        help='The signal pin to the second status led')
    parser.add_argument('y', type=int, 
        help='The signal pin to the third status led')
    parser.add_argument('r', type=int, 
        help='The signal pin to the last status led')

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

    lcd = umr.LCD_dummy_display()
    # lcd = umr.LCD1602_display(echo=False)
    fld = umr.file_display('lcd_leds_dht_sensor.out')
    lcd.display('initializing.. ')
    leds = umr.status_leds(colorpins)
    dht = umr.DHT11_device(DHT_PIN)

    try:
        lcd.display('running.. ')
        expected_ip = get_ip()
        main(fld, lcd, leds, dht, expected_ip)
    except KeyboardInterrupt:
        leds.clear()
        lcd.destroy()

