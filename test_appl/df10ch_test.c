/*
 * Copyright (C) 2009, 2010 Andreas Auras
 *
 * This file is part of the atmo post plugin, a plugin for the free xine video player.
 *
 * atmo post plugin is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * atmo post plugin is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110, USA
 *
 */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <ctype.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <sys/time.h>


/***************************************************************************************************
 *    DF10CH output driver for my own designed "next generation" 10ch RGB Controller
 ***************************************************************************************************/

#include <libusb.h>
#include "../df10ch_usb_proto.h"

#define DF10CH_USB_CFG_VENDOR_ID     0x16c0
#define DF10CH_USB_CFG_PRODUCT_ID    0x05dc
#define DF10CH_USB_CFG_VENDOR_NAME   "yak54@gmx.net"
#define DF10CH_USB_CFG_PRODUCT       "DF10CH"
#define DF10CH_USB_CFG_SERIAL        "AP"
#define DF10CH_USB_DEFAULT_TIMEOUT   100

#define DF10CH_MAX_CHANNELS     30

typedef struct df10ch_output_driver_s df10ch_output_driver_t;

typedef struct df10ch_ctrl_s {
  struct df10ch_ctrl_s *next;
  df10ch_output_driver_t *driver;
  libusb_device_handle *dev;
  int idx_serial_number;        // USB string index of serial number
  uint16_t pwm_res;             // PWM resolution
  char id[32];                  // ID of Controller
  struct libusb_transfer *transfer; // Prepared set brightness request for asynchrony submitting
  uint8_t *transfer_data;       // Data of set brightness request
  int pending_submit;           // Is true if a asynchrony transfer is pending
  int transfer_error;
} df10ch_ctrl_t;

struct df10ch_output_driver_s {
  libusb_context *ctx;
  df10ch_ctrl_t *ctrls;             // List of found controllers
  int max_transmit_latency;
  int avg_transmit_latency;
  int transfer_err_cnt;             // Number of transfer errors
};


static const char *df10ch_usb_errmsg(int rc) {
  switch (rc) {
  case LIBUSB_SUCCESS:
    return ("Success (no error)");
  case LIBUSB_ERROR_IO:
    return ("Input/output error");
  case LIBUSB_ERROR_INVALID_PARAM:
    return ("Invalid parameter");
  case LIBUSB_ERROR_ACCESS:
    return ("Access denied (insufficient permissions)");
  case LIBUSB_ERROR_NO_DEVICE:
    return ("No such device (it may have been disconnected)");
  case LIBUSB_ERROR_NOT_FOUND:
    return ("Entity not found");
  case LIBUSB_ERROR_BUSY:
    return ("Resource busy");
  case LIBUSB_ERROR_TIMEOUT:
    return ("Operation timed out");
  case LIBUSB_ERROR_OVERFLOW:
    return ("Overflow");
  case LIBUSB_ERROR_PIPE:
    return ("Pipe error");
  case LIBUSB_ERROR_INTERRUPTED:
    return ("System call interrupted (perhaps due to signal)");
  case LIBUSB_ERROR_NO_MEM:
    return ("Insufficient memory");
  case LIBUSB_ERROR_NOT_SUPPORTED:
    return ("Operation not supported or unimplemented on this platform");
  case LIBUSB_ERROR_OTHER:
    return ("Other error");
  }
  return ("?");
}


static const char * df10ch_usb_transfer_errmsg(int s) {
  switch (s) {
  case LIBUSB_TRANSFER_COMPLETED:
    return ("Transfer completed without error");
  case LIBUSB_TRANSFER_ERROR:
    return ("Transfer failed");
  case LIBUSB_TRANSFER_TIMED_OUT:
    return ("Transfer timed out");
  case LIBUSB_TRANSFER_CANCELLED:
    return ("Transfer was cancelled");
  case LIBUSB_TRANSFER_STALL:
    return ("Control request stalled");
  case LIBUSB_TRANSFER_NO_DEVICE:
    return ("Device was disconnected");
  case LIBUSB_TRANSFER_OVERFLOW:
    return ("Device sent more data than requested");
  }
  return ("?");
}


static void df10ch_comm_errmsg(int stat, char *rc) {
  if (stat == 0)
    strcpy(rc, "OK");
  else
    *rc = 0;
  if (stat & (1<<COMM_ERR_OVERRUN))
      strcat(rc, " OVERRUN");
  if (stat & (1<<COMM_ERR_FRAME))
      strcat(rc, " FRAME");
  if (stat & (1<<COMM_ERR_TIMEOUT))
      strcat(rc, " TIMEOUT");
  if (stat & (1<<COMM_ERR_START))
      strcat(rc, " START");
  if (stat & (1<<COMM_ERR_OVERFLOW))
      strcat(rc, " OVERFLOW");
  if (stat & (1<<COMM_ERR_CRC))
      strcat(rc, " CRC");
  if (stat & (1<<COMM_ERR_DUPLICATE))
      strcat(rc, " DUPLICATE");
  if (stat & (1<<COMM_ERR_DEBUG))
      strcat(rc, " DEBUG");
}


