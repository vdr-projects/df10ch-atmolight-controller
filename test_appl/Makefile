#
# Makefile for DF10CH Test program
#
CFLAGS_USB ?= $(shell pkg-config --cflags libusb-1.0)
LIBS_USB ?= $(shell pkg-config --libs libusb-1.0)
CFLAGS ?= -pipe -Wall -g

.PHONY: all clean

all: df10ch_test

clean:
	@-rm -f df10ch_test

df10ch_test: df10ch_test.c ../df10ch_usb_proto.h
	$(CC) $(CFLAGS) $(CFLAGS_USB) $(LIBS_USB) -o $@ $<
