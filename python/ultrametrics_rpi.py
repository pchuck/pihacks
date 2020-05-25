# ultrametrics_rpi.py
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
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
    System - an encapsulation of a system with methods for interrogating state.
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

    Sphinx markup is used for documentation generation.
"""

class ActiveBuzzer():
    """ wrapper for controlling an active buzzer
    """
    def __init__(self, pin):
        """
        :param pin: The pin number (in BCM) of the buzzer's input.
        :type pin: int
        """
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)

    def start(self):
        """ Start the buzzer. """
        GPIO.output(self.pin, GPIO.HIGH)

    def stop(self):
        """ Stop the buzzer. """
        GPIO.output(self.pin, GPIO.LOW)

class PassiveBuzzer():
    """ wrapper for controlling a passive buzzer
    """
    def __init__(self, pin, resonance=2000, magnitude=500):
        """
        :param pin: The pin number (in BCM) of the buzzer's input.
        :type pin: int
        :param resonance: The resonant frequency in Hz of the buzzer.
        :type resonance: int
        :param magnitude: The magnitude of the waveform to produce.
        :type magnitude: int
        """
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)
        self.pwm = GPIO.PWM(pin, 1)
        self.pwm.start(0)
        self.magnitude = magnitude
        self.resonant = resonant

    def start(self):
        """ Start the buzzer. """
        period = 0.001
        degrees = 360
        self.pwm.start(0)
        for x in range(self.degrees):
            sin_val = math.sin(x * (math.pi / self.degrees / 2))
            tone_val = self.resonant + sin_val * self.magnitude
            self.pwm.ChangeFrequency(tone_val)
            sleep(self.period)

    def stop(self):
        """ Stop the buzzer. """
        self.pwm.stop()

class StatusLeds():
    """ wrapper for controlling commonly used 4-led status bar
        used to indicate four relative levels of criticality.
        Order the lights by 'severity', e.g. red, ylw, grn, blu.
    """
    def __init__(self, colorpins):
        """
        :param colorpins: The pin numbers (in BCM) of the leds.
        :type colorpins: list
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
        """ Light the specified led.
        :param color: The pin number (in BCM) of the led to light
        :type color: int
        """
        GPIO.output(self.colorpins.get(color), GPIO.HIGH)

    def light_threshold(self, v, t1, t2):
        """ Light leds based on a value compared to thresholds. 
        Assumes 3 lights and 2 thresholds.

        :param v: The value to compare to the thresholds.
        :type v: int
        :param t1: The lower threshold.
        :type t1: int
        :param t2: The upper threshold.
        :type t2: int
        """
        if(v < t1):               
            GPIO.output(self.colorpins.get('green'), GPIO.HIGH)
        elif(v >= t1 and v < t2):
            GPIO.output(self.colorpins.get('yellow'), GPIO.HIGH)
        elif(v >= t2):
            GPIO.output(self.colorpins.get('red'), GPIO.HIGH)

    def clear(self):
        """ Clear all leds. """
        GPIO.output(list(self.colorpins.values()), GPIO.LOW)

class StatusLedsPwm():
    """ wrapper for controlling commonly used 4-led status bar
        used to indicate four relative levels of criticality.
        Order the lights by 'severity', e.g. red, ylw, grn, blu.
        Uses PWM to control brightness.
    """
    def __init__(self, colorpins):
        """
        :param colorpins: The pin numbers (in BCM) of the leds.
        :type colorpins: list
        """
        self.colorpins = colorpins
        self.colors, self.pins = colorpins.keys(), colorpins.values()
        self.pwms = {}
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        logging.info('using GPIO pins to drive LEDs: ')
        # enable output and flash each pin in sequence
        for color, pin in colorpins.items(): 
            GPIO.setup(pin, GPIO.OUT)
            logging.info('led pin %d - %s ' % (pin, color))
            self.pwms[color] = GPIO.PWM(pin, 1000)
            self.pwms[color].start(10)
            sleep(0.2)
        self.clear_all()

    def light(self, color, brightness=100):
        """ Light the specified led.
        :param color: The pin number (in BCM) of the led to light
        :type color: int
        :param brightness: The brightness from 0 to 100.
        :type brightness: int
        """
        self.pwms[color].ChangeDutyCycle(brightness)

    def light_threshold(self, v, t1, t2, brightness=100):
        """ Light leds based on a value compared to thresholds. 
        Assumes 3 lights and 2 thresholds.

        :param v: The value to compare to the thresholds.
        :type v: int
        :param t1: The lower threshold.
        :type t1: int
        :param t2: The upper threshold.
        :type t2: int
        """
        if(v < t1):
            self.pwms['green'].ChangeDutyCycle(brightness)
        elif(v >= t1 and v < t2):
            self.pwms['yellow'].ChangeDutyCycle(brightness)
        elif(v >= t2):
            self.pwms['red'].ChangeDutyCycle(brightness)

    def clear_all(self):
        """ Clear all leds. """
        for color, pin in self.colorpins.items(): 
            self.pwms[color].ChangeDutyCycle(0)

    def clear(self, color):
        """ Clear the specified led.
        :param color: The pin number (in BCM) of the led to clear
        :type color: int
        """
        self.pwms[color].ChangeDutyCycle(0)

