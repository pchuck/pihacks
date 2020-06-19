#!/usr/bin/env python3
#
# audio_viz_luma.py
#
# real-time visualization of audio on raspberry pi using luma
# currently only supports max7219 led array
#
# Requires python libraries: luma.core, luma.led-matrix, pyaudio
# system libs: libportaudio0 libportaudio2 libportaudiocpp0 portaudio19-dev
#
# To list available input devices:
#   arecord -l
#
# Notes on (alsa) audio/mic tweaks to optimize the display:
#   amixer sset 'Input Mux' 'Mic'
#   amixer sset 'Mic' toggle
#   amixer sset 'Mic Boost' 1
#
# If the input device is not default, use '-c' to specify the card, e.g.
#   amixer -c 1 sset 'Mic' toggle
#
# To set the microphone gain of the non-default device.
#   amixer -c 1 sset Mic Capture 350
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
#
import sys
import math
from random import randrange
import argparse
import pyaudio
import wave
from luma.core.render import canvas
from PIL import Image, ImageDraw

# init audio
def init_audio(resolution, sample_rate, channels, audio_id, chunk_size):
    print('initializing audio..')
    audio = pyaudio.PyAudio() # create pyaudio instantiation
    stream = audio.open(format=resolution, rate=sample_rate, channels=channels,
                        input_device_index=audio_id, input=True,
                        frames_per_buffer=chunk_size)
    return(audio, stream)

#
# initialize and return the new display device handle
#
def init_display(device, n, block_orientation, rotate, inreverse, intensity,
                 device_id=0):
    # max7219, via SPI
    if(device.lower() == 'max7219'):
        from luma.core.interface.serial import spi, noop
        from luma.led_matrix.device import max7219 as led
        
        serial = spi(port=0, device=device_id, gpio=noop())
        # spi_bus_speed = 8000000 # max: 32000000
        device = led(serial, cascaded=n, block_orientation=block_orientation,
                     rotate=rotate, blocks_arranged_in_reverse_order=inreverse)
        device.contrast(intensity)

    # ili9341, via SPI
    elif(device.lower() == 'ili9341'):
        from luma.core.interface.serial import spi, noop
        from luma.lcd.device import ili9341 as lcd
        # note: would be nice to parameterize other DC and RST wiring options
        serial = spi(port=0, device=device_id, gpio_DC=24, gpio_RST=23,
                     bus_speed_hz=32000000)
        device = lcd(serial, gpio_LIGHT=25, active_low=False)
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
def render(draw, color, width, height, trace, sideways=False):
    if(sideways):
        for c in range(width):
            draw.line((height, c, height - trace[c], c), fill=color)
    else:
        for c in range(width):
            draw.line((c, height, c, height - trace[c]), fill=color)

# stream/capture/viz
def capture_and_viz(v_dev, a_dev, a_stream,
                    ar, # audio resolution (e.g. 16-bit)
                    color, width, height, sideways=False):

    # whether the visualization is rotated 90 degrees; width/height swapped
    if(sideways is True):
        t = width; width = height; height = t
        
    print('capturing and visualizing..')
    # compute the number of bits in the height (or width) resolution
    vr = math.log(height) / math.log(2) # solving 2^vr = height, for vr
    
    # sound to video scaling
    # the number of bits to shift an audio value to get a video height value
    # e.g. diff between 'ar' (audio resolution) and 'vr' (height 'resolution')
    rshift = int(ar - vr)
    
    # shift one less bit so that the display is more sensitive
    # note: this may need to change based on microphone sensitivity
    # or gain, but seems to yield aesthetic results, so far
    rshift -= 1
    print("shifting audio samples by %d (2^%d audio -> %d display height).."
          % (rshift, ar, height))
    
    trace = list(range(width)) # current display trace
    col = 0 # current display column in the display trace
    # stream
    try:
        # continually read stream and append audio chunks to frame array
        while(True):
            data = a_stream.read(chunk, exception_on_overflow = False)
            # (for debugging, sim 16-bit results)
            #   data = [randrange(256), randrange(256) ]
            val = int.from_bytes(data, "big") # extract a value
            level = val >> rshift # e.g. scale from 65K to 16
            if(level < height + 1):
                trace[col] = level
                col += 1
                if(col == width):
                    col = 0
                    with canvas(v_dev) as draw:
                        render(draw, color, width, height, trace, sideways)

    except KeyboardInterrupt:
        print("cleaning up.. ")
        a_stream.stop_stream()
        a_stream.close()
        a_dev.terminate()
        pass


## argument parsing
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='audio_viz_luma arguments',
                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # hardware constants
    parser.add_argument('--device', '-dv', type=str, default='max7219',
        choices=['max7219', 'ssd1306', 'ili9341'],
        help='The type of device')
    parser.add_argument('--device-id', '-di', type=int, default=0,
        help='The SPI device id (e.g. CE0, CE1) to address.')
    parser.add_argument('--cascaded', '-n', type=int, default=1,
        help='Number of cascaded LED matrices (usu. max7219)')
    parser.add_argument('--block-orientation', '-bo', type=int, default=0,
        choices=[0, 90, -90],
        help='Corrects block orientation when wired vertically')
    parser.add_argument('--rotate', '-rot', type=int, default=0,
        choices=[0, 1, 2, 3],
        help='Rotate display 0=0°, 1=90°, 2=180°, 3=270°')
    parser.add_argument('--reverse-order', '-ro', type=bool, default=False,
        help='Set to true if blocks are in reverse order')
    parser.add_argument('--intensity', '-i', type=int, default=128,
        help='The intensity of the LED output (from 0..255)')
    # visualization options
    parser.add_argument('--color', '-c', type=str, default='White',
        help='The color of the display (if applicable)')
    parser.add_argument('--sideways', '-s', type=bool, default=False,
        help='Whether to draw the visualization \"sidways\"')
    parser.add_argument('--audio-id', '-aid', type=int, default=0,
        help='The alsa device id of the microphone or sampling device')
    parser.add_argument('--sample-rate', '-sr', type=int, default=48000,
        help='The audio sample rate in Hz')
    # required positional arguments
    parser.add_argument('x', type=int, # required!
        help='The x resolution of the display/matrix')
    parser.add_argument('y', type=int, # required!
        help='The y resolution of the display/matrix')

    args = parser.parse_args()
    try:
        v_dev = init_display(args.device,
                             args.cascaded,
                             args.block_orientation,
                             args.rotate,
                             args.reverse_order,
                             args.intensity,
                             device_id=args.device_id
        )

        ar, ares = 16, pyaudio.paInt16 # audio resolution, in bits
        chans = 1 # mono
        chunk = 1 # rather than, say, a 4K buffer, capture 1 at a time
        aid = args.audio_id # use p.get_device_info_by_index() to find
        srate = args.sample_rate # sample rate in Hz
        (a_dev, a_stream) = init_audio(ares, srate, chans, aid, chunk)

        # process
        capture_and_viz(v_dev, a_dev, a_stream, ar, args.color, args.x, args.y,
                        sideways=args.sideways)

        
    except KeyboardInterrupt:
        pass

##
