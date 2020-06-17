#!/usr/bin/env python3
#
# sev_seg_message.py
#
# simple utility to display given message on a seven segment display.
#
# Copyright (C) 2020, Patrick Charles
# Distributed under the Mozilla Public License
# http://www.mozilla.org/NPL/MPL-1.1.txt
#
import time
import argparse
from luma.core.interface.serial import spi, noop
from luma.core.virtual import sevensegment
from luma.led_matrix.device import max7219


parser = argparse.ArgumentParser(description='sev_seg_message',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('--device-id', type=int, default=0, choices=[0, 1],
                    help='The SPI device id to use.')
parser.add_argument('--delay', type=int, default=1, 
                    help='The number of seconds to persist the message.')
parser.add_argument('message', type=str, 
                    help='The message to display')

args = parser.parse_args()

serial = spi(port=0, device=args.device_id, gpio=noop())
device = max7219(serial, cascaded=1)
seg = sevensegment(device)
seg.device.contrast(1)
seg.text = args.message

time.sleep(1)
