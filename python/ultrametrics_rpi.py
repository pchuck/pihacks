# ultrametrics_rpi.py
#
# prerequisites:
#   pip3 install luma.core
#   pip3 install luma.oled # for ssd1306
#   sudo apt-get install libgpiod2
#   pip3 install adafruit-circuitpython-dht # for DHT11 or 22
#   pip3 install adafruit-circuitpython-bme280 # for BME/BMP280
#   pip3 install adafruit-circuitpython-ads1x15
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
#
import json
import logging
import os
import math
import socket
from time import strftime, sleep
from datetime import datetime

"""
  Classes for controlling Raspberry Pi GPIO devices
    System - an encapsulation of a system with methods for interrogating state.
    BuzzerInterface - a standard interface for buzzers.
    PassiveBuzzer - a passive buzzer component, with start() and stop()
    ActiveBuzzer - an active buzzer component, with start() and stop()
    DummyBuzzer - a buzzer that doesn't make any sound.
    Notifier - a controller for sending text notifications on thresholds
    StatusLeds - status lights controlled individually or by threshold
    StatusLedsPwm - status lights, pwm version with brightness control
    DHT - a DHT11 or DHT22 temperature and humidity sensor
    BME280 - a temperature, humidity and pressure sensor
    BasicDisplay - basic interface for displaying status text and graphs
    LCD1602Display - an LCD that can display two lines of status
    ILI9341Display - an hi res color LED that can display status/graphics
    SSD1306Display - an low res mono OLED that can display status/graphs
    MAX7219Display - an LED matrix that can display status/graphs
    LogDisplay - adheres to BasicDisplay interface and outputs to a logger
    PrintDisplay - adheres to BasicDisplay interface and outputs to console
    DummyDisplay - adheres to BasicDisplay interface with noop or console out
    SensorLog - writes data to file for later analysis
    System - a utility class with static methods for fetching system stats
    Sensor - an abstraction for sensors
    ADS1115 - analog to digital converter

    Sphinx markup is used for documentation generation.
"""


class BuzzerInterface():
    """ an informal interface for buzzers.
    """
    def __init__(self):
        pass

    def start(self):
        pass
    
    def stop(self):
        pass

    def destroy(self):
        pass

class DummyBuzzer(BuzzerInterface):
    """ a buzzer that doesn't make any sound.
    """

class ActiveBuzzer(BuzzerInterface):
    """ wrapper for controlling an active buzzer
    """
    def __init__(self, pin):
        """
        :param pin: The pin number (in BCM) of the buzzer's input.
        :type pin: int
        """
        import RPi.GPIO as GPIO
        self.GPIO = GPIO
        self.pin = pin
        self.GPIO.setmode(self.GPIO.BCM)
        self.GPIO.setup(pin, self.GPIO.OUT)

    def start(self):
        """ Start the buzzer. """
        self.GPIO.output(self.pin, self.GPIO.HIGH)

    def stop(self):
        """ Stop the buzzer. """
        self.GPIO.output(self.pin, self.GPIO.LOW)

    def destroy(self):
        self.GPIO.cleanup()

class PassiveBuzzer(BuzzerInterface):
    """ wrapper for controlling a passive buzzer
    """

    def __init__(self, pin):
        """
        :param pin: The pin number (in BCM) of the buzzer's input.
        :type pin: int
        """
        import RPi.GPIO as GPIO
        self.GPIO = GPIO
        self.pin = pin
        self.GPIO.setmode(self.GPIO.BCM)
        self.GPIO.setup(self.pin, self.GPIO.OUT)
        self.pwm = self.GPIO.PWM(self.pin, 1) # create pwm at 1Hz initially
        
    def start(self, frequency=2000, duty=50):
        """ Start the buzzer. 
        :param frequency: The frequency in Hz of the tone to play.
        :type frequency: int
        :param duty: The duty cycle of the waveform to play.
        :type duty: int
        """
        self.duty = duty
        self.frequency = frequency
        self.pwm.ChangeFrequency(frequency)
        self.pwm.start(duty)

    def stop(self):
        """ Stop the buzzer. """
        self.pwm.stop()

    def destroy(self):
        self.GPIO.cleanup()

