# micropython scripts and control targets
# for raspberry pi pico
#
# prerequisites
#   % python3 -m pip install --user rshell
#
BOOTDEV=/Volumes/RPI-RP2
#DEV=/dev/ttyACM0
DEV=/dev/cu.usbmodem1442301
PARAMS=--buffer-size 512
MAIN=pico_sketch.py

# find the device
find:
	rshell -l

# install the python application to the pico to autostart
install:
	rshell -p $(DEV) $(PARAMS) cp $(MAIN) /pyboard/main.py

# connect shell to pico
# once connected, to see installed files
#   % ls /pyboard
shell:
	rshell -p  $(DEV)

# factory reset
# requires the device to be in bootloader mode
nuke:
	cp ../Pico_roms/flash_nuke.uf2 $(BOOTDEV)

# install the pico python environment to the pico
# requires the device to be in bootloader mode
flash:
	cp ../Pico_roms/rp2-pico-20230426-v1.20.0.uf2 $(BOOTDEV)
