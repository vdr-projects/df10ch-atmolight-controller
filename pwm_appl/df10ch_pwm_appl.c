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
// Application firmware for PWM processor.
//

#include <stdint.h>
#include <string.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>
#include <avr/pgmspace.h>
#include <avr/eeprom.h>

#include "../df10ch_common.h"
#include "../df10ch_usb_proto.h"


// ---
// Fuse-Bit settings for the flash programmer (ATmega 162):
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
//	BOOTRST=1
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
	.high = (FUSE_SPIEN & FUSE_WDTON & FUSE_BOOTSZ1 & FUSE_BOOTSZ0),
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
// PWM generation related
//
#define DEF_F_PWM 			100UL	// Default PWM cycle frequency in Hz
#define PWM_HWPRESCALE	16		// Hardware timer prescale
#define PWM_PRESCALE		9			// require: (PWM_PRESCALE * PWM_HWPRESCALE) > (size of ISR for timer )

#define DEF_MAX_PWM (F_CPU / (PWM_HWPRESCALE * PWM_PRESCALE * DEF_F_PWM) - 1)	// Maximum internal resolution for pwm

#define PWM_STEP_PAGE_SIZE (NCHANNELS + 2) // possible maximum steps: NCHANNELS + Pause + End of Table

typedef struct pwm_step_s {
	uint8_t port_val[NPORTS];				// Values for Port A,B,C,D
	uint16_t timer_val;							// Timer compare value
	struct pwm_step_s *next_step;		// Pointer to next list entry
	} pwm_step_t;

	// One actual and one shadow page
static pwm_step_t pwm_step_page1[PWM_STEP_PAGE_SIZE] NOMEMINIT;
static pwm_step_t pwm_step_page2[PWM_STEP_PAGE_SIZE] NOMEMINIT;
static pwm_step_t *shadow_pwm_page NOMEMINIT;
static pwm_step_t *active_pwm_page NOMEMINIT;
static pwm_step_t * volatile actual_pwm_step NOMEMINIT;
static uint8_t update_pwm_page NOMEMINIT;


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


// ---
// Actual brightness values for each channel
//
static uint16_t bright_vals[NCHANNELS];


// ---
// Port channel mapping related variables
//
typedef struct { uint8_t code, port_bits; } channel_map_t;

static const channel_map_t default_channel_map[NCHANNELS] PROGMEM = {
		// J3
	{ CM_CODE(PA_IDX, 0), _BV(2) },
	{ CM_CODE(PA_IDX, 1), _BV(1) },
	{ CM_CODE(PA_IDX, 2), _BV(0) },

		// J4
	{ CM_CODE(PA_IDX, 3), _BV(5) },
	{ CM_CODE(PA_IDX, 4), _BV(4) },
	{ CM_CODE(PA_IDX, 5), _BV(3) },

		// J5
	{ CM_CODE(PC_IDX, 6), _BV(7) },
	{ CM_CODE(PA_IDX, 7), _BV(7) },
	{ CM_CODE(PA_IDX, 8), _BV(6) },

		// J6
	{ CM_CODE(PC_IDX, 9), _BV(4) },
	{ CM_CODE(PC_IDX, 10), _BV(5) },
	{ CM_CODE(PC_IDX, 11), _BV(6) },

		// J7
	{ CM_CODE(PC_IDX, 12), _BV(1) },
	{ CM_CODE(PC_IDX, 13), _BV(2) },
	{ CM_CODE(PC_IDX, 14), _BV(3) },

		// J8
	{ CM_CODE(PD_IDX, 15), _BV(6) },
	{ CM_CODE(PD_IDX, 16), _BV(7) },
	{ CM_CODE(PC_IDX, 17), _BV(0) },

		// J9
	{ CM_CODE(PD_IDX, 18), _BV(3) },
	{ CM_CODE(PD_IDX, 19), _BV(4) },
	{ CM_CODE(PD_IDX, 20), _BV(5) },

		// J10
	{ CM_CODE(PB_IDX, 21), _BV(6) },
	{ CM_CODE(PB_IDX, 22), _BV(7) },
	{ CM_CODE(PD_IDX, 23), _BV(2) },

		// J11
	{ CM_CODE(PB_IDX, 24), _BV(3) },
	{ CM_CODE(PB_IDX, 25), _BV(4) },
	{ CM_CODE(PB_IDX, 26), _BV(5) },

		// J12
	{ CM_CODE(PB_IDX, 27), _BV(0) },
	{ CM_CODE(PB_IDX, 28), _BV(1) },
	{ CM_CODE(PB_IDX, 29), _BV(2) }

	};


