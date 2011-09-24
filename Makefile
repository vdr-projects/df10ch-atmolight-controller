#
# Copyright (C) 2011 Andreas Auras
#
# This file is part of the DF10CH Atmolight controller project.
#
# DF10CH Atmolight controller is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# DF10CH Atmolight controller is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110, USA
#
# ################################
# Build all distribution tar files
# ################################

FIRMWARE_DIRS = usb_boot usb_appl pwm_boot pwm_appl
.PHONY: all dist srcdist windist clean firmware $(FIRMWARE_DIRS)

all: firmware

# Build binary distribution (linux) (setup program and *.dff firmware files)
dist: clean firmware
	mkdir -p dist
	mkdir -p build/firmware
	python setup.py sdist
	cp usb_boot/df10ch_usb_boot.hex build/firmware/df10ch_usb_boot.hex
	cp usb_appl/df10ch_usb_appl.dff build/firmware/df10ch_usb_appl.dff
	cp pwm_boot/df10ch_pwm_boot.hex build/firmware/df10ch_pwm_boot.hex
	cp pwm_appl/df10ch_pwm_appl.dff build/firmware/df10ch_pwm_appl.dff
	tar -C build -cvzf dist/df10ch_firmware.tar.gz firmware

# Build binary distribution (windows)
windist:
	python winsetup.py py2exe

# Build source distribution
srcdist: clean
	mkdir -p dist
	tar -cvz --exclude build --exclude dist --exclude '\..*' --exclude 'kicad/*\.bak' --exclude 'kicad/*\.000' --exclude 'kicad/*savepcb*' --exclude "*pyc" -f dist/df10ch_src_dist.tar.gz *
	
# Build firmware
firmware: $(FIRMWARE_DIRS)

$(FIRMWARE_DIRS):
	$(MAKE) -C $@

## Clean target
clean:
	for dir in $(FIRMWARE_DIRS) test_appl; do \
		$(MAKE) -C $$dir clean; \
	done
	rm -rf build MANIFEST