class Notifier():
    """ wrapper for ringing a buzzer and sending notifications
    """
    def __init__(self, sensor, px, buzz, notify, buzzer=None):
        """
        :param sensor: The sensor.
        :type sensor: dict
        :param px: The preferred index (into the value/baseline list).
        :type sensor: int
        :param buzz: Whether to sound the buzzer above threshold.
        :type buzz: bool
        :param notify: Whether to send notifications above upper threshold.
        :type notify: bool
        :param buzzer: Optional buzzer device to sound above threshold.
        :type buzzer: Buzzer
        """
        from pushover import Client
        self.buzzer = buzzer
        self.triggered = False
        self.client = Client
        self.name = sensor.name
        self.short = sensor.short
        # lower, middle and upper alert thresholds
        self.t1 = sensor.thresholds[0] * sensor.baseline[px]
        self.t2 = sensor.thresholds[1] * sensor.baseline[px]
        self.t3 = sensor.thresholds[2] * sensor.baseline[px]
        self.buzz = buzz
        self.notify = notify
        self.host = System.get_hostname()

    def test_threshold(self, v):
        """ Send notifications based on a value compared to thresholds. 
        Assumes 3 thresholds.

        :param v: The value to compare to the thresholds.
        :type v: int
        """
        logging.debug('notifier: test_threshold: %s: %.2f %.2f %.2f %.2f' %
                      (self.name, v, self.t1, self.t2, self.t3))
        if(v < self.t1):
            if(self.buzzer and self.buzz):
                self.buzzer.stop()
        elif(v >= self.t1 and v < self.t2):
            if(self.buzzer and self.buzz):
                self.buzzer.stop()
        elif(v >= self.t2 and v < self.t3):
            if(self.buzzer and self.buzz):
                self.buzzer.start()
        # activate alarms above t3
        elif(v >= self.t3):
            if(self.buzzer and self.buzz): self.buzzer.start()
            if(self.notify and not self.triggered):
                self.client().send_message(
                    "%s detected %.2f > %.2f!" % (self.short, v, self.t3),
                    title="%s: %s alarm" % (self.host, self.name))
                self.triggered = True

        # clear any active alarms below t2
        if(v < self.t2 and self.notify and self.triggered):
            self.client().send_message(
                "%s clearing. %.2f < %.2f)" % (self.short, v, self.t2),
                title="%s: %s" % (self.host, self.name))
            self.triggered = False


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
        import RPi.GPIO as GPIO
        self.GPIO = GPIO
        self.colorpins = colorpins
        self.colors, self.pins = colorpins.keys(), colorpins.values()
        self.GPIO.setmode(self.GPIO.BCM)
        self.GPIO.setwarnings(False)
        logging.info('using GPIO pins to drive LEDs: ')
        # enable output and flash each pin in sequence
        for color, pin in colorpins.items(): 
            self.GPIO.setup(pin, self.GPIO.OUT)
            logging.info('led pin %d - %s ' % (pin, color))
            self.GPIO.output(pin, self.GPIO.HIGH)
            sleep(0.2)
            self.GPIO.output(pin, self.GPIO.LOW)
        self.light('green')

    def light(self, color):
        """ Light the specified led.
        :param color: The pin number (in BCM) of the led to light
        :type color: int
        """
        logging.debug('StatusLeds: light: %s' % color)
        self.GPIO.output(self.colorpins.get(color), self.GPIO.HIGH)

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
        logging.debug('StatusLeds: threshold: %.2f %.2f %.2f' %
                      (v, t1, t2))
        if(v < t1):               
            self.GPIO.output(self.colorpins.get('green'), self.GPIO.HIGH)
        elif(v >= t1 and v < t2):
            self.GPIO.output(self.colorpins.get('yellow'), self.GPIO.HIGH)
        elif(v >= t2):
            self.GPIO.output(self.colorpins.get('red'), self.GPIO.HIGH)

    def clear_all(self):
        """ Clear all leds. """
        self.GPIO.output(list(self.colorpins.values()), self.GPIO.LOW)

    def destroy(self):
        self.GPIO.cleanup()