// ---
// Setup values that will be stored to eeprom.
//

typedef struct {
	uint16_t max_pwm;
	uint8_t common_pwm;
	channel_map_t channel_map[NCHANNELS];
	} setup_t;
	
setup_t setup NOMEMINIT;

#define EE_VALID_MARK 0xA5
static uint8_t ee_valid EEMEM;		// If eeprom content is valid this byte is EE_VALID_MARK
static setup_t ee_setup EEMEM;


// Status LED related
#define STATUS_LED_PORT	PORTE
#define STATUS_LED_BIT	1

// Common PWM channel related
#define MAX_COMMON_PWM 255
#define DEF_COMMON_PWM 255	// Default common pwm value

#define COMMON_PWM_PORT	PORTE
#define COMMON_PWM_BIT	2


// Input pin for enable/disable of bootloader
#define BL_SENSE_PIN	 	PINE
#define BL_SENSE_BIT		0


// ---
// Definition of port direction and initial values.
//
#define PA_DDR	0xFF
#define PA_INIT	0x00

#define PB_DDR	0xFF
#define PB_INIT	0x00

#define PC_DDR	0xFF
#define PC_INIT	0x00

#define PD_DDR (_BV(1) | _BV(2) | _BV(3) | _BV(4) | _BV(5) | _BV(6) | _BV(7))
#define	PD_INIT _BV(1)

#define PE_DDR	(_BV(STATUS_LED_BIT) | _BV(COMMON_PWM_BIT))
#define	PE_INIT	_BV(BL_SENSE_BIT)


// ---
// Catchup all unused interrupts and wait until watchdog resets device.
// This ISR is only for unexpected interrupts.
//
ISR(BADISR_vect)
{
	for (;;);
}


// ---
// ISR for PWM generation.
//
ISR(TIMER3_COMPA_vect)
{
	pwm_step_t *p = actual_pwm_step;

		// Optimized OCR3A = p->timer_val
	OCR3AH = ((uint8_t *)&(p->timer_val))[1];
	OCR3AL = ((uint8_t *)&(p->timer_val))[0];

	PORTA = p->port_val[PA_IDX];
	PORTB = p->port_val[PB_IDX];
	PORTC = p->port_val[PC_IDX];
	PORTD = p->port_val[PD_IDX];

		// Optimized actual_pwm_step = p->next_step
	((uint8_t *)&(actual_pwm_step))[0] = ((uint8_t *)&(p->next_step))[0];
	((uint8_t *)&(actual_pwm_step))[1] = ((uint8_t *)&(p->next_step))[1];
}


