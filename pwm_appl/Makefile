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
#
###############################################################################
# Makefile for the application firmware of PWM processor
###############################################################################

## General Flags
PROJECT = df10ch_pwm_appl
MCU = atmega162
TARGET = df10ch_pwm_appl.elf
CC = avr-gcc
AVRDUDE ?= avrdude -c stk500v2 -P avrdoper
F_CPU ?= 16000000UL
FIRMWARE_VERSION ?= 2

## Options common to compile, link and assembly rules
COMMON = -mmcu=$(MCU)

## Compile options common for all C compilation units.
CFLAGS = $(COMMON)
CFLAGS += -Wall -gdwarf-2 -Os -funsigned-char -funsigned-bitfields -fpack-struct -fshort-enums
CFLAGS += -DF_CPU=$(F_CPU) -DFIRMWARE_VERSION=$(FIRMWARE_VERSION)

## Assembly specific flags
ASMFLAGS = $(COMMON)
ASMFLAGS += $(CFLAGS)
ASMFLAGS += -x assembler-with-cpp -Wa,-gdwarf2

## Linker flags
LDFLAGS = $(COMMON)
LDFLAGS += -Wl,-Map=df10ch_pwm_appl.map
LDFLAGS += -Wl,-section-start=.eeprom=0x810001


## Intel Hex file production flags
HEX_FLASH_FLAGS = -R .eeprom -R .fuse -R .lock -R .signature

HEX_EEPROM_FLAGS = -j .eeprom
HEX_EEPROM_FLAGS += --set-section-flags=.eeprom="alloc,load"
HEX_EEPROM_FLAGS += --change-section-lma .eeprom=0x01 --no-change-warnings

## AVR size flags
#AVR_SIZE_FLAGS ?= -C --mcu=${MCU}
AVR_SIZE_FLAGS ?= --format=sysv

## Include Directories
INCLUDES = -I. -I..

## Objects that must be built in order to link
OBJECTS = df10ch_pwm_appl.o

## Objects explicitly added by the user
LINKONLYOBJECTS = 

## Build
all: $(TARGET) df10ch_pwm_appl.dff df10ch_pwm_appl.lss size

df10ch_pwm_appl.dff: df10ch_pwm_appl.hex
	echo "@DF10CH-PWM" $(FIRMWARE_VERSION) > $@
	cat df10ch_pwm_appl.hex >> $@
	
prog: flash
	$(AVRDUDE) -p $(MCU) -u -Ulfuse:w:0xc0:m -Uhfuse:w:0xc9:m -Uefuse:w:0xf9:m -Ulock:w:0xef:m
	
flash: df10ch_pwm_appl.hex
	$(AVRDUDE) -p $(MCU) -U flash:w:df10ch_pwm_appl.hex:i

## Compile
df10ch_pwm_appl.o: df10ch_pwm_appl.c ../df10ch_usb_proto.h ../df10ch_common.h
	$(CC) $(INCLUDES) $(CFLAGS) -c  $<

##Link
$(TARGET): $(OBJECTS)
	 $(CC) $(LDFLAGS) $(OBJECTS) $(LINKONLYOBJECTS) $(LIBDIRS) $(LIBS) -o $(TARGET)

%.hex: $(TARGET)
	avr-objcopy -O ihex $(HEX_FLASH_FLAGS)  $< $@

%.eep: $(TARGET)
	-avr-objcopy $(HEX_EEPROM_FLAGS) -O ihex $< $@ || exit 0

%.lss: $(TARGET)
	avr-objdump -h -S $< > $@

size: ${TARGET}
	@echo
	@avr-size ${AVR_SIZE_FLAGS} ${TARGET}

## Clean target
.PHONY: clean
clean:
	-rm -rf $(OBJECTS) df10ch_pwm_appl.elf df10ch_pwm_appl.dff df10ch_pwm_appl.hex df10ch_pwm_appl.eep df10ch_pwm_appl.lss df10ch_pwm_appl.map
