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
// Bootloader firmware for PWM processor.
//

#include <stdint.h>
#include <string.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>
#include <avr/pgmspace.h>
#include <avr/eeprom.h>
#include <avr/boot.h>

#include "../df10ch_common.h"
#include "../df10ch_usb_proto.h"


// ---
// Fuse-Bit settings for the flash programmer (Atmega 162):
//
//	M161C=1
//	BODLEVEL2=1
//	BODLEVEL1=0
//	BODLEVEL0=0
//
//	OCDEN=1
//	JTAGEN=1
//	SPIEN=0
//	WDTON=0
//	EESAVE=1
//	BOOTSZ1=0
//	BOOTSZ0=0
//	BOOTRST=0
//
//	CKDIV8=1
//	CKOUT=1
//	SUT1=0
//	SUT0=1
//	CKSEL3=1
//	CKSEL2=1
//	CKSEL1=1
//	CKSEL0=1
//
// Memory-Lock Bits:
//	BLB12=1, BLB11=0, BLB02=1, BLB01=1, LB2=1, LB1=1
//
FUSES = 
{
	.low = (FUSE_SUT1),
	.high = (FUSE_SPIEN & FUSE_WDTON & FUSE_BOOTSZ1 & FUSE_BOOTSZ0 & FUSE_BOOTRST),
	.extended = (FUSE_BODLEVEL1 & FUSE_BODLEVEL0),
};
LOCKBITS = (LB_MODE_1 & BLB0_MODE_1 & BLB1_MODE_2);
//SIGNATURE_DATA = { SIGNATURE_2, SIGNATURE_1, SIGNATURE_0 } ;


// ---
// System clock related.
// System clock is implemented with hardware timer 0
//
#define SYS_HWPRESCALE		64				// Hardware Prescaler
#define SYS_PRESCALER			256				// Timer Prescaler

	// useconds <-> timer ticks conversation
#define US2TICKS(t)	((uint16_t)((double)(t) * (double)F_CPU / (1000000.0 * (double)SYS_HWPRESCALE * (double)SYS_PRESCALER) + 0.5))
#define	TICKS2US(t)	(((t) / (F_CPU / (1000000UL * SYS_HWPRESCALE * SYS_PRESCALER))))

static uint16_t sys_clock;


// ---
// Keep alive reply related
//
#define MIN_KEEP_ALIVE_PAUSE	US2TICKS(15000)

static uint16_t last_keep_alive;

   
// ---
// Request parser related variables
//
typedef union
{
	uint8_t bytes[REQ_HEADER_SIZE];
	struct
	{
    uint8_t request_type;
 		uint8_t request;
   	bytes_word_t value;
   	bytes_word_t index;
   	bytes_word_t length;
  };
} pwm_request_t;

static pwm_request_t actual_req;
static uint8_t header_pos;
static uint8_t payload_pos;
static uint8_t payload_count;


// ---
// RX buffer related variables
//
#define RXBUF_SIZE (REQ_HEADER_SIZE + MAX_REQ_PAYLOAD_SIZE + 1)
#if RXBUF_SIZE == 256
#define CHECK_RXBUF_END(pos)
#else
#define CHECK_RXBUF_END(pos)	if ((pos) == RXBUF_SIZE) (pos) = 0
#endif

static uint8_t volatile rxrpos, rxwpos, rxspos, rx_err_status;
static uint8_t rxbuf[RXBUF_SIZE] NOMEMINIT;


// Status LED related
#define STATUS_LED_PORT	PORTE
#define STATUS_LED_BIT	1

// Input pin for enable/disable of bootloader
#define BL_SENSE_PIN	 	PINE
#define BL_SENSE_BIT		0

#define APPL_START_VECT	0x0000

// ---
// Definition of port direction and initial values.
//
#define PE_DDR	_BV(STATUS_LED_BIT)
#define	PE_INIT	_BV(BL_SENSE_BIT)


// ---
// ISR handler for IRQ's that do not have a dedicated handler.
//
EMPTY_INTERRUPT(BADISR_vect)