// ---
// ISR for receiving data.
//
ISR(USART0_RXC_vect)
{
	clear_bit(UCSR0B, RXCIE0);
	sei();

	do
	{
		uint8_t i = rxwpos;
		uint8_t p = i + 1;
		CHECK_RXBUF_END(p);
		if (p == rxrpos)
			set_bit(rx_err_status, COMM_ERR_OVERFLOW);
		else
			rxwpos = p;			// set data valid

		if (bit_is_set(UCSR0A, DOR0))
			set_bit(rx_err_status, COMM_ERR_OVERRUN);
		if (bit_is_set(UCSR0A, FE0))
			set_bit(rx_err_status, COMM_ERR_FRAME);
		if (bit_is_set(UCSR0B, RXB80))
			rxspos = i;		// save start of request message
	  rxbuf[i] = UDR0;	// read data
	}
	while (bit_is_set(UCSR0A, RXC0));

	cli();
	set_bit(UCSR0B, RXCIE0);
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
// Set on time 'v' for port bits 'pb' of port 'pi' in shadow pwm page.
//
static void set_channel(uint8_t pi, uint8_t pb, uint16_t v)
{
	pwm_step_t *p = shadow_pwm_page;
	pwm_step_t *l, *n;

	while (p->timer_val && v >= p->timer_val)
	{
		p->port_val[pi] |= pb;
		if (p->timer_val == v)
			return;
		l = p;
		p = l->next_step;
	}

	if (p->timer_val)
	{
		n = p;
		do
		{
			l = n;
			n = l->next_step;
		}	
		while (n->timer_val);

		l->next_step = n->next_step;
		n[0] = p[0];
		p->next_step = n;
	}
	else
	{					
		p->port_val[PA_IDX] = PA_INIT;
		p->port_val[PB_IDX] = PB_INIT;
		p->port_val[PC_IDX] = PC_INIT;
		p->port_val[PD_IDX] = PD_INIT;
	}
	p->timer_val = v;
	p->port_val[pi] |= pb;
}


// ---
// Init shadow pwm page.
//
static uint8_t init_pwm_page(uint8_t do_init)
{
	pwm_step_t *p = shadow_pwm_page;
	pwm_step_t *e = p + PWM_STEP_PAGE_SIZE;

		// Check if shadow page is deactivated
	cli();
	pwm_step_t *a = actual_pwm_step;
	sei();
	if (a >= p && a < e)
		return(0); // Shadow page is still active

	if (do_init)
	{
		while (p < e)
		{
			p->timer_val = 0;
			a = p + 1;
			p->next_step = a;
			p = a;
		}
	}

	return(1);
}


// ---
// Finalize shadow pwm page and activate it.
//
static void activate_pwm_page(void)
{
	pwm_step_t *p = shadow_pwm_page;
	pwm_step_t *l;
	uint16_t t = 0;

		// Calculate time steps
	while (p->timer_val)
	{
		uint16_t ts = p->timer_val - t;
		t = p->timer_val;
		p->timer_val = ts * PWM_PRESCALE;
		l = p;
		p = l->next_step;
	}

		// Add pause entry to reach a full cycle
	t = setup.max_pwm - t;
	if (t)
	{
		p->port_val[PA_IDX] = PA_INIT;
		p->port_val[PB_IDX] = PB_INIT;
		p->port_val[PC_IDX] = PC_INIT;
		p->port_val[PD_IDX] = PD_INIT;
		p->timer_val = t * PWM_PRESCALE;
		l = p;
	}

		// Make list cyclic
	p = shadow_pwm_page;
	l->next_step = p;
	
		// Install Link to shadow page in active page
	p = active_pwm_page;
	active_pwm_page = l;
	l = shadow_pwm_page;
	cli();
	p->next_step = l;
	sei();

		// Swap shadow page
	if (l == pwm_step_page1)
		p = pwm_step_page2;
	else
		p = pwm_step_page1;
	shadow_pwm_page = p;
	
	update_pwm_page = 0;
}


// ---
// Calculate pwm page.
//
static void calc_pwm_page(void)
{
	uint8_t c;

	c = NCHANNELS;
	while (c--)
	{
		uint8_t port_bits = setup.channel_map[c].port_bits;
		if (port_bits)
		{
			uint8_t code = setup.channel_map[c].code;
			uint16_t v = bright_vals[CM_CHANNEL(code)];
			if (v)
			{
				if (v > setup.max_pwm)
					v = setup.max_pwm;
				set_channel(CM_PORT(code), port_bits, v);
			}
		}
	}
}


// ---
// Initialize pwm step table and start pwm timer.
//
static void init_pwm_step_tab(void)
{
		// Set up pwm step table
	shadow_pwm_page = pwm_step_page1;
	active_pwm_page = pwm_step_page2;
	actual_pwm_step = pwm_step_page2;
	init_pwm_page(1);
	calc_pwm_page();
	activate_pwm_page();
	actual_pwm_step = active_pwm_page->next_step;

	TCNT3 = 0;	// Reset timer counter
	OCR3A = PWM_PRESCALE; // Initial startup step
	TCCR3B = _BV(CS32) | _BV(CS31) | _BV(WGM32);	// Start timer, Prescaler 16, CTC mode
}


// ---
// Set default setup values.
//
static void init_setup_values(void)
{
	setup.max_pwm = DEF_MAX_PWM;
	setup.common_pwm = DEF_COMMON_PWM;

	memcpy_P(&setup.channel_map, &default_channel_map, sizeof(setup.channel_map));
}


// ---
// Read setup values from eeprom.
//
static void read_setup_values(void)
{
	if (eeprom_read_byte(&ee_valid) == EE_VALID_MARK)
		eeprom_read_block(&setup, &ee_setup, sizeof(setup));
	else
		init_setup_values();
}


// ---
// Store actual setup values into eeprom.
//
static void store_setup_values(void)
{
	uint8_t i = sizeof(setup);
	uint8_t *src = (uint8_t *) (&setup);
	uint8_t *dst = (uint8_t *) (&ee_setup);
	while (i--)
	{
		if (eeprom_read_byte(dst) != *src)
		{
			eeprom_write_byte(dst, *src);
			while (!eeprom_is_ready())
				send_keep_alive_reply();
		}
		++src;
		++dst;
	}
	if (eeprom_read_byte(&ee_valid) != EE_VALID_MARK)
	{
		eeprom_write_byte(&ee_valid, EE_VALID_MARK);
		while (!eeprom_is_ready())
			send_keep_alive_reply();
	}
}


// ---
// Set common pwm value.
//
static void set_common_pwm(void)
{
	uint8_t v = setup.common_pwm;

	if (v == 0 || v == 255)
	{
		if (v)
			set_bit(COMMON_PWM_PORT, COMMON_PWM_BIT);
		else
			clear_bit(COMMON_PWM_PORT, COMMON_PWM_BIT);
		clear_bit(TCCR1A, COM1B1);	// Normal port output
	}
	else
	{
		OCR1B = v;
		clear_bit(COMMON_PWM_PORT, COMMON_PWM_BIT);
		set_bit(TCCR1A, COM1B1);		// pwm port output
	}
}


// ---
// Send reply packet from ram memory.
//
static void send_reply_mem(uint8_t *data, uint16_t len)
{
	pwm_request_t *r = &actual_req;
	FIX_POINTER(r);

	uint16_t p = r->index.word << 1;
	uint16_t n = r->length.word;
	if (p >= len)
		n = 0;
	if (n && (p + n) > len)
		n = len - p;
	if (n > MAX_REPLY_PAYLOAD_SIZE)
		n = 0;	// Send nothing!

	send_reply_start(n);

	data += p;
	while (n)
	{
		send_reply_data(*data++);
		--n;
	} 
}


// ---
// Process set brightness value.
//
static void req_set_brightness(void)
{
	pwm_request_t *r = &actual_req;
	FIX_POINTER(r);

	uint8_t p = payload_pos;
	uint16_t c = r->index.word;
	uint16_t len = r->length.word >> 1;
	while (len && c < NCHANNELS)
	{
		bytes_word_t v;
		v.bytes[0] = rxbuf[p++];
		CHECK_RXBUF_END(p);
		v.bytes[1] = rxbuf[p++];
		CHECK_RXBUF_END(p);

		if (bright_vals[c] != v.word)
		{
			bright_vals[c] = v.word;
			update_pwm_page = 1;
		}

		++c;
		--len;
	}
}


// ---
// Process set channel map request.
//
static void req_set_channel_map(void)
{
	pwm_request_t *r = &actual_req;
	FIX_POINTER(r);

	uint8_t p = payload_pos;
	uint16_t c = r->index.word;
	uint16_t len = r->length.word >> 1;
	while (len && c < NCHANNELS)
	{
		uint8_t v = rxbuf[p++];
		CHECK_RXBUF_END(p);

		if (CM_CHANNEL(v) >= NCHANNELS)
			v = NCHANNELS - 1;

		if (setup.channel_map[c].code != v)
		{
			setup.channel_map[c].code = v;
			update_pwm_page = 1;
		}

		v = rxbuf[p++];
		CHECK_RXBUF_END(p);

		if (setup.channel_map[c].port_bits != v)
		{
			setup.channel_map[c].port_bits = v;
			update_pwm_page = 1;
		}

		++c;
		--len;
	}
}


// ---
// Process received request.
//
static void process_request(void)
{				 
	pwm_request_t *r = &actual_req;
	FIX_POINTER(r);

	uint8_t req = r->request;

	if (req == PWM_REQ_SET_BRIGHTNESS)
		req_set_brightness();
	else if (req == PWM_REQ_SET_BRIGHTNESS_SYNCED)
	{
		req_set_brightness();
		if (update_pwm_page)
		{
			while (!init_pwm_page(0))
				background_processing();
		}
	}
	else if (req == PWM_REQ_GET_BRIGHTNESS)
	{
		send_reply_mem((uint8_t *)bright_vals, sizeof(bright_vals));
		return;
	}
	else if (req == PWM_REQ_SET_CHANNEL_MAP)
		req_set_channel_map();
	else if (req == PWM_REQ_GET_CHANNEL_MAP)
	{
		send_reply_mem((uint8_t *)&setup.channel_map, sizeof(setup.channel_map));
		return;
	}
	else if (req == PWM_REQ_STORE_SETUP)
		store_setup_values();
	else if (req == PWM_REQ_RESET_SETUP)
	{
		init_setup_values();
		update_pwm_page = 1;
		if (eeprom_read_byte(&ee_valid) == EE_VALID_MARK)
			eeprom_write_byte(&ee_valid, (uint8_t)(~EE_VALID_MARK));	// Invalidate eeprom values
	}
	else if (req == PWM_REQ_GET_REQUEST_ERR_STATUS)
	{
		send_reply_start(1);
		send_reply_data(rx_err_status);
		rx_err_status = 0;
		return;
	}
	else if (req == PWM_REQ_SET_COMMON_PWM)
	{
		setup.common_pwm = (r->value.word <= MAX_COMMON_PWM) ? r->value.bytes[0]: MAX_COMMON_PWM;
		set_common_pwm();
	}
	else if (req == PWM_REQ_GET_COMMON_PWM)
	{
		send_reply_start(2);
		send_reply_data(setup.common_pwm);
		send_reply_data(0);
		return;
	}
	else if (req == PWM_REQ_GET_MAX_PWM)
	{
		send_reply_start(4);
		send_reply_data((uint8_t)(setup.max_pwm & 0x00FF));
		send_reply_data((uint8_t)(setup.max_pwm >> 8));
		send_reply_data(MAX_COMMON_PWM);
		send_reply_data(0);
		return;
	}
	else if (req == PWM_REQ_SET_PWM_FREQ)
	{
		if (r->value.word >= MIN_PWM_FREQ && r->value.word <= MAX_PWM_FREQ)
		{
			setup.max_pwm = F_CPU / (PWM_HWPRESCALE * PWM_PRESCALE * (uint32_t)r->value.word) - 1;
			update_pwm_page = 1;
		}
	}
	else if (req == PWM_REQ_GET_PWM_FREQ)
	{
		uint16_t f = F_CPU / (((uint32_t)setup.max_pwm + 1) * PWM_HWPRESCALE * PWM_PRESCALE);
		send_reply_start(2);
		send_reply_data((uint8_t)(f & 0x00FF));
		send_reply_data((uint8_t)(f >> 8));
		return;
	}
	else if (req == PWM_REQ_GET_VERSION)
	{
		send_reply_start(2);
		send_reply_data(PWM_VERS_APPL);
		send_reply_data(FIRMWARE_VERSION);
		return;
	}
	else if (req == PWM_REQ_ECHO_TEST)
	{
		send_reply_start(8);
		send_reply_data(r->bytes[0]);
		send_reply_data(r->bytes[1]);
		send_reply_data(r->bytes[2]);
		send_reply_data(r->bytes[3]);
		send_reply_data(r->bytes[4]);
		send_reply_data(r->bytes[5]);
		send_reply_data(r->bytes[6]);
		send_reply_data(r->bytes[7]);
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
	PORTA = PA_INIT;
	PORTB = PB_INIT;
	PORTC = PC_INIT;
	PORTD = PD_INIT;
	PORTE = PE_INIT;
	DDRA = PA_DDR;
	DDRB = PB_DDR;
	DDRC = PC_DDR;
	DDRD = PD_DDR;
	DDRE = PE_DDR;

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

	read_setup_values();

		// Timer 0 is used for system clock
		// Normal mode, Prescaler 64
	TCCR0 = _BV(CS01) | _BV(CS00);

		// Timer 1 is used for common PWM generation
		// Fast 8-Bit PWM mode, Prescaler 1, PWM output at OC1B Pin 
	TCCR1A = _BV(WGM10);
	TCCR1B = _BV(WGM12) | _BV(CS10);
	set_common_pwm();

		// Timer 3 is used for PWM generation
	ETIMSK = _BV(OCIE3A);	// Enable timer 3 compare a interrupt
	init_pwm_step_tab();

		// Main loop
  for (;;)
  {	
		background_processing();

		if (rxrpos != rxwpos)
			read_data();

		if (update_pwm_page && init_pwm_page(1))
		{
			calc_pwm_page();
			activate_pwm_page();
		}

		if (update_pwm_page || header_pos)
			clear_bit(STATUS_LED_PORT, STATUS_LED_BIT); // We are processing a request
		else
			set_bit(STATUS_LED_PORT, STATUS_LED_BIT);		// No request
  }
}
