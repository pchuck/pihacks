#!/usr/bin/env python3
#
# sev_seg_effects.py
#
# Various visual effects renderable on seven segment displays.
# Uses both the luma matrix device and seg abstractions.
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
#
import os
import socket
import time
import random
import string
from datetime import datetime
import argparse
from luma.core.interface.serial import spi, noop
from luma.led_matrix.device import max7219 as led
from luma.core.render import canvas
from luma.core.virtual import sevensegment

# segment id's - y-coords and their corresponding segments
# 7 - .
# 6 - top bar
# 5 - right top bar
# 4 - right bottom bar
# 3 - bottom bar
# 2 - left bottom bar
# 1 - left top bar
# 0 - middle bar

def init_device(port=0, device_id=0, cascaded=1, contrast=127):
    '''Initialize both the raw matrix device and sevensegment abstraction.
       Each is used by the different effects generated below.
    '''
    serial = spi(port=port, device=device_id, gpio=noop())
    device = led(serial)
    seg = sevensegment(device)
    device.contrast(contrast)
    return device, seg

fluid_r = {7: {  1: [3, 2]},  6: {  0: [5],  1: [6, 1]},
           5: {  1: [6, 0]},  4: {  0: [7],  1: [0, 3]},
           3: {  0: [4, 7]},  2: {  0: [0, 3]},
           1: {  0: [0, 6]},  0: {  0: [5, 4],  1: [0]}}

fluid_l = {7: {  0: [4, 3]}, 6: {  -1: [5, 6],
                 0: [1] },   5: {   0: [6, 0]},
           4: {  0: [0, 3]}, 3: {   0: [2],
                -1: [7]},    2: {  -1: [0, 7]},
           1: { -1: [6, 0]}, 0: {   0: [1, 2], -1: [0]}}

def sev_seg_fluid(device, t, delay):
    x = device.width - 1
    f = fluid_r
    y = random.randrange(device.height)
    for c in range(int(t / delay)):
        with canvas(device) as draw:
            draw.point((x, y), fill='white')
            digit_inc = random.choice(list(f[y].keys()))
            x -= digit_inc
            y = random.choice(f[y][digit_inc])
            if(x < 0): f = fluid_l
            if(x > device.width): f = fluid_r
            
        time.sleep(delay)

def render_segments(device, x, segment_sequence, forward, delay):
    '''Given a list of segments, activate each in sequence.
       See above for the mapping of id to segment.
    '''
    for y in segment_sequence:
        with canvas(device) as draw:
            draw.point((x, y), fill='white')
            time.sleep(delay)
    
def sev_seg_snake_t1(device, loop=1, delay=0.05):
    def render(forward=False):
        # the traversal order of segments to produce 'snake' pattern
        evn_seg_traverse = [6, 5, 0, 2, 3, 7]
        odd_seg_traverse = [3, 4, 0, 1, 6]
        xcoords = list(range(device.width))
        xs = xcoords[::-1] if forward else xcoords
        s1 = evn_seg_traverse if forward else evn_seg_traverse[::-1]
        s2 = odd_seg_traverse if forward else odd_seg_traverse[::-1]
        for x in xs:
            seq =  s1 if x % 2 == 0 else s2
            render_segments(device, x, seq, forward, delay)
    for i in range(loop):
        # for each loop, traverse forward and back
        render(forward=True)
        render(forward=False)
        
def sev_seg_snake_t2(device, loop=1, delay=0.05):
    def render(forward=False):
        seq_traverse = [7, 4, 0, 1, 6, 5, 0, 2, 3, 7]
        xcoords = list(range(device.height))
        xs = xcoords[::-1] if forward else xcoords
        ss = seq_traverse if forward else seq_traverse[::-1]
        for x in xs:
            render_segments(device, x, ss, forward, delay)
    for i in range(loop):
        render(forward=True)
        render(forward=False)

def sev_seg_counter(seg, t, delay=0.05):
    for c in range(int(t / delay)):
        seg.text = str(c).rjust(seg.device.width, ' ')
        time.sleep(delay)

def sev_seg_powers(seg, base, t, delay=0.05):
    power = 0
    for c in range(int(t / delay)):
        result = str(base ** power).rjust(seg.device.width, ' ')
        if(len(result) > seg.device.width):
            break
        seg.text = result
        power += 1

        time.sleep(delay)

def sev_seg_random_chars(seg, t, delay=0.05, choices=string.ascii_letters):
    for c in range(int(t / delay)):
        seg.text = ''.join(random.choices(choices, k=seg.device.width))
        time.sleep(delay)

def sev_seg_waves(device, t, delay=0.05, reverse=False):
    t1 = random.sample(range(0, device.height), device.width)
    t2 = random.sample(range(0, device.height), device.width)
    def update_trace(trace):
        trace.pop(0)
        trace.append(random.randrange(device.height + 1))
        return trace

    for c in range(int(t / delay)):
        with canvas(device) as draw:
            for x in range(device.width):
                y1 = t1[x]; y2 = t2[x]
                w = device.width
                if(reverse):
                    draw.line((y1, w - x - 1, y2, w - x - 1), fill='white')
                else:
                    draw.line((w - x - 1, y1, w - x - 1, y2), fill='white')
                
                t1 = update_trace(t1); t2 = update_trace(t2)
            time.sleep(delay)

