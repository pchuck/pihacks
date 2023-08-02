# micropython scripts and control targets
# for raspberry pi pico
#
# prerequisites
#   % python3 -m pip install --user rshell
#
ROMPATH=../Pico_roms # firmware store
BOOTPATH=/Volumes/RPI-RP2 # mounted device bootloader path
#DEV=/dev/ttyACM0
DEV=/dev/cu.usbmodem1442301 # device
PARAMS=--buffer-size 512 # rshell parameters
MAIN=pico_sketch.py # main script

# list available devices (use to set 'DEV')
find:
	rshell -l

# install the python application to the pico to autostart
install:
	rshell -p $(DEV) $(PARAMS) cp $(MAIN) /pyboard/main.py

# connect shell to pico
# once connected, to see installed files
#   % ls /pyboard
shell:
	rshell -p $(DEV)

# factory reset
# requires the device to be in bootloader mode
nuke:
	cp $(ROMPATH)/flash_nuke.uf2 $(BOOTPATH)

# install the pico python environment to the pico
# requires the device to be in bootloader mode
flash:
	cp $(ROMPATH)/rp2-pico-20230426-v1.20.0.uf2 $(BOOTPATH)
