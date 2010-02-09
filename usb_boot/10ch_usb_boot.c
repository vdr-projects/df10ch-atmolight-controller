/*
 * Copyright (C) 2010 Andreas Auras
 *
 * This file is part of the DF10CH Atmolight controller project.
 *
 * DF10CH Atmolight controller is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * DF10CH Atmolight controller is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110, USA
 *
 */

// ======================================================================
// Bootloader firmware for USB processor.
//

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>
#include <avr/eeprom.h>
#include <avr/boot.h>
#include <avr/pgmspace.h>

#include "../df10ch_common.h"
#include "../df10ch_usb_proto.h"
#include "usbconfig.h"


// ---
// Fuse-Bit settings for the flash programmer (ATmega8):
//	RSTDISBL=1
//	WDTON=1
//	SPIEN=0
//	CKOPT=0
//	EESAVE=1
//	BOOTSZ1=0
//	BOOTSZ0=0
//	BOOTRST=0
//
//	BODLEVEL=0
//	BODEN=0
//	SUT1=0
//	SUT0=1
//	CKSEL3=1
//	CKSEL2=1
//	CKSEL1=1
//	CKSEL0=1
//
// Memory-Lock Bits:
//	BL12=1, BL11=0, BL02=1, BL01=1, LB2=1, LB1=1
//
FUSES = 
{
	.low = (FUSE_BODLEVEL & FUSE_BODEN & FUSE_SUT1),
	.high = (FUSE_SPIEN & FUSE_CKOPT & FUSE_BOOTSZ1 & FUSE_BOOTSZ0 & FUSE_BOOTRST)
};
LOCKBITS = (LB_MODE_1 & BLB0_MODE_1 & BLB1_MODE_2);
SIGNATURE_DATA = { SIGNATURE_2, SIGNATURE_1, SIGNATURE_0 } ;


// ---
// System clock related.
// System clock ist implemented with hardware timer 1
//
#define SYS_HWPRESCALE		1024			// Hardware Prescaler

	// useconds <-> timer ticks conversation
#define US2TICKS(t)	((uint16_t)((double)(t) * (double)F_CPU / (1000000.0 * (double)SYS_HWPRESCALE) + 0.5))
#define	TICKS2US(t)	((uint16_t)((t) / (F_CPU / (1000000UL * SYS_HWPRESCALE))))


	// Input pin (Jumper) for enable/disable of bootloader
	// Enabled when Jumper set -> 0, Disabled if Jumper is away -> 1
#define BL_SENSE_DDR		DDRB
#define BL_SENSE_PORT 	PORTB
#define BL_SENSE_PIN	 	PINB
#define BL_SENSE_BIT		0

#define APPL_START_VECT	0x0000

static uint8_t leave_state;		// Is true when bootloader should be leaved


// ---
// USB related.
//
#define USB_DISCONNECT_TIME		US2TICKS(500000UL)
#define USB_STALL_RC					0xFF

static uint8_t usb_last_data_token NOMEMINIT;			// Token PID of last usb packet received
static uint8_t usb_last_rc = USB_STALL_RC;				// Return status of last payload packet
static uint8_t payload_req NOMEMINIT;							// ID of actual proccessed USB request

// ---
// flash programming related.
//
static uint16_t page_address NOMEMINIT;			// actual page address
static uint8_t	page_offset NOMEMINIT;			// actual offset into page
static uint8_t 	page_size_reply[2] = { (SPM_PAGESIZE & 0xFF), (SPM_PAGESIZE >> 8) };

#include <usbdrv.c>


// ---
// ISR handler for IRQ's that do not have a dedicated handler.
//
EMPTY_INTERRUPT(BADISR_vect)


// ---
// Write request payload data.
//
USB_PUBLIC uint8_t usbFunctionWrite(uint8_t *data, uint8_t len)
{
	uint8_t rc = USB_STALL_RC;

	if (usb_last_rc != USB_STALL_RC)
	{
		if (len != 8 || usbCrc16(data, 8) == ((uint16_t *)data)[4])
		{
			if (usbCurrentDataToken == usb_last_data_token)
				return usb_last_rc;	// Ignore packet

			if (payload_req == BL_REQ_WRITE_PAGE)
			{
				rc = 0;
			  while (len > 1)
				{
					bytes_word_t code;
					code.bytes[0] = *data++;
					code.bytes[1] = *data++;

			    cli();
			    boot_page_fill(page_address + page_offset, code.word);
			    sei();

			    page_offset += 2;
					len -= 2;
			    if (page_offset >= SPM_PAGESIZE)
					{
			      cli();
			      boot_page_write(page_address);
			      sei();

						while (boot_spm_busy())
							wdt_reset();

						rc = 1;
			    }
				}
			}
		}
	}

	if (rc)
		usb_last_rc = USB_STALL_RC;
	usb_last_data_token = usbCurrentDataToken;

	return rc;
}


