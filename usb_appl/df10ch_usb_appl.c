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
// Application firmware for USB processor.
//

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>
#include <avr/eeprom.h>
#include <avr/sleep.h>

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
//	BOOTRST=1
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
	.high = (FUSE_SPIEN & FUSE_CKOPT & FUSE_BOOTSZ1 & FUSE_BOOTSZ0)
};
LOCKBITS = (LB_MODE_1 & BLB0_MODE_1 & BLB1_MODE_2);
//SIGNATURE_DATA = { SIGNATURE_2, SIGNATURE_1, SIGNATURE_0 } ;


#define EE_MEM_SIZE	(E2END + 1)


// ---
// System clock related.
// System clock ist implemented with hardware timer 1
//
#define SYS_HWPRESCALE		1024			// Hardware Prescaler

	// useconds <-> timer ticks conversation
#define US2TICKS(t)	((uint16_t)((double)(t) * (double)F_CPU / (1000000.0 * (double)SYS_HWPRESCALE) + 0.5))
#define	TICKS2US(t)	((uint16_t)((t) / (F_CPU / (1000000UL * SYS_HWPRESCALE))))


// ---
// pwm controller reset related.
//
#define RESET_TIME		US2TICKS(128UL)
#define STARTUP_TIME	US2TICKS(10000UL)

	// Output pin for PWM controller reset
#define RESET_PORT		PORTB
#define RESET_BIT			4

	// Output pin for enabling PWM controller bootloader
#define BOOTLOADER_PORT 	PORTB
#define BOOTLOADER_BIT		3


// ---
// bootloader related.
//
#define BL_START_VECT			0x1800

// Input/Output pin for bootloader startup
#define BL_SENSE_DDR		DDRB
#define BL_SENSE_PORT 	PORTB
#define BL_SENSE_PIN	 	PINB
#define BL_SENSE_BIT		0

#define BL_START_DELAY_TIME			US2TICKS(30000UL)

static uint8_t 	bl_start;
static uint16_t	bl_time;


// ---
// USB related.
//
#define USB_SLEEP_TIMEOUT				US2TICKS(5000UL)
#define USB_DISCONNECT_TIME			US2TICKS(500000UL)
#define USB_INITIALIZE_TIMEOUT	US2TICKS(1750000UL)
#define USB_STALL_RC						0xFF

volatile uint16_t usb_sof_time;					// Time of last USB start of frame IRQ
static uint8_t usb_is_resetting;				// Is true while reset condition on USB bus happen
static uint8_t usb_is_initialized;			// Is true after USB address has been set
static uint8_t usb_last_data_token;			// Token PID of last usb packet received
static uint8_t usb_last_rc;							// Return status of last payload packet
static uint8_t payload_req;							// ID of actual proccessed USB request
static uint16_t payload_pos;						// Position of actual payload read/write
static uint16_t payload_count;					// Number of bytes left of actual payload read/write



// ---
// RX buffer related.
//
#define RXBUF_SIZE 256
#if RXBUF_SIZE == 256
#define CHECK_RXBUF_END(pos)
#else
#define CHECK_RXBUF_END(pos)	if ((pos) == RXBUF_SIZE) (pos) = 0
#endif

static volatile uint8_t rxrpos, rxwpos;
static volatile uint8_t rxspos;	// Start position of reply
static uint8_t rxbuf[RXBUF_SIZE] NOMEMINIT;


// ---
// TX buffer related.
//
#define TXBUF_SIZE 256
#if TXBUF_SIZE == 256
#define CHECK_TXBUF_END(pos)
#else
#define CHECK_TXBUF_END(pos)	if ((pos) == TXBUF_SIZE) (pos) = 0
#endif

static uint8_t txrpos, txwpos;
static uint8_t txbuf[TXBUF_SIZE] NOMEMINIT;


// ---
// PWM controller communication related.
//
#define REPLY_START_TIMEOUT	US2TICKS(50000UL)
#define REPLY_TIMEOUT				US2TICKS(10000UL)

static uint8_t actual_req_id;
static uint8_t reply_start;
static uint8_t reply_count;
static volatile uint8_t reply_err_status;
static uint16_t reply_start_timeout = REPLY_START_TIMEOUT;
static uint16_t reply_timeout = REPLY_TIMEOUT;