def sev_seg_expl(seg, t, delay=0.05):
    ms = [
        '        ',
        '   --   ',
        '  =  =  ',
        ' X-  -X ',
        '#/ oo \#']
    for c in range(int(t / delay / len(ms) / 2)):
        for m in ms:
            seg.text = m
            time.sleep(0.1)
        for m in ms[::-1]:
            seg.text = m
            time.sleep(0.1)

def sev_seg_date(seg, t):
    now = datetime.now()
    seg.text = now.strftime("%y-%m-%d")
    time.sleep(t)

def sev_seg_clock(seg, t):
    interval = 0.5
    for i in range(int(t / interval)):
        dot = '-' if i % 2 else ' '
        seg.text = datetime.now().strftime('%H' + dot + '%M' + dot + '%S')
        time.sleep(interval)

def sev_scroll_str(seg, msg, reverse=False, delay=0.05):
    width = seg.device.width
    padding = " " * width
    msg = padding + msg + padding

    for i in range(len(msg)):
        seg.text = msg[i:i + width][::-1] if reverse else msg[i:i + width]
        time.sleep(delay)

def sev_seg_cpu(seg, t, delay=0.05):
    for i in range(int(t / delay)):
        tmp = open('/sys/class/thermal/thermal_zone0/temp')
        cpu = tmp.read()
        tmp.close()
        seg.text = 'cpu %.1fC' % (float(cpu) / 1000.0)
        time.sleep(delay)

def sev_seg_gpu(seg, t, delay=0.05):
    for i in range(int(t / delay)):
        cmd = os.popen('vcgencmd measure_temp').read()
        cmd = cmd.replace('temp=', '')
        cmd = cmd.replace('\'', '')
        cmd = cmd.replace('\n', '')
        seg.text = 'gpu %s' % cmd
        time.sleep(delay)

def sev_seg_load(seg, t, delay=0.05):
    for i in range(int(t / delay)):
        seg.text = 'load %.2f' % os.getloadavg()[0]
        time.sleep(delay)

def sev_seg_free(seg, t, delay=0.05):
    for i in range(int(t / delay)):
        cmd = os.popen('free | awk \'FNR == 2 {print $4/1000}\'').read()
        seg.text = ('%.0f MB' % float(cmd)).rjust(seg.device.width, ' ')
        time.sleep(delay)

def sev_seg_ip(seg, t, delay=0.05):
    for i in range(int(t / delay)):
        try: 
            ip = socket.gethostbyname(socket.gethostname())
            seg.text = ip.rjust(seg.device.width + 3, ' ')
        except socket.gaierror:
            pass # ignore
        time.sleep(delay)

try:
    parser = argparse.ArgumentParser(description='sev_seg_effects',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--device-id', type=int, default=0,
                        choices=[0, 1],
                        help='The SPI device id to use.')
    args = parser.parse_args()

    device, seg = init_device(device_id=args.device_id, contrast=1)

    while(True):
        sev_seg_clock(seg, t=2)
        sev_seg_fluid(device, t=1.8, delay=0.05)
        
        sev_seg_date(seg, t=2)
        sev_seg_powers(seg, 2, t=2, delay=0.05)
        
        sev_seg_ip(seg, t=3, delay=0.2)
        sev_seg_random_chars(seg, t=1, choices=string.punctuation,
                             delay=0.05)
        
        sev_seg_free(seg, t=3, delay=0.2)
        sev_seg_random_chars(seg, t=1, choices=string.ascii_lowercase,
                             delay=0.05)
        
        sev_seg_load(seg, t=3, delay=0.2)
        sev_seg_random_chars(seg, t=1, choices=string.ascii_uppercase,
                             delay=0.05)
        
        sev_seg_cpu(seg, t=3, delay=0.2)
        sev_seg_random_chars(seg, t=1, choices=string.ascii_letters,
                             delay=0.05)
        
        sev_seg_gpu(seg, t=3, delay=0.2)
        sev_seg_random_chars(seg, t=1, choices=string.printable, delay=0.05)
        
        sev_seg_snake_t1(device, loop=1, delay=0.02)
        sev_seg_waves(device, t=1, delay=0.05)

        # sev_seg_random_chars(seg, t=1, choices=string.hexdigits, delay=0.05)
        # sev_seg_random_chars(seg, t=1, choices=string.digits, delay=0.05)

        # sev_seg_snake_t2(device, loop=1, delay=0.02)
        # sev_seg_counter(seg, t=2, delay=0.05)
        # sev_scroll_str(seg, string.ascii_lowercase, delay=0.05)
        # sev_scroll_str(seg, string.ascii_lowercase, delay=0.05, reverse=True)
        # sev_seg_expl(seg, t=0.5, delay=0.05)

except KeyboardInterrupt:
    pass