class StatusLedsPwm():
    """ wrapper for controlling commonly used 4-led status bar
        used to indicate four relative levels of criticality.
        Order the lights by 'severity', e.g. red, ylw, grn, blu.
        Uses PWM to control brightness.
    """
    def __init__(self, colorpins, brightness=100):
        """
        :param colorpins: The pin numbers (in BCM) of the leds.
        :type colorpins: list
        """
        import RPi.GPIO as GPIO
        self.GPIO = GPIO
        self.colorpins = colorpins
        self.default_brightness = brightness
        self.colors, self.pins = colorpins.keys(), colorpins.values()
        self.pwms = {}
        self.GPIO.setmode(GPIO.BCM)
        self.GPIO.setwarnings(False)
        logging.info('using GPIO pins to drive LEDs: ')
        # enable output and flash each pin in sequence
        for color, pin in colorpins.items(): 
            self.GPIO.setup(pin, self.GPIO.OUT)
            logging.info('led pin %d - %s ' % (pin, color))
            self.pwms[color] = self.GPIO.PWM(pin, 1000)
            self.pwms[color].start(brightness)
            sleep(0.2)
        self.clear_all()
        self.light('green')

    def light(self, color, brightness=None):
        """ Light the specified led.
        :param color: The pin number (in BCM) of the led to light
        :type color: int
        :param brightness: The brightness from 0 to 100.
        :type brightness: int
        """
        logging.debug('StatusLedsPwm: light: %s' % color)
        if(brightness is None):
            brightness = self.default_brightness
        self.pwms[color].ChangeDutyCycle(brightness)

    def light_threshold(self, v, t1, t2, brightness=None):
        """ Light leds based on a value compared to thresholds. 
        Assumes 3 lights and 2 thresholds.

        :param v: The value to compare to the thresholds.
        :type v: int
        :param t1: The lower threshold.
        :type t1: int
        :param t2: The upper threshold.
        :type t2: int
        """
        logging.debug('StatusLedsPwm: threshold: %.2f %.2f %.2f' %
                      (v, t1, t2))

        if(brightness is None):
            brightness = self.default_brightness
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

    def destroy(self):
        self.GPIO.cleanup()

class DHT():
    """ dht11 temperature and humidity sensor wrapper
    .. note:: requires adafruit-circuitpython-dht, not Adafruit_DHT,
              also libgpiod2
    """
    def __init__(self, pin, type='11'):
        """
        :param pin: The pin number (in BCM) of the DHT data line.
        :type pin: int
        """
        import adafruit_dht
        if(type == '11'):
            self.dht = adafruit_dht.DHT11(pin)
        else:
            self.dht = adafruit_dht.DHT22(pin)

    def sense_data(self):
        """ Read the temperature and humidity from the DHT sensor.
        .. note:: RuntimeError is handled internally. DT11 read often fails.

        :return: the temperature in celsius, farenheit and the humidity.
        :rtype: (int, int, int)
        :raises: RuntimeError: when the DHT read fails
        """
        try:
            temperature_c = self.dht.temperature
            if(temperature_c is None): temperature_f = None
            else: temperature_f = temperature_c * (9 / 5) + 32
            humidity = self.dht.humidity
        except RuntimeError:
            # dht doesn't always succeed. continue.
            return(None, None, None, None)
        
        return(temperature_c, temperature_f, humidity, None)
    
    def sense_temperature(self):
        """ Read the temperature from the DHT sensor.
        :return: the temperature in farenheit
        :rtype: float
        """
        return self.sense_data()[1]

    def sense_humidity(self):
        """ Read the humidity from the DHT sensor.
        :return: the humidity.
        :rtype: float
        """
        return self.sense_data()[2]