// ---
// Port setup related.
//
#define PORTB_INIT	(_BV(BL_SENSE_BIT) | _BV(BOOTLOADER_BIT) | _BV(1) | _BV(2) | _BV(5))
#define DDRB_INIT		(_BV(BOOTLOADER_BIT) | _BV(RESET_BIT))

#define PORTC_INIT	(0xFF)
#define DDRC_INIT		(0)

#define PORTD_INIT	(_BV(1) | _BV(5) | _BV(6) | _BV(7))
#define DDRD_INIT		(_BV(1))


// ---
// Watchdogtimer related.
//
#define WDTO_TIMEOUT     WDTO_120MS


#include <usbdrv.c>


// ---
// ISR handler for IRQ's that do not have a dedicated handler.
//
ISR(BADISR_vect)
{
		for (;;);    // wait until watchdog resets device
}


// ---
// ISR for receiving data.
//
ISR(USART_RXC_vect)
{
	clear_bit(UCSRB, RXCIE);
	sei();

	do
	{
		uint8_t i = rxwpos;
		uint8_t p = i + 1;
		CHECK_RXBUF_END(p);
		if (p == rxrpos)
			set_bit(reply_err_status, COMM_ERR_OVERFLOW);
		else
			rxwpos = p;		// set data valid

		if (bit_is_set(UCSRA, DOR))
			set_bit(reply_err_status, COMM_ERR_OVERRUN);
		if (bit_is_set(UCSRA, FE))
			set_bit(reply_err_status, COMM_ERR_FRAME);
		if (bit_is_set(UCSRB, RXB8))
			rxspos = i;	// save reply start position
		rxbuf[i] = UDR;	// read data
	}
	while (bit_is_set(UCSRA, RXC));

	cli();
	set_bit(UCSRB, RXCIE);
}


// ---
// Read actual system clock counter.
// Note: Counter is also read inside USB irq handler -> we need save read!
//
static uint16_t get_sys_clock(void)
{
	uint8_t sreg = SREG;
	cli();
	uint16_t t = TCNT1;
	SREG = sreg;
	nop();
	return t;
}


// ---
// Calculate timer ticks from milliseconds.
//
static uint16_t ms_to_ticks(uint16_t ms)
{
	uint32_t t = F_CPU / SYS_HWPRESCALE;
	t *= ms;
	t /= 1000;
	return (uint16_t) t;
}


// ---
// Processing while waiting for a event.
//
static void background_processing(void)
{
	wdt_reset();

		// Write data from transmit buffer to USART
	while (bit_is_set(UCSRA, UDRE))
	{
		uint8_t p = txrpos;
		if (p == txwpos)
			break;

		UDR = txbuf[p++];
		CHECK_TXBUF_END(p);
		txrpos = p;
	}
}


// ---
// Timer based delay.
//
static void timer_delay(uint16_t d)
{
	uint16_t t = get_sys_clock();
	while ((get_sys_clock() - t) < d)
		background_processing();
}


// ---
// Put data into transmit buffer.
//
static void send_data(uint8_t c)
{
	uint8_t p = txwpos + 1;
	CHECK_TXBUF_END(p);

		// Wait until space available
	while (p == txrpos)
		background_processing();

	txbuf[txwpos] = c;
	txwpos = p;

	background_processing();
}


// ---
// Send command request for PWM controller.
//
static void send_request(uint8_t req_type)
{
		// Wait until transmit buffers are empty
	while (txrpos != txwpos || bit_is_clear(UCSRA, UDRE))
		background_processing();

	rxspos = rxwpos - 1;		// Reset start reply position

	++actual_req_id;
	actual_req_id &= PWMRQ_ID_MASK;

	set_bit(UCSRB, TXB8);						// Set 9th bit for start of request
	UDR = req_type | actual_req_id;	// Send request type and id unbuffered
	clear_bit(UCSRB, TXB8);
}


// ---
// Read reply data.
//
static uint8_t read_data(void)
{
	uint8_t p = rxrpos;
	uint8_t c = rxbuf[p++];
	CHECK_RXBUF_END(p);
	rxrpos = p;
	return c;
}