class DHT11:
    """ dht11 temperature and humidity sensor wrapper
    .. note:: requires adafruit-circuitpython-dht, not Adafruit_DHT,
              also libgpiod2
    """
    def __init__(self, pin):
        """
        :param pin: The pin number (in BCM) of the DHT data line.
        :type pin: int
        """
        import adafruit_dht
        self.dht = adafruit_dht.DHT11(pin)

    def sense_data(self):
        """ Read the temperature and humidity from the DHT11 sensor.
        .. note:: RuntimeError is handled internally. The DT11 read often fails.

        :return: the temperature in celsius, farenheit and the humidity.
        :rtype: (int, int, int)
        :raises: RuntimeError: when the DHT11 read fails
        """
        try:
            temperature_c = self.dht.temperature
            if(temperature_c is None): temperature_f = None
            else: temperature_f = temperature_c * (9 / 5) + 32
            humidity = self.dht.humidity
        except RuntimeError:
            # dht doesn't always succeed. continue.
            return(None, None, None)

        return(temperature_c, temperature_f, humidity)
    
class BasicDisplay:
    """ an informal interface for displaying textual data on a display device
    """
    def clear(self):
        """ Clear the display. """
        pass
    
    def display(self, message):
        """ Display a message.

        :param message: The message to display on the device.
        :type message: str
        """
        pass
    def display_formatted(self, label, sformat, value):
        """ Display a formatted message.

        :param label: The label for the value to be displayed.
        :type label: str
        :param sformat: The formatting string for the value.
        :type sformate: str
        :param value: The value to display.
        :type value: numeric
        """
        if(value is not None):
            self.display(label + ': ' + sformat % value)
        else:
            self.display(label + ': Error')
            
    def destroy(self):
        """ Clean up the device. """
        pass

class DummyDisplay(BasicDisplay):
    """ a dummy implementation of display
    """
    def display(self, message, trace=None):
        """ Display a message.

        :param message: The message to display on the device.
        :type message: str
        :param trace: Ignored. Dummy displays can't display graphical traces.
        :type trace: bool
        """
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
        """
        :param echo: Whether or not to echo writes to the logger.
        :type echo: bool
        """
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
        """ Clear the display. """
        self.lcd.clear()
        
    def display(self, message, trace=None):
        """ Display a message.

        :param message: The message to display on the device.
        :type message: str
        :param trace: Ignored. LCD displays can't display graphical traces.
        :type trace: bool
        """
        self.lcd.clear()
        self.lcd.message(message)
        if(self.echo):
            logging.info(message)

    def destroy(self):
        """ Clean up the display. """
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
    def __init__(self, echo=False, width=128, height=32, rotate=0,
                 trace_height=16,
                 font=None, color='White', i2c_addr=0x3c):
        """
        :param echo: Whether or not to echo writes to the logger.
        :type echo: bool
        :param width: Number of horizontal pixels (optional, defaults to 128).
        :type width: int
        :param height: Number of vertical pixels (optional, defaults to 32).
        :type height: int
        :param rotate: Integer value of 0 (default), 1, 2 or 3 only, where 0 is
            no rotation, 1 is rotate 90° clockwise, 2 is 180° rotation and 3
            represents 270° rotation.
        :type rotate: int
        :param th: Trace height. Height in pixels of the trace graph.
        :type th: int
        :param font: The font.
        :type font: Font
        :param color: Drawing color. Ignored, if the display is monochrome.
        :type color: str
        :param i2c_addr: The address of the device on the i2c bus.
        :type i2c_addr: int
        """
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306 as led

        logging.info('looking for OLED on i2c bus at %x' % i2c_addr)
        serial = i2c(port=1, address=i2c_addr)
        self.device = led(serial, height=height, width=width, rotate=rotate)
        logging.info('OLED found')
        self.device.clear()
        self.echo = echo
        self.font = font
        self.color = color
        self.x = self.device.width
        self.y = self.device.height
        self.trace_height = trace_height
        with canvas(self.device) as draw:
            draw.text((0, 0), 'initializing..',
                      fill=self.color, font=self.font)

    def clear(self):
        """ Clear the display. """
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
                       xp, self.y - (trace[xp] - mnx) *
                           self.trace_height / delta),
                       fill=self.color)
            
    def display(self, message, trace=None):
        """ Display a message.

        :param message: The message to display on the device.
        :type message: str
        :param trace: Whether or not to display a graphical trace.
        :type trace: bool
        """
        with canvas(self.device) as draw:
            draw.text((0, 0), message, fill=self.color, font=self.font)
            if(trace is not None and len(trace) > 0):
                self._graph(draw, trace)
        if(self.echo):
            logging.info(message)

    def destroy(self):
        """ Clean up the display. """
        self.device.cleanup()

