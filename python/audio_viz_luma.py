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
import pyaudio
import wave
from random import randrange

from luma.core.render import canvas
from luma.core.interface.serial import spi, noop
from luma.led_matrix.device import max7219 as led


# init audio
def init_audio(resolution, sample_rate, channels, audio_index, chunk_size):
    print('initializing audio..')
    audio = pyaudio.PyAudio() # create pyaudio instantiation
    stream = audio.open(format=resolution, rate=sample_rate, channels=channels,
                        input_device_index=audio_index, input=True,
                        frames_per_buffer=chunk_size)
    return(audio, stream)

# display device initialization
def init_display(port, index, bus_speed, n, orientation, rotate, inreverse,
                 intensity):
    print('initializing display..')
    serial = spi(port=port, device=index, gpio=noop(),
                 bus_speed_hz=bus_speed)
    device = led(serial, cascaded=n, block_orientation=orientation,
                 rotate=rotate, blocks_arranged_in_reverse_order=inreverse)
    device.contrast(intensity)
    return(device)

# render
def render(draw, trace):
    for c in range(width):
        # move origin below axis so that silence doesn't register
        draw.line((c, -1, c, trace[c] - 1), fill='White')

# stream/capture/viz
def capture_and_viz(audio, stream, width, height):
    print('capturing and visualizing..')
    # max_level = 0 # track peak recorded level (for range validation)
    trace = list(range(width)) # current display trace
    col = 0 # current display column

    # stream
    try:
        # continually read stream and append audio chunks to frame array
        while(True):
            data = stream.read(chunk, exception_on_overflow = False)
            val = int.from_bytes(data, "big") # extract a value
            level = val >> 12 # scale from 65K to 16
            # if(level > max_level): max_level = level
            if(level < height + 1):
                trace[col] = level
                col += 1
                if(col == width):
                    col = 0
                    with canvas(device) as draw:
                        render(draw, trace)

    except KeyboardInterrupt:
        # print("max: " + str(max_level))
        print("cleaning up.. ")
        stream.stop_stream()
        stream.close()
        audio.terminate()
        pass


res = pyaudio.paInt16 # 16-bit resolution
chans = 1 # mono
samp_rate = 12000 # 12K rather than 44.1KHz is sufficient here
chunk = 1 # rather than a, say, 4K buffer. capture 1 at a time
audio_index = 2 # device index found by p.get_device_info_by_index(ii)

(audio, stream) = init_audio(res, samp_rate, chans, audio_index, chunk)

spi_port = 0
spi_index = 0
spi_bus_speed = 4000000 # max: 32000000
cascades = 4
orientation = 90
rotate = 0
inreverse = True
intensity = 1

device = init_display(spi_port, spi_index, spi_bus_speed,
                     cascades, orientation, rotate, inreverse, intensity)

width = 32
height = 8

capture_and_viz(audio, stream, width, height)