// ---
// Wait for reply data from PWM controller.
//
static uint8_t wait_for_reply(void)
{
	uint16_t t = get_sys_clock();
	uint16_t d = reply_timeout;

	while ((get_sys_clock() - t) < d)
	{
		background_processing();

		if (rxwpos != rxrpos)
		{
			if (reply_start == rxspos)	// Check for same reply
				return 1;
			set_bit(reply_err_status, COMM_ERR_START);
			return 0;
		}
	}

	set_bit(reply_err_status, COMM_ERR_TIMEOUT);
	return 0;
}


// ---
// Wait for start of reply data from PWM controller.
//
static uint8_t wait_for_reply_start(void)
{
	uint16_t t = get_sys_clock();
	uint16_t d = reply_start_timeout;

	while ((get_sys_clock() - t) < d)
	{
		background_processing();

		uint8_t p = rxrpos;
		if (rxwpos != p)
		{
			if (rxspos == p)
			{		// reply start detected
				uint8_t id = read_data();
				if (id == PWMRP_KEEP_ALIVE)
				{		// keep alive reply
					t = get_sys_clock();
					continue;
				}
				if ((id & PWMRQ_ID_MASK) == actual_req_id)
				{		// reply is for actual request
					reply_start = p;
					if (!(id & PWMRP_HAS_PAYLOAD))
					{
						reply_count = 0;
						return 1;
					}
					if (wait_for_reply())
					{
						reply_count = read_data();
						return 1;
					}
					return 0;
				}
			}
				// drop garbagge
			++p;
			CHECK_RXBUF_END(p);
			rxrpos = p;
		}

		if (bit_is_clear(UCSRA, TXC))
			t = get_sys_clock();
	}

	set_bit(reply_err_status, COMM_ERR_TIMEOUT);
	return 0;
}


// ---
// Stop PWM controller.
//
static void stop_pwm_ctrl(void)
{
	clear_bit(UCSRB, RXEN);	// Disable USART RX
	clear_bit(RESET_PORT, RESET_BIT);
}


// ---
// Reset PWM controller.
//
static void reset_pwm_ctrl(void)
{
	stop_pwm_ctrl();
	timer_delay(RESET_TIME);

	set_bit(RESET_PORT, RESET_BIT);
	timer_delay(STARTUP_TIME);

	rxwpos = rxrpos = 0;	// Flush reply buffer
	reply_err_status = 0;

	set_bit(UCSRB, RXEN);		// Enable USART RX
}


// ---
// Send PWM controller request payload data.
//
static uint8_t send_payload_data(uint8_t *data, uint8_t len)
{
	if(len > payload_count)
		len = payload_count;
	payload_count -= len;

	uint8_t i = 0;
	while (i < len)
		send_data(data[i++]);

	if (!payload_count)
	{
		if (wait_for_reply_start())	// Wait for ACK
			return 1; // all done successfull
		return USB_STALL_RC; // error happen
	}

	return 0; // next packet
}


// ---
// Read PWM controller request payload data.
//
static uint8_t read_payload_data(uint8_t *data, uint8_t len)
{
	if (len > reply_count)
		len = reply_count;
	if(len > payload_count)
		len = payload_count;
	reply_count -= len;
	payload_count -= len;

	uint8_t i = 0;
	while (i < len && wait_for_reply())
		data[i++] = read_data();

	if (i < len)
		return USB_STALL_RC;	// error happen

	return i;
}


// ---
// Write EE prom data.
//
static uint8_t write_ee_data(uint8_t *data, uint8_t len)
{
	if(len > payload_count)
		len = payload_count;
	payload_count -= len;

	uint8_t i = 0;
	while (i < len && payload_pos < EE_MEM_SIZE)
	{
		uint8_t old_data = eeprom_read_byte((uint8_t *)payload_pos);
		uint8_t new_data = data[i];
		if (old_data != new_data)
		{
			eeprom_write_byte((uint8_t *)payload_pos, new_data);

			while (!eeprom_is_ready())
				background_processing();

			old_data = eeprom_read_byte((uint8_t *)payload_pos);
			if (old_data != new_data)
				return USB_STALL_RC; // write error
		}
		++i;
		++payload_pos;
	}

	return payload_count == 0;
}