static int df10ch_control_in_transfer(df10ch_ctrl_t *ctrl, uint8_t req, uint16_t val, uint16_t index, unsigned int timeout, uint8_t *buf, uint16_t buflen)
{
      // Use a return buffer always so that the controller is able to send a USB reply status
      // This is special for VUSB at controller side
    unsigned char rcbuf[1];
    int len = buflen;
    if (!len)
    {
        buf = rcbuf;
        len = 1;
    }

      // Because VUSB at controller sends ACK reply before CRC check of received data we have to retry sending request our self if data is corrupted
    int n = 0, retrys = 0;
    while (retrys < 3)
    {
        n = libusb_control_transfer(ctrl->dev, LIBUSB_ENDPOINT_IN | LIBUSB_REQUEST_TYPE_VENDOR | LIBUSB_RECIPIENT_DEVICE, req, val, index, buf, len, timeout);
        if (n != LIBUSB_ERROR_INTERRUPTED)
        {
            if (n < 0)
              ++ctrl->driver->transfer_err_cnt;
            if (n >= 0 || n != LIBUSB_ERROR_PIPE)
                break;
            ++retrys;
            printf( "%s: sending USB control transfer message %d failed (pipe error): retry %d\n", ctrl->id, req, retrys);
        }
    }

    if (n < 0)
    {
        printf( "%s: sending USB control transfer message %d failed: %s\n", ctrl->id, req, df10ch_usb_errmsg(n));
        return -1;
    }

    if (n != buflen)
    {
        printf( "%s: sending USB control transfer message %d failed: read %d bytes but expected %d bytes\n", ctrl->id, req, n, buflen);
        return -1;
    }

    return 0;
}


static void df10ch_dispose(df10ch_output_driver_t *this) {
  df10ch_ctrl_t *ctrl = this->ctrls;
  while (ctrl) {
    libusb_free_transfer(ctrl->transfer);
    libusb_release_interface(ctrl->dev, 0);
    libusb_close(ctrl->dev);

    df10ch_ctrl_t *next = ctrl->next;
    free(ctrl->transfer_data);
    free(ctrl);
    ctrl = next;
  }

  if (this->ctx)
    libusb_exit(this->ctx);

  this->ctrls = NULL;
  this->ctx = NULL;
}


static void df10ch_read_status(df10ch_output_driver_t *this, int always) {
  df10ch_ctrl_t *ctrl = this->ctrls;
  while (ctrl) {
    if (ctrl->transfer_error || always) {
      char reply_errmsg[128], request_errmsg[128];
      uint8_t data[1];
      if (df10ch_control_in_transfer(ctrl, REQ_GET_REPLY_ERR_STATUS, 0, 0, DF10CH_USB_DEFAULT_TIMEOUT, data, 1))
        strcpy(reply_errmsg, "N/A");
      else
        df10ch_comm_errmsg(data[0], reply_errmsg);
      if (df10ch_control_in_transfer(ctrl, PWM_REQ_GET_REQUEST_ERR_STATUS, 0, 0, DF10CH_USB_DEFAULT_TIMEOUT, data, 1))
        strcpy(request_errmsg, "N/A");
      else
        df10ch_comm_errmsg(data[0], request_errmsg);
      printf( "%s: comm error USB: %s, PWM: %s\n", ctrl->id, reply_errmsg, request_errmsg);
    }
    ctrl = ctrl->next;
  }
}


static void df10ch_wait_for_replys(df10ch_output_driver_t *this) {
    // wait for end of all pending transfers
  struct timeval timeout;
  timeout.tv_sec = 0;
  timeout.tv_usec = (DF10CH_USB_DEFAULT_TIMEOUT + 50) * 1000;
  df10ch_ctrl_t *ctrl = this->ctrls;
  while (ctrl) {
    if (ctrl->pending_submit) {
      int rc = libusb_handle_events_timeout(this->ctx, &timeout);
      if (rc && rc != LIBUSB_ERROR_INTERRUPTED) {
        printf( "handling USB events failed: %s\n", df10ch_usb_errmsg(rc));
        break;
      }
    }
    else
      ctrl = ctrl->next;
  }
  df10ch_read_status(this, 0);
}