// ---
// ISR for receiving data.
//
ISR(USART0_RXC_vect)
{
	do
	{
		uint8_t i = rxwpos;
		uint8_t p = i + 1;
		CHECK_RXBUF_END(p);

		if (bit_is_set(UCSR0A, FE0))
			set_bit(rx_err_status, COMM_ERR_FRAME);
		else if (bit_is_set(UCSR0A, DOR0))
			set_bit(rx_err_status, COMM_ERR_OVERRUN);
		else if (p == rxrpos)
			set_bit(rx_err_status, COMM_ERR_OVERFLOW);
		else
		{
			if (bit_is_set(UCSR0B, RXB80))
				rxspos = i;		// save start of request message
			rxwpos = p;			// set data valid
		}
	  rxbuf[i] = UDR0;	// read data
	}
	while (bit_is_set(UCSR0A, RXC0));
}


// ---
// Processing while waiting for a event.
//
static void background_processing(void)
{
	wdt_reset();

		// count system clock
	if (bit_is_set(TIFR, TOV0))
	{
		++sys_clock;
		TIFR = _BV(TOV0);
	}
}


// ---
// Put data into transmit buffer.
//
static void send_reply_data(uint8_t c)
{
		// Wait until transmit buffer free
	while (bit_is_clear(UCSR0A, UDRE0))
		background_processing();

	UDR0 = c;
}


// ---
// Send reply start.
//
static void send_reply_start(uint8_t len)
{
		// Wait until transmit buffer free
	while (bit_is_clear(UCSR0A, UDRE0))
		background_processing();

	uint8_t id = actual_req.request_type & PWMRQ_ID_MASK;
	if (len)
		id |= PWMRP_HAS_PAYLOAD;

	set_bit(UCSR0B, TXB80);		// Set 9th bit for start of reply
	UDR0 = id;								// Send reply id
	clear_bit(UCSR0B, TXB80);

	if (len)
		send_reply_data(len);		// Send reply length

	last_keep_alive = sys_clock;
}


// ---
// Send keep alive reply.
//
static void send_keep_alive_reply(void)
{
	background_processing();
	if ((sys_clock - last_keep_alive) > MIN_KEEP_ALIVE_PAUSE)
	{
			// Wait until transmit buffer free
		while (bit_is_clear(UCSR0A, UDRE0))
			background_processing();

		set_bit(UCSR0B, TXB80);		// Set 9th bit for start of reply
		UDR0 = PWMRP_KEEP_ALIVE;	// Send keep alive ID
		clear_bit(UCSR0B, TXB80);

		last_keep_alive = sys_clock;
	}
}


// ---
// Send reply packet from flash memory.
//
static void send_reply_read_flash(PGM_P p, uint16_t n)
{
	if (n > MAX_REPLY_PAYLOAD_SIZE)
		n = 0;	// Send nothing!

	send_reply_start((uint8_t)n);

	while (n)
	{
		send_reply_data(pgm_read_byte(p));
		++p;
		--n;
	} 
}


// ---
// Process write flash page request.
//
static void req_write_flash_page(uint16_t page_address, uint16_t len)
{
	while (!eeprom_is_ready())
		send_keep_alive_reply();

  cli();
  boot_page_erase(page_address);
  sei();

	while (boot_spm_busy())
		send_keep_alive_reply();

  uint8_t page_offset = 0;
	uint8_t p = payload_pos;
	while (len > 1 && page_offset < SPM_PAGESIZE)
	{
		bytes_word_t v;
		v.bytes[0] = rxbuf[p++];
		CHECK_RXBUF_END(p);
		v.bytes[1] = rxbuf[p++];
		CHECK_RXBUF_END(p);

    cli();
    boot_page_fill(page_address + page_offset, v.word);
    sei();

    page_offset += 2;
		len -= 2;
	}

	cli();
	boot_page_write(page_address);
	sei();

	while (boot_spm_busy())
		send_keep_alive_reply();

	if (boot_rww_busy())
		boot_rww_enable();
}