// ---
// Read EE prom data.
//
static uint8_t read_ee_data(uint8_t *data, uint8_t len)
{
	if(len > payload_count)
		len = payload_count;
	payload_count -= len;

	uint8_t i = 0;
	while (i < len && payload_pos < EE_MEM_SIZE)
	{
		data[i] = eeprom_read_byte((uint8_t *)payload_pos);
		++i;
		++payload_pos;
	}

	return i;
}


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
			{
				set_bit(reply_err_status, COMM_ERR_DUPLICATE);
				return usb_last_rc;	// Ignore packet
			}

			if (payload_req >= REQ_PWM_START)
				rc = send_payload_data(data, len);
			else if (payload_req == REQ_WRITE_EE_DATA)
				rc = write_ee_data(data, len);
		}
		else
			set_bit(reply_err_status, COMM_ERR_CRC);
	}

	usb_last_data_token = usbCurrentDataToken;
	usb_last_rc = rc;

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
		if (payload_req >= REQ_PWM_START)
			rc = read_payload_data(data, len);
		else if (payload_req == REQ_READ_EE_DATA)
			rc = read_ee_data(data, len);
	}

	usb_last_rc = rc;

	return rc;
}


// ---
// Handle a non-standard USB SETUP packet.
//
USB_PUBLIC usbMsgLen_t usbFunctionSetup(uint8_t data[8])
{
	usbRequest_t *r = (usbRequest_t *) data;
	static uint8_t reply[1];

	usb_last_data_token = USBPID_SETUP;
	usb_last_rc = USB_STALL_RC;
	uint8_t rc = USB_NO_MSG;

	if (usbCrc16(data, 8) != ((uint16_t *)data)[4])
	{
		set_bit(reply_err_status, COMM_ERR_CRC);
		return rc;
	}

	uint8_t req = r->bRequest;

	if (req >= REQ_PWM_START)
	{
		if (bit_is_clear (RESET_PORT, RESET_BIT))
			reset_pwm_ctrl();
			
		uint8_t req_type = (r->bmRequestType & USBRQ_DIR_MASK) == USBRQ_DIR_DEVICE_TO_HOST ? PWMRQ_DEVICE_TO_HOST: 0;
		if (r->wLength.word <= MAX_REQ_PAYLOAD_SIZE)
		{
			send_request(req_type);
			send_data(req);
			send_data(r->wValue.bytes[0]);
			send_data(r->wValue.bytes[1]);
			send_data(r->wIndex.bytes[0]);
			send_data(r->wIndex.bytes[1]);
			send_data(r->wLength.bytes[0]);
			send_data(r->wLength.bytes[1]);

			payload_req = req;
			payload_count = r->wLength.word;

			if (req_type == PWMRQ_DEVICE_TO_HOST || !r->wLength.word)
			{
				if (wait_for_reply_start())
				{
					if (reply_count && r->wLength.word)
						usb_last_rc = 0;
					else
						rc = 0;
				}
			}
			else
				usb_last_rc = 0;
		}
	}
	else if (req == REQ_READ_EE_DATA || req == REQ_WRITE_EE_DATA)
	{
		if (r->wLength.word)
		{
			payload_pos = r->wIndex.word;
			payload_req = req;
			payload_count = r->wLength.word;
			usb_last_rc = 0;
		}
		else
			rc = 0;
	}
	else if (req == REQ_STOP_PWM_CTRL)
	{
		set_bit(BOOTLOADER_PORT, BOOTLOADER_BIT);
		stop_pwm_ctrl();
		rc = 0;
	}
	else if (req == REQ_RESET_PWM_CTRL)
	{
		set_bit(BOOTLOADER_PORT, BOOTLOADER_BIT);
		reset_pwm_ctrl();
		rc = 0;
	}
	else if (req == REQ_BOOTLOADER_RESET_PWM_CTRL)
	{
		clear_bit(BOOTLOADER_PORT, BOOTLOADER_BIT);
		reset_pwm_ctrl();
		rc = 0;
	}
	else if (req == REQ_GET_REPLY_ERR_STATUS)
	{
		reply[0] = reply_err_status;
		reply_err_status = 0; 
		usbMsgPtr = reply;
		rc = 1;
	}
	else if (req == REQ_SET_REPLY_TIMEOUT)
	{
		reply_start_timeout = ms_to_ticks(r->wValue.word);
		reply_timeout = ms_to_ticks(r->wIndex.word);
		rc = 0;
	}
	else if (req == REQ_START_BOOTLOADER)
	{
		bl_start = 1;
		bl_time = get_sys_clock();
		rc = 0;
	}

	return rc;
}