class BME280():
    """ BME/BMP280 temperature and humidity sensor wrapper
    .. note:: requires adafruit-circuitpython-bme280
    """
    def __init__(self, address):
        """
        :param pin: The pin number (in BCM) of the DHT data line.
        :type pin: int
        """
        import busio
        import board
        import adafruit_bme280
        i2c = busio.I2C(board.SCL, board.SDA)
        self.bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=address)

    def sense_data(self):
        """ Read the temperature and humidity from the sensor.
        :return: the temperature in celsius, farenheit, humidity and pressure.
        :rtype: (int, int, int, int)
        """
        try:
            temperature_c = self.bme280.temperature
            if(temperature_c is None): temperature_f = None
            else: temperature_f = temperature_c * (9 / 5) + 32
            humidity = self.bme280.humidity
            pressure = self.bme280.pressure
        except RuntimeError:
            return(None, None, None, None)
        
        return(temperature_c, temperature_f, humidity, pressure)

    def sense_temperature(self):
        """ Read the temperature.
        :return: the temperature farenheit.
        :rtype: float
        """
        return self.sense_data()[1]

    def sense_humidity(self):
        """ Read the humidity.
        :return: the humidity.
        :rtype: float
        """
        return self.sense_data()[2]

    def sense_pressure(self):
        """ Read the pressure.
        :return: the pressure.
        :rtype: float
        """
        return self.sense_data()[3]

class BasicDisplay():
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

class MAX7219SevenSegDisplay(BasicDisplay):
    """ implementation for displaying textual data on a display device
    """
    def __init__(self, device=0, brightness=16, echo=False):
        """
        :param echo: Whether or not to echo writes to the logger.
        :type echo: bool
        """
        from luma.core.interface.serial import spi, noop
        from luma.core.virtual import viewport, sevensegment
        self.viewport = viewport
        self.sevensegment = sevensegment
        from luma.led_matrix.device import max7219
        
        self.echo = echo
        logging.info('looking for seven-segment on SPI bus')
        try:
            self.serial = spi(port=0, device=device, gpio=noop())
            self.device = max7219(self.serial, cascaded=1)
            self.seg = self.sevensegment(self.device)
            self.seg.device.contrast(brightness)
            logging.info('found display!')
        except:
            logging.error('SPI error')

        self.seg.text = 'init...'
        
    def _show_message_vp(self, msg, delay=0.1):
        """ virtual viewport """
        width = self.device.width
        padding = " " * width
        msg = padding + msg + padding
        n = len(msg)

        virtual = self.viewport(self.device, width=n, height=8)
        self.sevensegment(virtual).text = msg
        for i in reversed(list(range(n - width))):
            virtual.set_position((i, 0))
            sleep(delay)

    def clear(self):
        """ Clear the display. """
        pass

    def _shorten(self, message):
        """ a hack to compact different metrics to fit in 8 characters """
        message = message.strip(' \n')
        message = message.replace(' ', '')
        if(':' in message):
            metric = message.split(':')[0]
            body = message.split(':', 1)[1]
            if(metric == 'cpu' or metric == 'gpu' or metric == 'load'):
                return message.replace('C', '')
            if(metric == 'uptime'):
                return body[:-3]
            if(metric == 'ip'):
                return body
            return body
        else:
            return message

    def display(self, message, trace=None):
        """ Display a message.

        :param message: The message to display on the device.
        :type message: str
        :param trace: Ignored. sevensegs can't display graphical traces.
        :type trace: bool
        """
        # shorten messages for display on seven segment
        message = self._shorten(message)
        # right-justify
        if('..' not in message): 
            message = message.rjust(self.seg.device.width +
                                    message.count('.'), ' ')
        # scroll if too wide (.'s don't count!)
        if(len(message.replace('.', '')) > self.seg.device.width):
            self._show_message_vp(message)
        # display if narrow enough
        else:
            self.seg.text = message
            
        if(self.echo):
            logging.info(message)

    def destroy(self):
        """ Clean up the display. """
        pass

