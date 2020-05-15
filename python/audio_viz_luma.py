#!/usr/bin/env python3
#
# audio_viz_luma.py
#
# real-time visualization of audio on raspberry pi using luma
# currently only supports max7219 led array
#
# Uses the luma libraries: luma.core, luma.led-matrix, 
# and requires pyaudio
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
#
import sys
from random import randrange
import pyaudio
import wave
from luma.core.render import canvas


# init audio
def init_audio(resolution, sample_rate, channels, audio_index, chunk_size):
    print('initializing audio..')
    audio = pyaudio.PyAudio() # create pyaudio instantiation
    stream = audio.open(format=resolution, rate=sample_rate, channels=channels,
                        input_device_index=audio_index, input=True,
                        frames_per_buffer=chunk_size)
    return(audio, stream)

def rx(draw):
    draw.line((0, 0, 32, 8), fill='White')

#
# initialize and return the new display device handle
#
def init_display(device, n, block_orientation, rotate, inreverse, intensity):
    # max7219, via SPI
    if(device.lower() == 'max7219'):
        from luma.core.interface.serial import spi, noop
        from luma.led_matrix.device import max7219 as led
        
        serial = spi(port=0, device=0, gpio=noop())
        # spi_bus_speed = 8000000 # max: 32000000
        device = led(serial, cascaded=n, block_orientation=block_orientation,
                     rotate=rotate, blocks_arranged_in_reverse_order=inreverse)
        device.contrast(intensity)

    # ili9341, via SPI
    elif(device.lower() == 'ili9341'):
        from luma.core.interface.serial import spi, noop
        from luma.lcd.device import ili9341 as lcd
        serial = spi(port=0, device=0, gpio_DC=23, gpio_RST=24,
                     bus_speed_hz=32000000)
        device = lcd(serial, gpio_LIGHT=18, active_low=False)
        # , pwm_frequency=50) # this appears to be broken
        device.backlight(True)
        device.clear()

    # ssd1306, via I2C
    elif(device.lower() == 'ssd1306'): 
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306 as led
       
        serial = i2c(port=1, address=0x3C)
        device = led(serial)

    else:
        sys.exit('unsupported display device: ' + device)

    return device

# render
def render(draw, width, height, trace):
    for c in range(width):
        # offset origin below axis (-1) so that total silence doesn't register
        draw.line((c, -1, c, trace[c] - 1), fill='White')

# stream/capture/viz
def capture_and_viz(v_dev, a_dev, a_stream, width, height):
    print('capturing and visualizing..')
    # max_level = 0 # track peak recorded level (for range validation)
    trace = list(range(width)) # current display trace
    col = 0 # current display column
    
    # stream
    try:
        # continually read stream and append audio chunks to frame array
        while(True):
            data = a_stream.read(chunk, exception_on_overflow = False)
            val = int.from_bytes(data, "big") # extract a value
            level = val >> 12 # scale from 65K to 16
            # if(level > max_level): max_level = level
            if(level < height + 1):
                trace[col] = level
                col += 1
                if(col == width):
                    col = 0
                    with canvas(v_dev) as draw:
                        render(draw, width, height, trace)
                        #rx(draw)

    except KeyboardInterrupt:
        # print("max: " + str(max_level))
        print("cleaning up.. ")
        a_stream.stop_stream()
        a_stream.close()
        a_dev.terminate()
        pass

device = 'max7219'
cascades = 4
orientation = 90
rotate = 0
inreverse = True
intensity = 1
v_dev = init_display(device, cascades, orientation, rotate, inreverse,
                     intensity)

res = pyaudio.paInt16 # 16-bit resolution
chans = 1 # mono
samp_rate = 12000 # 12K rather than 44.1KHz is sufficient here
chunk = 1 # rather than a, say, 4K buffer. capture 1 at a time
audio_index = 2 # device index found by p.get_device_info_by_index(ii)
(a_dev, a_stream) = init_audio(res, samp_rate, chans, audio_index, chunk)

width = 32
height = 8
capture_and_viz(v_dev, a_dev, a_stream, width, height)