// ----
// Main
//
void main(void) NORETURN;
void main(void)
{
  wdt_enable(WDTO_TIMEOUT);

		// Initialize Ports
	PORTB = PORTB_INIT;
	DDRB = DDRB_INIT;
	PORTC = PORTC_INIT;
	DDRC = DDRC_INIT;
	PORTD = PORTD_INIT;
	DDRD = DDRD_INIT;

	usbDeviceDisconnect();

	set_bit(ACSR, ACD);	// Disable analog comparator saving some power

		// Initialize Timer 1
	TCNT1 = 0;
	TCCR1B = _BV(CS12) | _BV(CS10);			// Start timer 1, Prescaler 1024

		// Initialize USART
#include <util/setbaud.h>
  UBRRH = UBRRH_VALUE;
  UBRRL = UBRRL_VALUE;
#if USE_2X
  UCSRA = _BV(U2X);
#endif
	UCSRC = _BV(URSEL) | _BV(UCSZ1) | _BV(UCSZ0);	// 9 data bits, 1 stop bit, no parity, asynchron mode
  UCSRB = _BV(TXEN) | _BV(UCSZ2) | _BV(RXCIE);	// Enable TX and RX IRQ

	reset_pwm_ctrl();

	timer_delay(USB_DISCONNECT_TIME);
	usbDeviceConnect();
	usbInit();

	sei();

		// Main loop
  for (;;)
  {	
		background_processing();

		usbPoll();	// process USB requests

		if ((bit_is_clear(BL_SENSE_PIN, BL_SENSE_BIT) ||
				 (bl_start && (get_sys_clock() - bl_time) > BL_START_DELAY_TIME)) &&
				 pgm_read_word(BL_START_VECT) != 0xFFFF)
		{
			cli();
			stop_pwm_ctrl();
	    clear_bit(USB_INTR_ENABLE, USB_INTR_ENABLE_BIT);	// Stop USB
			UCSRB = 0;	// Stop USART
			TCCR1B = 0;	// Stop Timer

				// enable boot loader by setting sense pin to 0
			clear_bit(BL_SENSE_PORT, BL_SENSE_BIT);
			set_bit(BL_SENSE_DDR, BL_SENSE_BIT);

				// start bootloader
			void (*jump_to_bl)(void) = BL_START_VECT / 2;		// Need flash word address for jump!
			jump_to_bl();
		}


#if 0
		if (!usb_is_initialized && get_sys_clock() > USB_INITIALIZE_TIMEOUT)
		{		// request USB device enumeration
			cli();
			usb_is_initialized = 1;
			usbDeviceDisconnect();
			timer_delay(USB_DISCONNECT_TIME);
			usbDeviceConnect();
			usbInit();
			sei();
		}
#endif

			// Check for standby state
		if (usb_is_resetting)
		{		// ongoing USB reset -> reset activity timeout
			cli();
			usb_sof_time = TCNT1;
			sei();
		}
		else
		{
			cli();
			uint16_t t = usb_sof_time;
			sei();
			if ((get_sys_clock() - t) > USB_SLEEP_TIMEOUT)
			{		// no USB activity -> go sleeping
				cli();
				stop_pwm_ctrl();
	      set_sleep_mode(SLEEP_MODE_PWR_DOWN);
				USB_INTR_CFG &= ~USB_INTR_CFG_SET;	// set low level triggered IRQ for wakeup
				USB_INTR_PENDING = _BV(USB_INTR_PENDING_BIT);	// reset pending IRQ
				wdt_disable();
        sleep_enable();
        sei();
        sleep_cpu();
        sleep_disable();
			  wdt_enable(WDTO_TIMEOUT);
				cli();
				TCNT1 = 0;
				usb_sof_time = 0;
				sei();
				reset_pwm_ctrl();			
			}
		}
  }
}