// ---
// Process received request.
//
static void process_request(void)
{				 
	pwm_request_t *r = &actual_req;
	FIX_POINTER(r);

	uint8_t req = r->request;

	if (req == BL_PWM_REQ_WRITE_PAGE)
		req_write_flash_page(r->index.word, r->length.word);
	else if (req == BL_PWM_REQ_READ_FLASH)
	{
		send_reply_read_flash((PGM_P) r->index.word, r->length.word);
		return;
	}
	else if (req == BL_PWM_REQ_GET_PAGE_SIZE)
	{
		send_reply_start(2);
		send_reply_data(SPM_PAGESIZE & 0xFF);
		send_reply_data(SPM_PAGESIZE >> 8);
		return;
	}
	else if (req == BL_PWM_REQ_GET_REQUEST_ERR_STATUS)
	{
		send_reply_start(1);
		send_reply_data(rx_err_status);
		rx_err_status = 0;
		return;
	}
	else if (req == PWM_REQ_GET_VERSION)
	{
		send_reply_start(2);
		send_reply_data(PWM_VERS_BOOT);
		send_reply_data(FIRMWARE_VERSION);
		return;
	}

	send_reply_start(0);
}


// ---
// Decode data byte of received data.
//
static void read_data(void)
{
	uint8_t p, c, is_req_start;

		// Read data from RX buffer
	p = rxrpos;
	is_req_start = (p == rxspos);
	c = rxbuf[p++];
	CHECK_RXBUF_END(p);
	rxrpos = p;

	p = header_pos;
	if (is_req_start)
	{
		if (p)
			set_bit(rx_err_status, COMM_ERR_TIMEOUT);

		p = 0;
	}
	else if (!p)
		return;					// Discard garbage

	if (p < sizeof(pwm_request_t))
	{
		pwm_request_t *r = &actual_req;
		FIX_POINTER(r);

		r->bytes[p++] = c;
		header_pos = p;

		if (p < sizeof(pwm_request_t))
			return;

			// Header complete
		if (!(r->request_type & PWMRQ_DEVICE_TO_HOST) && r->length.word)
		{
			payload_pos = rxrpos;
			payload_count = r->length.word;
			return;
		}
	}	
	else if (--payload_count)
		return;	// Payload not complete

	last_keep_alive = sys_clock;
	process_request();
	header_pos = 0;
}


// ---
// Device initialization and main program loop.
//
void main(void) NORETURN;
void main(void)
{
  wdt_enable(WDTO_30MS);	// Set watchdog timeout

		// Port init, enable pull-up resistors for unused ports
	PORTE = PE_INIT;
	DDRE = PE_DDR;

	if ((pgm_read_word(APPL_START_VECT) != 0xFFFF) &&			// Application reset vector programmed?
									bit_is_set(BL_SENSE_PIN, BL_SENSE_BIT))
	{			// boot loader disabled -> start application
		void (*jump_to_app)(void) = APPL_START_VECT / 2;	// Need flash word address!
		jump_to_app();
	}

	GICR = _BV(IVCE);	  	// enable change of interrupt vectors
	GICR = _BV(IVSEL);		// move interrupts to boot flash section

		// USART init
		// 9 data bits, 1 stop bit, no parity, asynchron mode
		// Enable TX, RX and RX Interrupts
#include <util/setbaud.h>
  UBRR0H = UBRRH_VALUE;
  UBRR0L = UBRRL_VALUE;
#if USE_2X
  UCSR0A = _BV(U2X);
#endif
	UCSR0C = _BV(URSEL0) | _BV(UCSZ01) | _BV(UCSZ00);
  UCSR0B = _BV(RXEN0) | _BV(TXEN0) | _BV(RXCIE0) | _BV(UCSZ02);

		// Timer 0 is used for system clock
		// Normal mode, Prescaler 64
	TCCR0 = _BV(CS01) | _BV(CS00);

	sei();

		// Main loop
  for (;;)
  {	
		background_processing();

		if (rxrpos != rxwpos)
			read_data();

		if (header_pos)
			clear_bit(STATUS_LED_PORT, STATUS_LED_BIT); // We are processing a request
		else
			set_bit(STATUS_LED_PORT, STATUS_LED_BIT);		// No request
  }
}