static void df10ch_reply_cb(struct libusb_transfer *transfer) {
  df10ch_ctrl_t *ctrl = (df10ch_ctrl_t *) transfer->user_data;
  ctrl->pending_submit = 0;
  if (transfer->status != LIBUSB_TRANSFER_COMPLETED && transfer->status != LIBUSB_TRANSFER_CANCELLED) {
    ++ctrl->driver->transfer_err_cnt;
    ctrl->transfer_error = 1;
    printf( "%s: submitting USB control transfer message failed: %s\n", ctrl->id, df10ch_usb_transfer_errmsg(transfer->status));
  }
}


static int df10ch_driver_open(df10ch_output_driver_t *this) {

  this->max_transmit_latency = 0;
  this->avg_transmit_latency = 0;
  this->transfer_err_cnt = 0;

  if (libusb_init(&this->ctx) < 0) {
    printf("can't initialize USB library\n");
    return -1;
  }

  libusb_device **list = NULL;
  size_t cnt = libusb_get_device_list(this->ctx, &list);
  if (cnt < 0) {
    printf("getting list of USB devices failed: %s\n", df10ch_usb_errmsg(cnt));
    df10ch_dispose(this);
    return -1;
  }

    // Note: Because controller uses obdev's free USB product/vendor ID's we have to do special lookup for finding
    // the controllers. See file "USB-IDs-for-free.txt" of VUSB distribution.
  int rc;
  size_t i;
  for (i = 0; i < cnt; i++) {
    libusb_device *d = list[i];
    struct libusb_device_descriptor desc;

    int busnum = libusb_get_bus_number(d);
    int devnum = libusb_get_device_address(d);

    rc = libusb_get_device_descriptor(d, &desc);
    if (rc < 0)
      printf( "USB[%d,%d]: getting USB device descriptor failed: %s\n", busnum, devnum, df10ch_usb_errmsg(rc));
    else if (desc.idVendor == DF10CH_USB_CFG_VENDOR_ID && desc.idProduct == DF10CH_USB_CFG_PRODUCT_ID) {
      libusb_device_handle *hdl = NULL;
      rc = libusb_open(d, &hdl);
      if (rc < 0)
        printf( "USB[%d,%d]: open of USB device failed: %s\n", busnum, devnum, df10ch_usb_errmsg(rc));
      else {
        unsigned char buf[256];
        rc = libusb_get_string_descriptor_ascii(hdl, desc.iManufacturer, buf, sizeof(buf));
        if (rc < 0)
          printf( "USB[%d,%d]: getting USB manufacturer string failed: %s\n", busnum, devnum, df10ch_usb_errmsg(rc));
        else if (rc == sizeof(DF10CH_USB_CFG_VENDOR_NAME) - 1 && !memcmp(buf, DF10CH_USB_CFG_VENDOR_NAME, rc)) {
          rc = libusb_get_string_descriptor_ascii(hdl, desc.iProduct, buf, sizeof(buf));
          if (rc < 0)
            printf( "USB[%d,%d]: getting USB product string failed: %s\n", busnum, devnum, df10ch_usb_errmsg(rc));
          else if (rc == sizeof(DF10CH_USB_CFG_PRODUCT) - 1 && !memcmp(buf, DF10CH_USB_CFG_PRODUCT, rc)) {
            char id[32];
            snprintf(id, sizeof(id), "DF10CH[%d,%d]", busnum, devnum);
            rc = libusb_set_configuration(hdl, 1);
            if (rc < 0)
              printf( "%s: setting USB configuration failed: %s\n", id, df10ch_usb_errmsg(rc));
            else {
              rc = libusb_claim_interface(hdl, 0);
              if (rc < 0)
                printf( "%s: claiming USB interface failed: %s\n", id, df10ch_usb_errmsg(rc));
              else {
                df10ch_ctrl_t *ctrl = (df10ch_ctrl_t *) calloc(1, sizeof(df10ch_ctrl_t));
                ctrl->next = this->ctrls;
                this->ctrls = ctrl;
                ctrl->driver = this;
                ctrl->dev = hdl;
                ctrl->idx_serial_number = desc.iSerialNumber;
                strcpy(ctrl->id, id);
                printf( "%s: device opened\n", id);
                continue;
              }
            }
          }
        }
        libusb_close(hdl);
      }
    }
  }

  libusb_free_device_list(list, 1);

  if (!this->ctrls) {
    printf("USB: no DF10CH devices found!\n");
    df10ch_dispose(this);
    return -1;
  }

    // Read controller configuration
  df10ch_ctrl_t *ctrl = this->ctrls;
  while (ctrl) {
    uint8_t data[256];

      // Read PWM resolution
    if (df10ch_control_in_transfer(ctrl, PWM_REQ_GET_MAX_PWM, 0, 0, DF10CH_USB_DEFAULT_TIMEOUT, data, 2)) {
      printf("%s: reading PWM resolution data fails!\n", ctrl->id);
      df10ch_dispose(this);
      return -1;
    }
    ctrl->pwm_res = data[0] + (data[1] << 8);

      // Prepare USB request for sending brightness values
    ctrl->transfer_data = calloc(1, (LIBUSB_CONTROL_SETUP_SIZE + DF10CH_MAX_CHANNELS * 2));
    libusb_fill_control_setup(ctrl->transfer_data, LIBUSB_ENDPOINT_OUT | LIBUSB_REQUEST_TYPE_VENDOR | LIBUSB_RECIPIENT_DEVICE, PWM_REQ_SET_BRIGHTNESS, 0, 0, DF10CH_MAX_CHANNELS * 2);
    ctrl->transfer = libusb_alloc_transfer(0);
    libusb_fill_control_transfer(ctrl->transfer, ctrl->dev, ctrl->transfer_data, df10ch_reply_cb, ctrl, DF10CH_USB_DEFAULT_TIMEOUT);
    ctrl->pending_submit = 0;

    ctrl = ctrl->next;
  }

  return 0;
}


