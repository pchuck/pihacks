# ultrametrics_rpi.py
#
import logging
import os
import math
import socket
from time import strftime, sleep
from datetime import datetime
import RPi.GPIO as GPIO
from luma.core.render import canvas

"""
  Classes for controlling Raspberry Pi GPIO devices
    Buzzer - a passive buzzer component, with start() and stop()
    ActiveBuzzer - an active buzzer component, with start() and stop()
    StatusLeds - status lights controlled individually or by threshold
    DHT11 - a temperature and humidity sensor that can be read
    BasicDisplay - basic interface for displaying status text and graphs
    LCD1602Display - an LCD that can display two lines of status
    SSD1306Display - an OLED that can display multiple lines of status/graphs
    LogDisplay - adheres to BasicDisplay interface and outputs to a logger
    PrintDisplay - adheres to BasicDisplay interface and outputs to console
    DummyDisplay - adheres to BasicDisplay interface with noop or console out
    FileDisplay - adheres to BasicDisplay interface and writes to a data file
    System - encapsulation of system with methods for interrogating state.
"""

class ActiveBuzzer():
    """ wrapper for controlling an active buzzer
    """
    def __init__(self, pin):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)

    def start(self):
        GPIO.output(self.pin, GPIO.HIGH)

    def stop(self):
        GPIO.output(self.pin, GPIO.LOW)

class PassiveBuzzer():
    """ wrapper for controlling a passive buzzer
    """
    def __init__(self, pin):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)
        self.pwm = GPIO.PWM(pin, 1)
        self.pwm.start(0)
        self.magnitude = 500
        self.resonant = 2000
        self.period = 0.001

    def start(self):
        self.pwm.start(50)
        for x in range(0, 361):
            sin_val = math.sin(x * (math.pi / 180.0))
            tone_val = self.resonant + sin_val * self.magnitude
            self.pwm.ChangeFrequency(tone_val)
            sleep(self.period)

    def stop(self):
        self.pwm.stop()

class StatusLeds():
    """ wrapper for controlling commonly used 4-led status bar
        used to indicate four relative levels of criticality
    """
    def __init__(self, colorpins):
        """ specify, using BCM, the pins used, in the order: red, ylw, grn, blu
            expects a dictionary of colors and associated bcm pin numbers
        """
        
        self.colorpins = colorpins
        self.colors, self.pins = colorpins.keys(), colorpins.values()
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
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

class DHT11:
    """ dht11 temperature and humidity sensor wrapper
    """
    def __init__(self, pin):
        import adafruit_dht
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
    
class BasicDisplay:
    """ an informal interface for displaying textual data on a display device
    """
    def clear(self):
        """clear the display"""
        pass
    def display(self, message):
        """display the message"""
        pass
    def display_formatted(self, label, sformat, value):
        if(value is not None):
            self.display(label + ': ' + sformat % value)
        else:
            self.display(label + ': Error')
            
    def destroy(self):
        """clean up the device"""
        pass

class DummyDisplay(BasicDisplay):
    """ a dummy implementation of display
    """
    def display(self, message, trace=None):
        print(message)
    
class LCD1602Display(BasicDisplay):
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
        from PCF8574 import PCF8574_GPIO
        from Adafruit_LCD1602 import Adafruit_CharLCD

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
        
    def display(self, message, trace=None):
        self.lcd.clear()
        self.lcd.message(message)
        if(self.echo):
            logging.info(message)

    def destroy(self):
        self.mcp.output(3, 0)
        self.lcd.clear()

class SSD1306Display(BasicDisplay):
    """ implementation for displaying textual data on a display device

    Notes
    -----
    LCD wiring - RPi (physical)
     1 - GND - GND  (1)
     2 - VCC - 5V   (4)
     3 - SDA - SDA1 (3)
     4 - SCL - SCL1 (5)
    """
    def __init__(self, echo=False, height=32, bh=16,
                 font=None, color='White', i2c_addr=0x3c):
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306 as led

        logging.info('looking for OLED on i2c bus at %x' % i2c_addr)
        serial = i2c(port=1, address=i2c_addr)
        self.device = led(serial, height=height)
        logging.info('OLED found')
        self.device.clear()
        self.echo = echo
        self.font = font
        self.color = color
        self.x = self.device.width
        self.y = self.device.height
        self.bh = bh # height of bar region, in pixels
        with canvas(self.device) as draw:
            draw.text((0, 0), 'initializing..',
                      fill=self.color, font=self.font)

    def clear(self):
        self.device.clear()

    def _graph(self, draw, trace):
        """
        auxiliary method invoked by display() when trace data is provided
        for graphical display.
        """
        mxx = max(trace)
        mnx = min(trace)
        delta = mxx - mnx + 1
        for xp in range(len(trace)):
            draw.line((xp, self.y,
                       xp, self.y - (trace[xp] - mnx) * self.bh / delta),
                       fill=self.color)
        
    def display(self, message, trace=None):
        with canvas(self.device) as draw:
            draw.text((0, 0), message, fill=self.color, font=self.font)
            if(trace is not None and len(trace) > 0):
                self._graph(draw, trace)
        if(self.echo):
            logging.info(message)

    def destroy(self):
        self.device.cleanup()

class PrintDisplay(BasicDisplay):
    """ implementation for displaying textual data on the console
    """
    def display(self, message):
        print(message)

class LogDisplay(BasicDisplay):
    """ implementation for displaying textual data on the console
    """
    def display(self, message):
        logging.info(message)


class FileDisplay(BasicDisplay):
    """ implementation for displaying textual data on the console
    """
    def __init__(self, filename, echo=False):
        self.echo = echo
        self.file = open(filename, 'a')
        
    def display(self, message):
        t = format('%s, %s\n' % (System.get_datetime(), message))
        self.file.write(t)
        if(self.echo):
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

class System:
    """
    An encapsulation of a system with static methods for reading its 
    current state and attributes.
    """
    def __init__(self):
        # record start info
        self.datetime_start = get_datetime()
        self.timestamp_start = get_timestamp()

    # hostname
    @staticmethod
    def get_hostname():
        return os.popen('hostname').read()

    # ip
    def get_ip():
        return socket.gethostbyname(socket.gethostname())

    # gpu temperature
    @staticmethod
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
    
    # CPU temperature
    @staticmethod
    def get_cpu_temp():
        tmp = open('/sys/class/thermal/thermal_zone0/temp')
        cpu = tmp.read()
        tmp.close()
        return float(cpu) / 1000.0

    # load
    @staticmethod
    def get_load():
        return os.getloadavg() # 1, 5, 15min load

    # load1 (non-tuple version useful as a passed function)
    @staticmethod
    def get_load1():
        (l1, l5, l15) = os.getloadavg()
        return l1

    # uptime
    @staticmethod
    def get_uptime():
        with open('/proc/uptime', 'r') as f:
            ts = float(f.readline().split()[0])
        days = int(ts / 86400)
        hours = int((ts - days * 86400) / 3600)
        minutes = int((ts - days * 86400 - hours * 3600) / 60)
        seconds = int(ts - days * 86400 - hours * 3600 - minutes * 60)
        return(days, hours, minutes, seconds)

    # read system time and format as a string for display
    @staticmethod
    def get_time():
        return datetime.now().strftime('%H:%M:%S')

    # generate the datetime stamp
    @staticmethod
    def get_datetime():
        return '{:%Y-%m-%d %H:%M:%S}'.format(datetime.now())

    # generate the current timestamp
    @staticmethod
    def get_timestamp():
        return datetime.now().timestamp()

