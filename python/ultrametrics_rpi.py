import logging
import os
from time import strftime, sleep
from datetime import datetime

import RPi.GPIO as GPIO
from PCF8574 import PCF8574_GPIO
from Adafruit_LCD1602 import Adafruit_CharLCD
import adafruit_dht

logging.basicConfig(level=logging.DEBUG)
GPIO.setmode(GPIO.BCM) # all functions use BCM pin numbering
GPIO.setwarnings(False)


class status_leds():
    """ wrapper for controlling commonly used 4-led status bar
        used to indicate four relative levels of criticality
    """
    def __init__(self, colorpins):
        """ specify, using BCM, the pins used, in the order: red, ylw, grn, blu
            expects a dictionary of colors and associated bcm pin numbers
        """
        
        self.colorpins = colorpins
        self.colors, self.pins = colorpins.keys(), colorpins.values()
        logging.info('using GPIO pins to drive LEDs: ')
        # enable output and flash each pin in sequence
        for color, pin in colorpins.items(): 
            GPIO.setup(pin, GPIO.OUT)
            logging.info('led pin %d - %s ' % (pin, color))
            GPIO.output(pin, GPIO.HIGH)
            sleep(0.2)
            GPIO.output(pin, GPIO.LOW)

    def light(self, color):
        GPIO.output(self.colorpins.get(color), GPIO.HIGH)


    def light_threshold(self, v, t1, t2):
        """ light leds based on specified thresholds
            note: currently assumes 3 lights and 2 thresholds
        """
        
        if(v < t1):               
            GPIO.output(self.colorpins.get('green'), GPIO.HIGH)
        elif(v >= t1 and v < t2):
            GPIO.output(self.colorpins.get('yellow'), GPIO.HIGH)
        elif(v >= t2):
            GPIO.output(self.colorpins.get('red'), GPIO.HIGH)

    def clear(self):
        """ clear all leds
        """
        GPIO.output(list(self.colorpins.values()), GPIO.LOW)

class DHT11_device:
    """ dht11 temperature and humidity sensor wrapper
    """
    def __init__(self, pin):
        self.dht = adafruit_dht.DHT11(pin)

    def sense_data(self):
        try:
            temperature_c = self.dht.temperature
            temperature_f = temperature_c * (9 / 5) + 32
            humidity = self.dht.humidity
        except RuntimeError:
            # dht doesn't always succeed. continue.
            return(None, None, None)

        return(temperature_c, temperature_f, humidity)
    
class informal_data_display:
    """ interface for displaying textual data on a display device
    """
    def clear(self):
        """clear the display"""
        pass
    def display(self, message):
        """display the message"""
        pass
    def destroy(self):
        """clean up the device"""
        pass

class LCD_dummy_display(informal_data_display):
    """ a dummy implementation of LCD1602 for testing/simulation
    """
    def display(self, message):
        print(message)
    
class LCD1602_display(informal_data_display):
    """ implementation for displaying textual data on a display device

    Notes
    -----
    LCD wiring - RPi (physical)
     1 - GND - GND  (1)
     2 - VCC - 5V   (4)
     3 - SDA - SDA1 (3)
     4 - SCL - SCL1 (5)
    """

    def __init__(self, echo=False):
        self.echo = echo
        PCF8574_address = 0x27  # I2C address of the PCF8574 chip.
        PCF8574A_address = 0x3F  # I2C address of the PCF8574A chip.

        logging.info('looking for LCD on i2c bus')
        try:
            logging.info('trying address ' + str(PCF8574_address) + '.. ')
            self.mcp = PCF8574_GPIO(PCF8574_address) # PCF8574 GPIO adapter
            logging.info('found PCF8574!')
        except:
            try:
                logging.info('trying addr %s.. ' % str(PCF8574A_address))
                self.mcp = PCF8574_GPIO(PCF8574A_address)
                logging.info('found PCF8574A!')
            except:
                logging.error('I2C error')

        # create LCD and pass in MCP GPIO adapter
        self.lcd = Adafruit_CharLCD(pin_rs=0,
                                    pin_e=2,
                                    pins_db=[4, 5, 6, 7],
                                    GPIO=self.mcp)

        self.mcp.output(3, 1) # turn on LCD backlight
        self.lcd.begin(16, 2) # set number of LCD lines and columns
        self.lcd.message('initializing...')

    def clear(self):
        self.lcd.clear()
        
    def display(self, message):
        self.lcd.clear()
        self.lcd.message(message)
        if(self.echo is True):
            logging.info(message)

    def destroy(self):
        self.mcp.output(3, 0)
        self.lcd.clear()

class print_display(informal_data_display):
    """ implementation for displaying textual data on the console
    """
    def display(self, message):
        print(message)
        
class log_display(informal_data_display):
    """ implementation for displaying textual data on the console
    """

    def display(self, message):
        logging.info(message)

class file_display(informal_data_display):
    """ implementation for displaying textual data on the console
    """
    def __init__(self, filename, echo=False):
        self.echo = echo
        self.file = open(filename, 'a')
        
    def display(self, message):
        t = format('ts - %s, %s\n' % (get_timestamp_now(), message))
        self.file.write(t)
        if(self.echo is True):
            logging.info(t)

    def destroy(self):
        self.file.close


# manager capable
#
class OutputManager(object):
    """ class summary line

    elaboration on the docstring

    Methods
    -------
    write(text)
        Write text to the specified targets
    """

    valid_targets = ['logger', 'lcd', 'file']
    targets = []
    
    
    def __init__(self, targets):
        self.targets = targets
        if(targets.contains('LCD1602')):
           d = LCD1602()
           (self.lcd, self.mcp) = LCD1602.get_device()
           
    def write(self, text):
        """ write some text

        Parameters
        ----------
        text : str
            The text to output

        Returns
        -------
        int
            whether or not the text was successfully written

        Raises
        ------
        Exception
           if the manager experienced a critical error performing the write

        See Also
        --------
        average : Weighted average

        Notes
        -----
        The FFT is a fast implementation of the discrete Fourier transform:
        """




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

# read system time and format as a string for display
def get_time_now():
    return datetime.now().strftime('%H:%M:%S')

# generate the current timestamp
def get_timestamp_now():
    return '{:%Y-%m-%d %H:%M:%S}'.format(datetime.now())