class PrintDisplay(BasicDisplay):
    """ implementation for displaying textual data on the console
    """
    def display(self, message):
        """ Display a message.

        :param message: The message to display on the console.
        :type message: str
        """
        print(message)

class LogDisplay(BasicDisplay):
    """ implementation for displaying textual data on the console
    """
    def display(self, message):
        """ Display a message.

        :param message: The message to display in the logs.
        :type message: str
        """
        logging.info(message)


class FileDisplay(BasicDisplay):
    """ implementation for displaying textual data on the console
    """
    def __init__(self, filename, echo=False):
        """
        :param echo: Whether or not to echo writes to the logger.
        :type echo: bool
        """
        self.echo = echo
        self.file = open(filename, 'a')
        
    def display(self, message):
        """ Display a message.

        :param message: The message to the file.
        :type message: str
        """
        t = format('%s, %s\n' % (System.get_datetime(), message))
        self.file.write(t)
        if(self.echo):
            logging.info(t)

    def destroy(self):
        """ Clean up the file resources. """
        self.file.close

class System:
    """
    An encapsulation of a system with static methods for reading its 
    current state and attributes.
    """
    def __init__(self):
        # record start info
        self.datetime_start = get_datetime()
        self.timestamp_start = get_timestamp()

    @staticmethod
    def get_hostname():
        """ Fetch the current hostname.
        :return: The name of the system
        :rtype: str
        """
        return os.popen('hostname').read().strip()

    def get_ip():
        """ Fetch the current ip address.
        :return: The ip address of the system
        :rtype: str
        """
        return socket.gethostbyname(socket.gethostname())

    @staticmethod
    def get_gpu_temp():
        """ Fetch the current GPU temperature (in degrees celsius).
        :return: The temperature of the system's gpu
        :rtype: float
        """
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
    
    @staticmethod
    def get_cpu_temp():
        """ Fetch the current CPU temperature (in degrees celsius).
        :return: The temperature of the system's cpu
        :rtype: float
        """
        tmp = open('/sys/class/thermal/thermal_zone0/temp')
        cpu = tmp.read()
        tmp.close()
        return float(cpu) / 1000.0 # convert from thousandths to degrees

    @staticmethod
    def get_load():
        """ Fetch the current system load.
        :return: The 1, 5 and 15 minute load on the system
        :rtype: (float, float, float)
        """
        return os.getloadavg()

    @staticmethod
    def get_load1():
        """ Fetch the current system 1min load.
        :return: The 1min load on the system
        :rtype: (float, float, float)
        """
        (l1, l5, l15) = os.getloadavg()
        return l1

    @staticmethod
    def get_uptime():
        """
        :return: The uptime of the system in days, hours, mins and secs.
        :rtype: (int, int, int, int)
        """
        hd = 24 # hours per day
        mh, sm = 60, 60 # minutes per hour and seconds per minute
        sh = mh * sm # seconds per hour
        sd = sh * hd # seconds per day
        with open('/proc/uptime', 'r') as f:
            ts = float(f.readline().split()[0])
        days = int(ts / sd)
        hours = int((ts - days * sd) / sh)
        minutes = int((ts - days * sd - hours * sh) / sm)
        seconds = int(ts - days * sd - hours * sh - minutes * sm)
        return(days, hours, minutes, seconds)

    @staticmethod
    def get_time():
        """
        :return: A string containing the formatted system time.
        :rtype: str
        """
        return datetime.now().strftime('%H:%M:%S')

    @staticmethod
    def get_datetime():
        """
        :return: The current formatted date and system time
        :rtype: str
        """
        return '{:%Y-%m-%d %H:%M:%S}'.format(datetime.now())

    @staticmethod
    def get_timestamp():
        """
        :return: The timestamp for the current time.
        :rtype: int
        """
        return datetime.now().timestamp()

