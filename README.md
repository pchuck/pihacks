# pihacks
raspberry pi tools/scripts


== Prerequisites ==

* A Raspberry Pi v1, v2, v3, v4 or Zero
* An installed Raspberry Pi distribution, such as 'Raspbian'
* python3 installed (included with Raspbian)
* SPI enabled in /boot/config.txt (see https://max7219.readthedocs.io/en/0.2.3/)
* luma.core python packages pip installed (if not included)
* A max2719 LED matrix, or other serial controlled display, wired to the GPIO ports, as follows (from 2719 pin -> Raspberry Pi GPIO pin):
  * p1 VCC -> RPi p2 5V0
  * p2 GND -> RPi p6 GND
  * p3 DIN -> RPi p19 GPIO 10 (MOSI)
  * p4 CS ->  RPi p24 GPIO 8 (SPI CE0)
  * p5 CLK -> RPi p23 GPIO 11 (SPI CLK)


== LED Swarm ==

To run the 'swarm' animation

* python/led_swarm.py

e.g. To simulate a swarm of 10 elements on 4 cascaded 8x8 LED matrics, oriented sideways and chained backwards:

* python/led_swarm.py --cascaded=4 --block-orientation=90 --reverse-order=True 32 8 10


== LED Text ==

To display a scrolling text message

* python/led_text.py 'your message'