// ---
// Read request payload data.
//
USB_PUBLIC uint8_t usbFunctionRead(uint8_t *data, uint8_t len)
{
	uint8_t rc = USB_STALL_RC;

	if (usb_last_rc != USB_STALL_RC)
	{
		if (payload_req == BL_REQ_READ_FLASH)
		{
			if (len > page_offset)
				len = page_offset;
			rc = len;
			if (len)
			{
				page_offset -= len;
				PGM_P p = (PGM_P) page_address;
				page_address += len;
				memcpy_P(data, p, len);
			}
		}

		if (rc != 8)
			usb_last_rc = USB_STALL_RC;
	}

	return rc;
}


// ---
// Handle a non-standard USB SETUP packet.
//
USB_PUBLIC usbMsgLen_t usbFunctionSetup(uint8_t data[8])
{
	usbRequest_t *r = (usbRequest_t *) data;

	usb_last_data_token = USBPID_SETUP;
	usb_last_rc = USB_STALL_RC;
	uint8_t rc = USB_NO_MSG;

	if (leave_state || usbCrc16(data, 8) != ((uint16_t *)data)[4])
		return rc;

	uint8_t req = r->bRequest;
	payload_req = req;

	if (req == BL_REQ_WRITE_PAGE)
	{
    page_address = r->wIndex.word;
    page_offset = 0;

		while (!eeprom_is_ready())
			wdt_reset();

    cli();
    boot_page_erase(page_address);
    sei();

		while (boot_spm_busy())
			wdt_reset();

		usb_last_rc = 0;
	}
	else if (req == BL_REQ_LEAVE_BOOT)
	{
		if (boot_rww_busy())
			boot_rww_enable();
		leave_state = 1;
		rc = 0;
	}
	else if (req == BL_REQ_GET_PAGE_SIZE)
	{
		usbMsgPtr = page_size_reply;
		rc = sizeof(page_size_reply);
	}
	else if (req == BL_REQ_READ_FLASH)
	{
		if (boot_rww_busy())
			boot_rww_enable();
    page_address = r->wIndex.word;
    page_offset = r->wLength.bytes[0];
		usb_last_rc = 0;
	}

	return rc;
}


// ----
// Main
//
void main(void) NORETURN;
void main(void)
{
	cli();

  wdt_enable(WDTO_120MS);	// Set watchdog timeout

		// Note: If application calls bootloader it must set the enable pin to output and low level
	if (bit_is_clear(BL_SENSE_DDR, BL_SENSE_BIT))
		set_bit(BL_SENSE_PORT, BL_SENSE_BIT);	// activate pullup

	if ((pgm_read_word(APPL_START_VECT) != 0xFFFF) &&			// Application reset vector programmed?
									bit_is_set(BL_SENSE_PIN, BL_SENSE_BIT))
	{			// boot loader disabled -> start application
		void (*jump_to_app)(void) = APPL_START_VECT / 2;	// Need flash word address!
		jump_to_app();
	}

	GICR = _BV(IVCE);	  	// enable change of interrupt vectors
	GICR = _BV(IVSEL);		// move interrupts to boot flash section

			// initialize boot loader disable pin: input + pullup
	clear_bit(BL_SENSE_DDR, BL_SENSE_BIT);
	set_bit(BL_SENSE_PORT, BL_SENSE_BIT);

	usbDeviceDisconnect();

		// Initialize Timer 1
	TIMSK = 0;
	TCCR1A = 0;
	TCCR1B = 0;
	TCNT1 = 0;
	TCCR1B = _BV(CS12) | _BV(CS10);			// Start timer 1, Prescaler 1024

	while (TCNT1 < USB_DISCONNECT_TIME)
		wdt_reset();

	TCCR1B = 0;	// Stop timer 1

	usbDeviceConnect();
	usbInit();

	sei();

		// Main loop
  for (;;)
  {	
			// Note: Delayed boot loader exit is done via watchdog timer reset
		if (!leave_state)
			wdt_reset();

		usbPoll();	// process USB requests
  }
}