class LumaDisplay(BasicDisplay):
    """ implementation for displaying text/graphics on a device supported 
        by the luma project
    """
    def __init__(self, width, height, rotate=0,
                 trace_height=16, echo=False,
                 font=None, color='White', trace_color='Yellow',
                 i2c_addr=0x3c, device=0):
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
        :param i2c_addr: Address of the device on the i2c bus (if applicable).
        :type i2c_addr: int
        """
        # display device-specific setup, creates self.device
        from luma.core.render import canvas
        self.canvas = canvas
        self._setup(rotate, width, height, device=device)
        self.device.clear()
        logging.info('OLED found')
        self.device.clear()
        self.echo = echo
        self.font = font
        self.color = color
        self.trace_color = trace_color
        self.x = self.device.width
        self.y = self.device.height
        self.trace_height = trace_height

    def clear(self):
        """ Clear the display. """
        self.device.clear()

    def _graph(self, draw, trace):
        """
        auxiliary method invoked by display() when trace data is provided
        for graphical display.
        """
        NZ = .001 # negligible non-zero value to prevent div0 when max == min
        mxx = max(trace)
        mnx = min(trace)
        delta = mxx - mnx + NZ
        for xp in range(len(trace)):
            draw.line((xp, self.y,
                       xp, self.y - (trace[xp] - mnx) *
                           self.trace_height / delta),
                       fill=self.trace_color)
            
    def display(self, message, trace=None):
        """ Display a message.

        :param message: The message to display on the device.
        :type message: str
        :param trace: The trace data to graph.
        :type trace: list
        """
        with self.canvas(self.device) as draw:
            draw.text((0, 0), message, fill=self.color, font=self.font)
            if(trace is not None and len(trace) > 0):
                self._graph(draw, trace)
        if(self.echo):
            logging.info(message)
            
    def display_trace(self, trace=None):
        """ Display a trace.
        :param trace: The trace data to graph.
        :type trace: list
        """
        with self.canvas(self.device) as draw:
            if(trace is not None and len(trace) > 0):
                self._graph(draw, trace)

    def destroy(self):
        """ Clean up the display. """
        self.device.cleanup()

class ILI9341Display(LumaDisplay):
    def _setup(self, rotate, width, height, device=0, i2c_addr=None):
        from luma.core.interface.serial import spi, noop
        from luma.lcd.device import ili9341 as led
        
        logging.info('looking for LED on SPI bus')
        serial = spi(port=0, device=device, gpio_DC=23, gpio_RST=24,
                     bus_speed_hz=32000000)
        self.device = led(serial, gpio_LIGHT=25, active_low=False,
                          rotate=rotate)
        self.device.backlight(True)

class SSD1306Display(LumaDisplay):
    def _setup(self, rotate, width, height, i2c_addr=0x3C, device=0):
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306 as led
        logging.info('looking for OLED on i2c bus at %x' % i2c_addr)
        serial = i2c(port=1, address=i2c_addr)
        self.device = led(serial, height=height, width=width, rotate=rotate)

class MAX7219Display(LumaDisplay):
    # note: !!! need to expose orientation, rotate, intensity, etc?
    def _setup(self, rotate, width, height, device=0):
        from luma.core.interface.serial import spi, noop
        from luma.led_matrix.device import max7219 as led
        logging.info('looking for matrix on spi..')
        serial = spi(port=0, device=device, gpio=noop())
        self.device = led(serial, cascaded=4,
                          block_orientation=90,
                          rotate=0,
                          blocks_arranged_in_reverse_order=True)
        self.device.contrast(1)

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
    def display_formatted(self, label, sformat, value):
        """ Display a formatted message. Overrides formatted display
        to change delimeter.

        :param label: The label for the value to be displayed.
        :type label: str
        :param sformat: The formatting string for the value.
        :type sformate: str
        :param value: The value to display.
        :type value: numeric
        """
        if(value is not None):
            self.display(label + ', ' + sformat % value)
        else:
            self.display(label + ', Error')

    def display(self, message):
        """ Display a message.

        :param message: The message to display in the logs.
        :type message: str
        """
        logging.info(message)

class SensorLog():
    """ implementation for writing sensor data to file
    """
    def __init__(self, filename, echo=False):
        """
        :param echo: Whether or not to echo writes to the logger.
        :type echo: bool
        """
        self.echo = echo
        self.file = open(filename, 'a')
        
    def write(self, label, values, vformat='%s'):
        """ Write formatted data value(s) to the file.
        :param label: The label for the value to be logged.
        :type label: str
        :param vformat: The formatting string for the value.
        :type vformate: str
        :param values: The value(s) to log.
        :type values: numeric
        """
        t = format('%s, %s, ' % (System.get_datetime(), label) + 
                   vformat % values + '\n')
        if(values is not None): # ignore non-existent data
            self.file.write(t)
            # self.file.flush() # for debugging
        if(self.echo):
            logging.info(t)

    def write_message(self, message):
        """ Write a message to the file. Caller performs formatting.
        :param message: The formatted message to be logged.
        :type message: str
        """
        t = format('%s, %s\n' % (System.get_datetime(), message))
        self.file.write(t)
        if(self.echo):
            logging.info(t)
            
    def destroy(self):
        """ Clean up the file resources. """
        self.file.close

class System():
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
        seconds = int( ts - days * sd - hours * sh - minutes * sm)
        return(days, hours, minutes, seconds)

    @staticmethod
    def get_uptime_str():
        return('%dd %02d:%02d:%02d' % System.get_uptime())

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
        return '{:%Y-%m-%d %H:%M:%S.%f}'.format(datetime.now())

    @staticmethod
    def get_timestamp():
        """
        :return: The timestamp for the current time.
        :rtype: int
        """
        return datetime.now().timestamp()

class Sensor():
    """
    An encapsulation of a sensor with attributes for normalizing its
    output and other features, particularly for MQ-series gas sensors.
    """
    def __init__(self, sensor_file, sensor_type):
        """
        :param sensor_file: The file containing sensor info.
        :type sensor_file: str
        :param sensor_type: The type of the sensor, e.g. "MQ6"
        :type sensor_type: str
        """
        logging.debug('%s: reading sensor: %s' %
                      (sensor_file, str(sensor_type)))
        with open(sensor_file) as jsonfile:
            self.sensors = json.load(jsonfile)
        self.key = Sensor.fix_name(sensor_type)
        self.sensor = self.sensors[self.key]
        self.name = self.sensor['name']
        self.short = self.sensor['short']
        self.description = self.sensor['long']
        # if there aren't any thresholds, skip along with baselines
        if('thresholds' in self.sensor):
            self.thresholds = self.sensor['thresholds']
            self.baseline = self.sensor['baseline']
            self.baseline_r = self.sensor['baseline'][0]
            self.baseline_v = self.sensor['baseline'][1]
        else:
            self.thresholds, self.baseline = None, None
            self.baseline_r, self.baseline_v = None, None

    @staticmethod
    def fix_name(unformatted_type):
        return unformatted_type.lower().replace('-', '')

class ADS1115:
    """ ADS11x5 analog/digital converter
    .. note:: requires adafruit-circuitpython-ads1x15
    """
    def __init__(self, address):
        """
        :param addr: The i2c address of the sensor.
        :type addr: int
        """
        import busio
        import board
        import adafruit_ads1x15.ads1115 as ADS
        from adafruit_ads1x15.analog_in import AnalogIn
        i2c = busio.I2C(board.SCL, board.SDA)
        self.ads =  ADS.ADS1115(i2c, address=int(address, 16))
        self.adcs = [AnalogIn(self.ads, ADS.P0),
                     AnalogIn(self.ads, ADS.P1),
                     AnalogIn(self.ads, ADS.P2),
                     AnalogIn(self.ads, ADS.P3)]

    def read_values(self, channel):
        """
        :param channel: The channel to read.
        :type channel: int
        """
        raw = self.adcs[channel].value
        voltage = self.adcs[channel].voltage
        return raw, voltage

    def read_raw(self, channel):
        """
        :param channel: The channel to read.
        :type channel: int
        """
        return self.adcs[channel].value

    def read_voltage(self, channel):
        """
        :param channel: The channel to read.
        :type channel: int
        """
        return self.adcs[channel].voltage


