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

// ---
// Useful utility defines.
//
#define NOMEMINIT						__attribute__((section(".noinit")))
#define NORETURN						__attribute__((noreturn))
#define NOINLINE						__attribute__((noinline))
#define INLINE							__attribute__((inline))
#define nop()								__asm__ __volatile__ ("nop" ::)
#define FIX_POINTER(_ptr)		__asm__ __volatile__("" : "=b" (_ptr) : "0" (_ptr))
#define SIGNATURE_DATA uint8_t __signature[3] __attribute__((section(".signature")))

#define set_bit(var, bit)		var |= _BV(bit)	
#define clear_bit(var, bit)	var &= ~_BV(bit)	

typedef union
{
  uint16_t	word;
  uint8_t		bytes[2];
} bytes_word_t;


// Definitions for usb <--> pwm controller communication
#define BAUD 125000UL

#define REQ_HEADER_SIZE	8

#define PWMRQ_DEVICE_TO_HOST	0x80
#define PWMRQ_ID_MASK					0x3F
#define PWMRP_KEEP_ALIVE			0x80
#define PWMRP_HAS_PAYLOAD			0x40



