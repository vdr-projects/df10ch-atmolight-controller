#
# Copyright (C) 2010 Andreas Auras
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

all: clean
	mkdir -p dist
	mkdir -p build/firmware
	python setup.py sdist
	(cd usb_boot && make)
	(cd usb_appl && make)
	(cd pwm_boot && make)
	(cd pwm_appl && make)
	cp usb_appl/df10ch_usb_appl.dff build/firmware/df10ch_usb_appl.dff
	cp pwm_appl/df10ch_pwm_appl.dff build/firmware/df10ch_pwm_appl.dff
	(cd build && tar cvzf ../dist/df10ch_firmware.tar.gz firmware)

## Clean target
.PHONY: clean
clean:
	(cd usb_boot && make clean)
	(cd usb_appl && make clean)
	(cd pwm_boot && make clean)
	(cd pwm_appl && make clean)
	rm -rf build MANIFEST