static int df10ch_driver_close(df10ch_output_driver_t *this) {

    // Cancel all pending requests
  df10ch_ctrl_t *ctrl = this->ctrls;
  while (ctrl) {
    if (ctrl->pending_submit)
      libusb_cancel_transfer(ctrl->transfer);
    ctrl = ctrl->next;
  }

  df10ch_wait_for_replys(this);
  df10ch_read_status(this, 1);
  df10ch_dispose(this);

  printf( "average transmit latency: %d [us]\n", this->avg_transmit_latency);

  if (this->transfer_err_cnt) {
    printf("%d transfer errors happen\n", this->transfer_err_cnt);
    return -1;
  }
  return 0;
}


static void df10ch_driver_output_colors(df10ch_output_driver_t *this, uint8_t *data, int len) {
  struct timeval tvnow, tvlast, tvdiff;

  gettimeofday(&tvlast, NULL);

    // Generate transfer messages and send it to controllers
  df10ch_ctrl_t *ctrl = this->ctrls;
  while (ctrl) {
      // Generate payload data (brightness values)
    uint8_t *payload = ctrl->transfer_data + LIBUSB_CONTROL_SETUP_SIZE;
    memcpy(payload, data, len);

      // initiate asynchron data transfer to controller
    ctrl->transfer_error = 0;
    int rc = libusb_submit_transfer(ctrl->transfer);
    if (rc)
      printf( "%s: submitting USB control transfer message failed: %s\n", ctrl->id, df10ch_usb_errmsg(rc));
    else
      ctrl->pending_submit = 1;

    ctrl = ctrl->next;
  }

    // wait for end of all pending transfers
  df10ch_wait_for_replys(this);

  gettimeofday(&tvnow, NULL);
  timersub(&tvnow, &tvlast, &tvdiff);
  this->avg_transmit_latency = (this->avg_transmit_latency + tvdiff.tv_usec) / 2;
  if (tvdiff.tv_usec > this->max_transmit_latency) {
    this->max_transmit_latency = tvdiff.tv_usec;
    printf( "max/avg transmit latency: %d/%d [us]\n", this->max_transmit_latency, this->avg_transmit_latency);
  }
}

static df10ch_output_driver_t driver;
static uint16_t bright[DF10CH_MAX_CHANNELS];

int main(int argc, char **argv) {
  int n, i, b;

  if (argc > 1)
    n = atoi(argv[1]);
  else
    n = 1;

  if (!df10ch_driver_open(&driver)) {
    int pwm_res = driver.ctrls->pwm_res - DF10CH_MAX_CHANNELS;

    while (n--) {
      b = 0;
      while (b < pwm_res) {
        for (i = 0; i < DF10CH_MAX_CHANNELS; ++i)
          bright[i] = b++;
        df10ch_driver_output_colors(&driver, (uint8_t *) bright, sizeof(bright));
        //usleep(100*1000);
      }
      b = driver.ctrls->pwm_res - 1;
      while (b > DF10CH_MAX_CHANNELS) {
        for (i = 0; i < DF10CH_MAX_CHANNELS; ++i)
          bright[i] = b--;
        df10ch_driver_output_colors(&driver, (uint8_t *) bright, sizeof(bright));
        //usleep(100*1000);
      }
    }

    df10ch_driver_close(&driver);
  }
  return 0;
}
