# pihacks
raspberry pi tools/scripts


== Prerequisites ==

* A Raspberry Pi v1, v2, v3, v4 or Zero
* An installed Raspberry Pi distribution, such as 'Raspbian'
* python3 installed (included with Raspbian)
* luma.core python packages pip installed (if not included)
* A max2719 LED matrix, or other serial controlled display, wired to the GPIO ports, as follows:
  * 2719 p1 VCC -> RPi GPIO p2 5V0
  * 2719 p2 GND -> RPi GPIO p6 GND
  * 2719 p3 DIN -> RPi TPIO p10 (MOSI)
  * 2719 p4 CS -> RPi GPIO p8 (SPI CS0)
  * 2719 p5 CLK -> RPi GPIO p11 (SPI CLK)


== LED Swarm ==

To run the 'swarm' animation

* python/led_swarm.py

e.g. To simulate a swarm of 10 elements on 4 cascaded 8x8 LED matrics, oriented sideways and chained backwards:

* python/led_swarm.py --cascaded=4 --block-orientation=90 --reverse-order=True 32 8 10


== LED Text ==

To display a scrolling text message

* python/led_text.py 'your message'

