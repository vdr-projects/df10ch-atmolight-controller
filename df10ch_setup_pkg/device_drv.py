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
# This file is part of the DF10CH setup program
#

import os
import time
import pickle
import string
import array

# ---
# Communication protocol related defines for 10 channel RGB Controller.
#
VENDOR_ID = 0x16c0
PRODUCT_ID = 0x05dc
VENDOR_NAME = 'yak54@gmx.net'
DEVICE_NAME = 'DF10CH'

REQ_USB_START = 0       # Start of usb controller requests
REQ_USB_BL_START = 64   # Start of usb controller boot loader requests
REQ_PWM_START = 128     # Start of pwm controller requests
REQ_PWM_BL_START = 192  # Start of pwm controller bootloader requests

    # usb controller requests
for i, key in enumerate([
        'REQ_START_BOOTLOADER', # start boot loader of usb controller

        'REQ_READ_EE_DATA', # read eeprom data (wLength: number of bytes, wIndex: eeprom start address)
        'REQ_WRITE_EE_DATA', # write eeprom data (wLength: number of bytes, wIndex: eeprom start address)

        'REQ_STOP_PWM_CTRL', # stop PWM controller
        'REQ_RESET_PWM_CTRL', # reset PWM controller
        'REQ_BOOTLOADER_RESET_PWM_CTRL', # reset PWM controller and signal bootloader start

        'REQ_SET_REPLY_TIMEOUT', # set reply timeout values (wValue: start timeout [ms], wIndex: timeout [ms])
        'REQ_GET_REPLY_ERR_STATUS' # get reply error status (COMM_ERR_...)
        ], start = REQ_USB_START):
    exec key + ' = ' + repr(i)

    # usb controller boot loader requests
for i, key in enumerate([
        'BL_REQ_WRITE_PAGE',                # write flash page
        'BL_REQ_LEAVE_BOOT',                # leave boot loader and start application
        'BL_REQ_GET_PAGE_SIZE',             # return flash page size of device
        'BL_REQ_READ_FLASH'                 # read flash memory
        ], start = REQ_USB_BL_START):
    exec key + ' = ' + repr(i)

    # pwm controller requests
for i, key in enumerate([
        'PWM_REQ_GET_VERSION', # Get firmware version

        'PWM_REQ_SET_BRIGHTNESS', # Set channel brightness values (wLenght: number of bytes, wIndex: start channel)
        'PWM_REQ_SET_BRIGHTNESS_SYNCED',
        'PWM_REQ_GET_BRIGHTNESS',

        'PWM_REQ_SET_CHANNEL_MAP', # Set channel to port mapping (wLength: number of bytes, wIndex: start channel)
        'PWM_REQ_GET_CHANNEL_MAP',

        'PWM_REQ_SET_COMMON_PWM', # Set common pwm value (wValue.low: pwm value)
        'PWM_REQ_GET_COMMON_PWM',

        'PWM_REQ_STORE_SETUP', # Store actual calibration values
        'PWM_REQ_RESET_SETUP', # Reset calibration values to default

        'PWM_REQ_GET_REQUEST_ERR_STATUS', # Get request error status (COMM_ERR_...)

        'PWM_REQ_GET_MAX_PWM',        # Get maximum internal PWM value

        'PWM_REQ_SET_PWM_FREQ',
        'PWM_REQ_GET_PWM_FREQ',
        
        'PWM_REQ_ECHO_TEST'     ## Reply 8 byte header
        ], start = REQ_PWM_START):
    exec key + '=' + repr(i)

    # pwm controller boot loader requests
for i, key in enumerate([
        'BL_PWM_REQ_WRITE_PAGE',    # write flash page
        'BL_PWM_REQ_GET_PAGE_SIZE', # return flash page size of device
        'BL_PWM_REQ_READ_FLASH',    # read flash memory
        'BL_PWM_REQ_GET_REQUEST_ERR_STATUS', # Get request error status (COMM_ERR_...)
        ], start = REQ_PWM_BL_START):
    exec key + ' = ' + repr(i)

    # Data payload related
MAX_PWM_REQ_PAYLOAD_SIZE = 128
MAX_PWM_REPLY_PAYLOAD_SIZE = 128

# Error flag definition for communication error's between usb and pwm controller
COMM_ERR_OVERRUN = 0
COMM_ERR_FRAME = 1
COMM_ERR_TIMEOUT = 2
COMM_ERR_START = 3
COMM_ERR_OVERFLOW = 4
COMM_ERR_CRC = 5
COMM_ERR_DUPLICATE = 6
COMM_ERR_DEBUG = 7

# Port channel mapping related
NCHANNELS = 30  # Number of supported Channels

NPORTS = 4
PA_IDX = 0
PB_IDX = 1
PC_IDX = 2
PD_IDX = 3

def CM_CODE(port, channel):
    return(((channel) << 2) | (port))
def CM_CHANNEL(code):
    return((code) >> 2)
def CM_PORT(code):
    return((code) & 0x03)
def CM_BV(bit):
    return (1<<bit)
def CM_BIT(bv):
    i = 0
    while bv:
        i = i + 1
        bv = bv >> 1
    return i - 1


PORT_NAME_MAP = {
    # J3
" 1.1": ( PA_IDX, CM_BV(2) ),
" 1.2": ( PA_IDX, CM_BV(1) ),
" 1.3": ( PA_IDX, CM_BV(0) ),

    # J4
" 2.1": ( PA_IDX, CM_BV(5) ),
" 2.2": ( PA_IDX, CM_BV(4) ),
" 2.3": ( PA_IDX, CM_BV(3) ),

    # J5
" 3.1": ( PC_IDX, CM_BV(7) ),
" 3.2": ( PA_IDX, CM_BV(7) ),
" 3.3": ( PA_IDX, CM_BV(6) ),

    # J6
" 4.1": ( PC_IDX, CM_BV(4) ),
" 4.2": ( PC_IDX, CM_BV(5) ),
" 4.3": ( PC_IDX, CM_BV(6) ),

    # J7
" 5.1": ( PC_IDX, CM_BV(1) ),
" 5.2": ( PC_IDX, CM_BV(2) ),
" 5.3": ( PC_IDX, CM_BV(3) ),

    # J8
" 6.1": ( PD_IDX, CM_BV(6) ),
" 6.2": ( PD_IDX, CM_BV(7) ),
" 6.3": ( PC_IDX, CM_BV(0) ),

    # J9
" 7.1": ( PD_IDX, CM_BV(3) ),
" 7.2": ( PD_IDX, CM_BV(4) ),
" 7.3": ( PD_IDX, CM_BV(5) ),

    # J10
" 8.1": ( PB_IDX, CM_BV(6) ),
" 8.2": ( PB_IDX, CM_BV(7) ),
" 8.3": ( PD_IDX, CM_BV(2) ),

    # J11
" 9.1": ( PB_IDX, CM_BV(3) ),
" 9.2": ( PB_IDX, CM_BV(4) ),
" 9.3": ( PB_IDX, CM_BV(5) ),

    # J12
"10.1": ( PB_IDX, CM_BV(0) ),
"10.2": ( PB_IDX, CM_BV(1) ),
"10.3": ( PB_IDX, CM_BV(2) )
}

# Brightness related
NBRIGHTS = 256
NCOMMONBRIGHTS = 256

# PWM frequency related
MIN_PWM_FREQ = 50
MAX_PWM_FREQ = 400

# PWM controller version request related
PWM_VERS_APPL = 0        # Is application firmware
PWM_VERS_BOOT = 1        # Is bootloader firmware

# USB related
DEF_USB_TIMEOUT = 100
DEF_RETRY = 3

def GetCommErrMsg(stat):
    if stat == 0:
        rc = 'OK'
    else:
        rc = ''
    if stat & (1<<COMM_ERR_OVERRUN):
        rc = rc + " OVERRUN"
    if stat & (1<<COMM_ERR_FRAME):
        rc = rc + " FRAME"
    if stat & (1<<COMM_ERR_TIMEOUT):
        rc = rc + " TIMEOUT"
    if stat & (1<<COMM_ERR_START):
        rc = rc + " START"
    if stat & (1<<COMM_ERR_OVERFLOW):
        rc = rc + " OVERFLOW"
    if stat & (1<<COMM_ERR_CRC):
        rc = rc + " CRC"
    if stat & (1<<COMM_ERR_DUPLICATE):
        rc = rc + " DUPLICATE"
    if stat & (1<<COMM_ERR_DEBUG):
        rc = rc + " DEBUG"
    return rc


CONFIG_VALID_ID = 0xA0A1
CONFIG_VERSION = 0x0002
CONFIG_CLASS_VERSION = 0x0002

DEFAULT_GAMMA_VAL = 22
MIN_GAMMA_VAL = 10
MAX_GAMMA_VAL = 50

DEFAULT_OVERSCAN = 30
MIN_OVERSCAN = 0
MAX_OVERSCAN = 200

DEFAULT_EDGE_WEIGHTING = 60
MIN_EDGE_WEIGHTING = 10
MAX_EDGE_WEIGHTING = 200

DEFAULT_ANALYZE_SIZE = 1
MIN_ANALYZE_SIZE = 0
MAX_ANALYZE_SIZE = 5

AREA_NAMES = "Top", "Bottom", "Left", "Right", "Center", "TopLeft", "TopRight", "BottomLeft", "BottomRight"
MAX_AREAS = 30, 30, 30, 30, 1, 1, 1, 1, 1

def NumBaseAreas():
    return len(AREA_NAMES)

def AreaIndex(area):
    return AREA_NAMES.index(area)

def AreaName(code, areaNum):
    areaIdx = code >> 2
    if areaIdx < 4:
        return "{0}-{1}".format(AREA_NAMES[areaIdx], areaNum + 1)
    if areaIdx < NumBaseAreas():
        return AREA_NAMES[areaIdx]
    return None

COLOR_NAMES = "red", "green", "blue"

def ColorIndex(name):
    return COLOR_NAMES.index(name)

def ColorName(code):
    return COLOR_NAMES[code & 0x03]

def AreaCode(area, color):
    s = string.split(area, '-')
    areaIdx = AreaIndex(s[0])
    if areaIdx < 4:
        areaNum = int(s[1]) - 1
    else:
        areaNum = 0
    return ((areaIdx << 2) + (color & 0x03)), areaNum


class DeviceError(Exception):
    def __init__(self, msg):
        self.message = msg

    def __str__(self):
        return self.message


class AtmoControllerError(Exception):
    def __init__(self, dev, msg):
        self.id = dev.id
        self.message = msg

    def __str__(self):
        return '{0}: {1}'.format(self.id, self.message)


    
class DF10CHController:
    '''
    Interface to DF10CH RGB Controller
    '''

    def __init__(self, usbdev, busnum, devnum, version, serial):
        self.usbdev = usbdev
        self.busnum = busnum
        self.devnum = devnum
        self.version = version
        self.serial = serial
        self.id = 'DF10CH[{0},{1}]'.format(self.busnum, self.devnum)
        self.error_count = 0
        
    def release(self):
        self.usbdev.releaseInterface(0)
        self.usbdev.close()

    def bootloader_mode(self):
        return self.serial == "BL"
    
    def ctrl_write(self, req, value, index, data, timeout = DEF_USB_TIMEOUT, retry = DEF_RETRY):
        if isinstance(data, basestring):
            sdata = data
        else:
            if isinstance(data, bytearray):
                bdata = data
            else:
                l = len(data)
                bdata = bytearray(l)
                while l:
                    l = l - 1
                    bdata[l] = data[l]
            sdata = str(bdata)
            
        while retry > 0:
            try:
                retry = retry - 1
                written = self.usbdev.controlWrite(libusb1.LIBUSB_RECIPIENT_DEVICE|libusb1.LIBUSB_TYPE_VENDOR, req, value, index, sdata, timeout)
            except libusb1.USBError as err:
                self.error_count = self.error_count + 1
                print 'write req={0}, retry={1}: {2}'.format(req, retry, err.__str__())
                if retry == 0 or err.value != libusb1.LIBUSB_ERROR_PIPE:
                    raise AtmoControllerError(self, 'write req={0}: {1}'.format(req, err.__str__()))
            else:
                if written != len(data):
                    self.error_count = self.error_count + 1
                    raise AtmoControllerError(self, 'write req={0}: could not write all payload data'.format(req))
                break

    def ctrl_read(self, req,  value = 0, index = 0, size = 0, timeout = DEF_USB_TIMEOUT, retry = DEF_RETRY):
        if size > 0:
            n = size
        else:
            n = 1
        while retry > 0:
            try:
                retry = retry - 1
                data = self.usbdev.controlRead(libusb1.LIBUSB_RECIPIENT_DEVICE|libusb1.LIBUSB_TYPE_VENDOR, req, value, index, n, timeout)
            except libusb1.USBError as err:
                print 'read req={0}, retry={1}: {2}'.format(req, retry, err.__str__())
                if retry == 0 or err.value != libusb1.LIBUSB_ERROR_PIPE:
                    self.error_count = self.error_count + 1
                    raise AtmoControllerError(self, 'read req={0}: {1}'.format(req, err.__str__()))
            else:
                if len(data) != size:
                    self.error_count = self.error_count + 1
                    raise AtmoControllerError(self, 'read req={0}: could not read all payload data'.format(req))
                break
        return bytearray(data)

    def pwm_ctrl_write(self, req, value, index, data, timeout = DEF_USB_TIMEOUT, retry = DEF_RETRY):
        if len(data) > MAX_PWM_REQ_PAYLOAD_SIZE:
            self.error_count = self.error_count + 1
            raise AtmoControllerError(self, 'to many bytes in payload request data')
        self.ctrl_write(req, value, index, data, timeout, retry)
        
    def pwm_ctrl_read(self, req,  value = 0, index = 0, size = 0, timeout = DEF_USB_TIMEOUT, retry = DEF_RETRY):
        if size > MAX_PWM_REPLY_PAYLOAD_SIZE:
            self.error_count = self.error_count + 1
            raise AtmoControllerError(self, 'to many bytes for reply payload data')
        return self.ctrl_read(req, value, index, size, timeout, retry)

    def verify_reply_data(self, start, data, rdata, msg):    
        for i in range(len(data)):
            if data[i] != rdata[i]:
                self.error_count = self.error_count + 1
                raise AtmoControllerError(self, '{4}: verify of written {3} data fails {0:04X}: write {1:02X} read {2:02X}'.format(start + i, data[i], rdata[i], msg, self.id))

    def read_ee_data(self, start, size):
        return self.ctrl_read(REQ_READ_EE_DATA, 0, start, size)
 
    def write_ee_data(self, start, data):
        self.ctrl_write(REQ_WRITE_EE_DATA, 0, start, data, DEF_USB_TIMEOUT + len(data) * 10)
        eedata = self.read_ee_data(start, len(data))
        self.verify_reply_data(start, data, eedata, 'eeprom')

    def stop_pwm_ctrl(self):
        self.ctrl_read(REQ_STOP_PWM_CTRL)

    def reset_pwm_ctrl(self):
        self.ctrl_read(REQ_RESET_PWM_CTRL)
        
    def start_pwm_ctrl_bootloader(self):
        self.ctrl_read(REQ_BOOTLOADER_RESET_PWM_CTRL)
        
    def set_reply_timeout(self, start_timeout, timeout):
        self.ctrl_read(REQ_SET_REPLY_TIMEOUT, start_timeout, timeout)
        
    def get_reply_error_status(self):
        data = self.ctrl_read(REQ_GET_REPLY_ERR_STATUS, 0, 0, 1)
        return data[0]

    def start_bootloader(self):
        self.ctrl_read(REQ_START_BOOTLOADER)

    def start_appl(self):
        self.ctrl_read(BL_REQ_LEAVE_BOOT)

    def get_flash_page_size(self):
        data = self.ctrl_read(BL_REQ_GET_PAGE_SIZE, 0, 0, 2)
        return data[0] + data[1] * 256

    def write_flash_page(self, addr, data):
        self.ctrl_write(BL_REQ_WRITE_PAGE, 0, addr, data)

    def read_flash(self, addr, len):
        return self.ctrl_read(BL_REQ_READ_FLASH, 0, addr, len)

    def get_request_error_status(self):
        data = self.pwm_ctrl_read(PWM_REQ_GET_REQUEST_ERR_STATUS, 0, 0, 1)
        return data[0]
    
    def set_brightness(self, start, values):
        l = len(values)
        data = bytearray(l*2)
        for i in range(l):
            data[i*2] = values[i] & 0x00FF
            data[i*2+1] = values[i] / 256
        self.pwm_ctrl_write(PWM_REQ_SET_BRIGHTNESS, 0, start, data)
    
    def set_brightness_synced(self, start, values):
        l = len(values)
        data = bytearray(l*2)
        for i in range(l):
            data[i*2] = values[i] & 0x00FF
            data[i*2+1] = values[i] / 256
        self.pwm_ctrl_write(PWM_REQ_SET_BRIGHTNESS_SYNCED, 0, start, data)
    
    def get_brightness(self, start, nch):
        data = self.pwm_ctrl_read(PWM_REQ_GET_BRIGHTNESS, 0, start, nch * 2)
        values = array.array('H')
        for i in range(nch):
            values.append(data[i*2] + data[i*2+1] * 256)
        return values;

    def get_channel_map(self, start, nch):
        data = self.pwm_ctrl_read(PWM_REQ_GET_CHANNEL_MAP, 0, start, nch * 2)
        map = list()
        for i in range(nch):
            map.append(dict(channel=CM_CHANNEL(data[i*2]), port=CM_PORT(data[i*2]), pins=data[i*2+1]))
        return map;
                    
    def set_channel_map(self, start, map):
        data = bytearray()
        for mapRec in map:
            data.append(CM_CODE(mapRec['port'], mapRec['channel']))
            data.append(mapRec['pins'])
        self.pwm_ctrl_write(PWM_REQ_SET_CHANNEL_MAP, 0, start, data)
                    
    def set_common_brightness(self, value):
        self.pwm_ctrl_read(PWM_REQ_SET_COMMON_PWM, value)

    def get_common_brightness(self):
        data = self.pwm_ctrl_read(PWM_REQ_GET_COMMON_PWM, 0, 0, 2)
        return data[0] + data[1] * 256;

    def get_max_pwm_value(self):
        data = self.pwm_ctrl_read(PWM_REQ_GET_MAX_PWM, 0, 0, 4)
        return data[0] + 256 * data[1]
 
    def get_common_max_pwm_value(self):
        data = self.pwm_ctrl_read(PWM_REQ_GET_MAX_PWM, 0, 0, 4)
        return data[2] + 256 * data[3]
 
    def set_pwm_freq(self, value):
        self.pwm_ctrl_read(PWM_REQ_SET_PWM_FREQ, value)
        
    def get_pwm_freq(self):
        data = self.pwm_ctrl_read(PWM_REQ_GET_PWM_FREQ, 0, 0, 2)
        return data[0] + 256 * data[1]
 
    def store_setup(self):
        self.pwm_ctrl_read(PWM_REQ_STORE_SETUP, 0, 0, 0, 1500)
    
    def reset_setup(self):
        self.pwm_ctrl_read(PWM_REQ_RESET_SETUP)
        
    def get_pwm_bootloader_mode(self):
        data = self.pwm_ctrl_read(PWM_REQ_GET_VERSION, 0, 0, 2)
        return (data[0] == PWM_VERS_BOOT)
    
    def get_pwm_version(self):
        data = self.pwm_ctrl_read(PWM_REQ_GET_VERSION, 0, 0, 2)
        return data[1]
    
    def pwm_echo_test(self, testValue):
        v = testValue & 0x0FFFF
        i = testValue >> 16
        data = self.pwm_ctrl_read(PWM_REQ_ECHO_TEST, v, i, 8)
        if (data[2] + data[3] * 256) != v or (data[4] + data[5] * 256) != i:
            raise AtmoControllerError(self, 'echo test fails for value {0}'.format(testValue))
    
    def get_pwm_flash_page_size(self):
        data = self.pwm_ctrl_read(BL_PWM_REQ_GET_PAGE_SIZE, 0, 0, 2)
        return data[0] + data[1] * 256

    def write_pwm_flash_page(self, addr, data):
        self.pwm_ctrl_write(BL_PWM_REQ_WRITE_PAGE, 0, addr, data)

    def read_pwm_flash(self, addr, len):
        return self.pwm_ctrl_read(BL_PWM_REQ_READ_FLASH, 0, addr, len)

    def get_bootloader_request_error_status(self):
        data = self.pwm_ctrl_read(BL_PWM_REQ_GET_REQUEST_ERR_STATUS, 0, 0, 1)
        return data[0]
    
        
dummySerial = "AP"

class dummyController:
    def __init__(self, busnum, devnum):
        self.busnum = busnum
        self.devnum = devnum
        self.serial = dummySerial
        self.id = 'DUMMY[{0},{1}]'.format(self.busnum, self.devnum)
        self.version = 0x0101
        self.ee_data = [ 0xFF ] * 512
        self._reset_setup()
        self.start_timeout = 50
        self.timeout = 10
        self.bright = [ 0] * NCHANNELS
        self.flash = dict()
        self.pwm_vers = PWM_VERS_APPL
        self.pwm_flash = dict()
        self.error_count = 0
        
    def _reset_setup(self):
        self.common_bright = NCOMMONBRIGHTS - 1
        self.pwm_freq = 100
        self.max_pwm = int(16000000 / (16 * 9 * self.pwm_freq) - 1);
        self.ch_map = [ dict(channel=0, port=0, pins=0) ] * 30

    def release(self):
        print "{0}: release interface".format(self.id)
        
    def bootloader_mode(self):
        return self.serial == "BL"
    
    def read_ee_data(self, start, size):
        return self.ee_data[start: start + size]
 
    def write_ee_data(self, start, data):
        self.ee_data[start: start + len(data)] = data
        print "{0}: set ee data:".format(self.id), self.ee_data

    def stop_pwm_ctrl(self):
        self.pwm_vers = PWM_VERS_APPL
        print "{0}: stop pwm controller".format(self.id)

    def reset_pwm_ctrl(self):
        self.pwm_vers = PWM_VERS_APPL
        print "{0}: reset pwm controller".format(self.id)
        
    def start_pwm_ctrl_bootloader(self):
        self.pwm_vers = PWM_VERS_BOOT
        print "{0}: start pwm controller bootloader".format(self.id)
        
    def set_reply_timeout(self, start_timeout, timeout):
        self.start_timeout = start_timeout
        self.timeout = timeout
        print "{0}: set start_timeout {1} timeout {2}".format(self.id, start_timeout, timeout)
        
    def get_reply_error_status(self):
        return 0
    
    def start_bootloader(self):
        print "start bootloader"
        global dummySerial
        dummySerial = "BL"

    def start_appl(self):
        print "start appl"
        global dummySerial
        dummySerial = "AP"

    def get_flash_page_size(self):
        return 64

    def write_flash_page(self, addr, data):
        print "write flash page {0:04X}: {1}".format(addr, data)
        self.flash[addr] = data
        
    def read_flash(self, addr, len):
        if not addr in self.flash:
            self.flash[addr] = [ 255 ] * len
        return self.flash[addr]
    
    def get_request_error_status(self):
        return 0
    
    def set_brightness(self, start, values):
        self.bright[start: start + len(values)] = values
        print "{0}: set bright:".format(self.id), self.bright
    
    def set_brightness_synced(self, start, values):
        self.bright[start: start + len(values)] = values
        print "{0}: set bright synced:".format(self.id), self.bright
    
    def get_brightness(self, start, nch):
        return self.bright[start: start + nch]

    def get_channel_map(self, start, nch):
        return self.ch_map[start: start + nch]
                    
    def set_channel_map(self, start, map):
        self.ch_map[start: start + len(map)] = map
        print "{0}: set channel map:".format(self.id), self.ch_map
                    
    def set_common_brightness(self, value):
        self.common_bright = value
        print "{0}: set common brightness:".format(self.id), self.common_bright

    def get_common_brightness(self):
        return self.common_bright

    def get_max_pwm_value(self):
        return self.max_pwm
 
    def get_common_max_pwm_value(self):
        return NCOMMONBRIGHTS - 1
 
    def set_pwm_freq(self, value):
        self.pwm_freq = value
        self.max_pwm = int(16000000 / (16 * 9 * value) - 1);
        print "{0}: set pwm freq {1} max pwm {2}".format(self.id, self.pwm_freq, self.max_pwm)
        
    def get_pwm_freq(self):
        return self.pwm_freq
 
    def store_setup(self):
        global dummyDevices
        file = open("dummyctrls.objs", "w")
        pickle.dump(dummyDevices, file)
        file.close()
        print "{0}: store setup".format(self.id)
    
    def reset_setup(self):
        self._reset_setup()
        global dummyDevices
        file = open("dummyctrls.objs", "w")
        pickle.dump(dummyDevices, file)
        file.close()
        print "{0}: reset setup".format(self.id)
        
    def get_pwm_bootloader_mode(self):
        return self.pwm_vers == PWM_VERS_BOOT

    def get_pwm_version(self):
        return 1

    def pwm_echo_test(self, testValue):
        pass
    
    def get_bootloader_request_error_status(self):
        return 0
    
    def get_pwm_flash_page_size(self):
        return 128

    def write_pwm_flash_page(self, addr, data):
        print "write pwm flash page {0:04X}: {1}".format(addr, data)
        self.pwm_flash[addr] = data
        
    def read_pwm_flash(self, addr, len):
        if not addr in self.pwm_flash:
            self.pwm_flash[addr] = [ 255 ] * len
        return self.pwm_flash[addr]
    

dummyDevices = None
SimulatedControllers = 0

def loadDummyDevices():
    global dummyDevices
    try:
        file = open("dummyctrls.objs", "r")
        dummyDevices = pickle.load(file)
        file.close()
    except IOError:
        dummyDevices = list()

    if len(dummyDevices) > SimulatedControllers:
        dummyDevices[SimulatedControllers: len(dummyDevices)] = []
    while len(dummyDevices) < SimulatedControllers:
        dummyDevices.append(dummyController(0, len(dummyDevices) + 1))

    return dummyDevices


class ControllerConfig:

    def __init__(self, ctrl):
        self.classVersion = CONFIG_CLASS_VERSION
        self.ctrl = ctrl
        self.id = ctrl.id
        self.read()
        
    def read(self):
        self.ctrl.reset_pwm_ctrl()
        self.pwmRes = self.ctrl.get_max_pwm_value()
        self.commonPWMRes = self.ctrl.get_common_max_pwm_value()
        self.pwmFreq = self.ctrl.get_pwm_freq()
        self.commonBright = self.ctrl.get_common_brightness()
        self.configVersion = 0
        self.numAreas = [ 0 ] * NumBaseAreas()
        self.numReqChannels = 0
        self.analyzeSize = DEFAULT_ANALYZE_SIZE
        self.edgeWeighting = DEFAULT_EDGE_WEIGHTING
        self.overscan = DEFAULT_OVERSCAN
        
        eedata = self.ctrl.read_ee_data(1, 8 + len(self.numAreas) + NCHANNELS * 6)
        #print "read eedata:", eedata
        configValidId = eedata[0] + eedata[1] * 256
        if configValidId == CONFIG_VALID_ID:
            self.configVersion = eedata[2] + eedata[3] * 256
            configVersionStr = "{0:04X}".format(self.configVersion)
            p = 4
            for i in range(len(self.numAreas)):
                self.numAreas[i] = min(eedata[p], MAX_AREAS[i])
                p = p + 1
            self.numReqChannels = min(eedata[p], NCHANNELS)
            p = p + 1
            if self.configVersion > 1:
                p = p + self.numReqChannels * 6
                self.overscan = max(min(eedata[p], MAX_OVERSCAN), MIN_OVERSCAN)
                self.analyzeSize = max(min(eedata[p + 1], MAX_ANALYZE_SIZE), MIN_ANALYZE_SIZE)
                self.edgeWeighting = max(min(eedata[p + 2], MAX_EDGE_WEIGHTING), MIN_EDGE_WEIGHTING)
        else:
            configVersionStr = ""
        self.version = "USB:{0:04X} PWM:{1:04X} CONFIG:{2}".format(self.ctrl.version, self.ctrl.get_pwm_version(), configVersionStr)
        pwmChannelMap = self.ctrl.get_channel_map(0, NCHANNELS)
        #print "read pwmChannelMap", pwmChannelMap
        self.channelMap = dict()
        for portName in PORT_NAME_MAP.keys():
            foundArea = None
            port, pin = PORT_NAME_MAP[portName]
            for channelRec in pwmChannelMap:
                reqChannel = channelRec['channel']
                outPort = channelRec['port']
                outPins = channelRec['pins']
                if outPort == port and (outPins & pin):
                    if configValidId == CONFIG_VALID_ID:
                        p = 5 + len(self.numAreas)
                        for i in range(self.numReqChannels):
                            if eedata[p] == reqChannel:
                                area = AreaName(eedata[p + 1], eedata[p + 2])
                                if area:
                                    foundArea = area
                                    color = eedata[p + 1] & 0x03
                                    gamma = max(min(eedata[p + 3], MAX_GAMMA_VAL), MIN_GAMMA_VAL)
                                    whiteCal = min((eedata[p + 4] + eedata[p + 5] * 256), self.pwmRes)
                                    break
                            p = p + 6
                    break
            if foundArea:
                self.channelMap[portName] = dict(area=foundArea, color=color, gamma=gamma, whiteCal=whiteCal)
            else:
                self.channelMap[portName] = None
        #print "read channelMap:", self.channelMap
                
    def write(self):
        #print "write channelMap:", self.channelMap
        eedata = bytearray()
        eedata.append(CONFIG_VALID_ID & 0x00FF)
        eedata.append(CONFIG_VALID_ID >> 8)
        eedata.append(CONFIG_VERSION & 0x00FF)
        eedata.append(CONFIG_VERSION >> 8)
        eedata.extend(self.numAreas)
        eedata.append(0)

        reqChannelMap = dict()
        pwmChannelMap = list()
        n = 0
        for portName in self.channelMap.keys():
            port, pin = PORT_NAME_MAP[portName]
            channelRec = self.channelMap[portName]
            if channelRec:
                area = channelRec['area']
                color = channelRec['color']
                whiteCal = channelRec['whiteCal']
                if whiteCal > self.pwmRes: whiteCal = self.pwmRes
                gamma = channelRec['gamma']
                areaCode, areaNum = AreaCode(area, color)
                key = '{0}{1}{2}{3}'.format(areaCode, areaNum, gamma, whiteCal)
                if key in reqChannelMap:
                    reqChannel = reqChannelMap[key]
                else:
                    reqChannel = n
                    n = n + 1
                    reqChannelMap[key] = reqChannel
                    eedata.append(reqChannel)
                    eedata.append(areaCode)
                    eedata.append(areaNum)
                    eedata.append(gamma)
                    eedata.append(whiteCal & 0x00FF)
                    eedata.append(whiteCal >> 8)
                pwmChannelMap.append(dict(channel=reqChannel, port=port, pins=pin))

        eedata[4 + len(self.numAreas)] = n
        eedata.append(self.overscan)
        eedata.append(self.analyzeSize)
        eedata.append(self.edgeWeighting)

        self.numReqChannels = 0
        while len(pwmChannelMap) < NCHANNELS:
            pwmChannelMap.append(dict(channel=0, port=0, pins=0))

        #print "write pwmChannelMap:", pwmChannelMap
        #print "write eedata:", eedata
        self.ctrl.write_ee_data(1, eedata)
        self.ctrl.set_channel_map(0, pwmChannelMap)
        self.ctrl.store_setup()
        self.read()

    def reset(self):
        self.ctrl.write_ee_data(1, [ 0xFF, 0xFF ])
        self.ctrl.reset_setup()
        self.read()
    
    def setCommonBright(self, v):
        if self.commonBright != v:
            self.ctrl.set_common_brightness(v)
            self.commonBright = v
            
    def setPWMFreq(self, v):
        if self.pwmFreq != v:
            self.ctrl.set_pwm_freq(v)
            self.pwmRes = self.ctrl.get_max_pwm_value()
            self.pwmFreq = v


UsbContext = None
DeviceList = list()
                       
def FindDevices():
    global DeviceList, UsbContext, libusb1, usb1

    if UsbContext == None and SimulatedControllers == 0:
        try:
            import libusb1
            import usb1
            UsbContext = usb1.LibUSBContext()
        except Exception as err:
            raise DeviceError(str(err))
        
    ReleaseDevices()

    if SimulatedControllers > 0:
        DeviceList = loadDummyDevices()
        return

    for dev in UsbContext.getDeviceList():
        try:
            if dev.getVendorID() == VENDOR_ID and dev.getProductID() == PRODUCT_ID and dev.getManufacturer() == VENDOR_NAME and dev.getProduct() == DEVICE_NAME:
                serial = dev.getSerialNumber()
                handle = dev.open()
                handle.setConfiguration(1)
                handle.claimInterface(0)
                ctrl = DF10CHController(handle, dev.getBusNumber(), dev.getDeviceAddress(), dev.getbcdDevice(), serial)
                DeviceList.append(ctrl)
        except libusb1.USBError:
            pass

                    
def ReleaseDevices():
    global DeviceList
    for dev in DeviceList:
        if SimulatedControllers > 0:
            dev.release()
        else:
            try:
                dev.release()
            except libusb1.USBError:
                pass
    DeviceList = list()


ConfigMap = dict()

def LoadConfigs():
    global ConfigMap, DeviceList
    ConfigMap = dict()
    FindDevices()
    for ctrl in DeviceList:
        if not ctrl.bootloader_mode() and not ctrl.get_pwm_bootloader_mode():
            config = ControllerConfig(ctrl)
            ConfigMap[ctrl.id] = config

            
if __name__ == "__main__":
    def calc_gamma_tab(gamma, max_pwm):
        result = list();
        for i in range (256):
            v = pow (i / 255.0, gamma)
            iv = int(round(v * max_pwm))
            result.append(iv)
        return result

    FindDevices()
    if len(DeviceList):
        dev = DeviceList[0]
        
        #dev.set_reply_timeout(150, 10)
        
        if 0:
#            data = range(128, 0, -1)
#            print "write"
#            dev.write_ee_data(0, data)
            print "read"
            for i in range(50):
                eedata = dev.read_ee_data(0, 254)
                print eedata

        #print "set reply timeout"
        #dev.set_reply_timeout(950,5)

        if 1:
            import firmware
            fw = firmware.FlashMem("/home/andy/python_ws/df10ch/pwm_ctrl/10ch_pwm_ctrl.dff", 128, True)
            if dev.bootloader_mode():
                dev.start_appl()
                time.sleep(5)
            if not dev.get_pwm_bootloader_mode():
                dev.start_pwm_ctrl_bootloader()
            print dev.bootloader_mode(), dev.get_pwm_bootloader_mode()
            try:
                for i in range(50):
                    print i
                    for fp in fw.pageList:
                        #print fp.baseAddr
                        data = dev.read_pwm_flash(fp.baseAddr, fp.pageSize)
                        fp.verify(data)
            except:
                pass
            print "get request error status"
            stat = dev.get_bootloader_request_error_status()
            print GetCommErrMsg(stat)
            
        if 0:
            print 'get pwm version'
            v = dev.get_pwm_version()
            print "pwm version: ", v

        if 0:
            print 'set brighness'
            #dev.set_pwm_freq(100)
            f = dev.get_pwm_freq()
            print "freq: ", f
            m = dev.get_max_pwm_value()
            print "max pwm: ", m
            gtab = calc_gamma_tab(2.2, m)
            #while 1:
            t = time.clock()
            n = 0
            for i in range(9):
                for v in range(NBRIGHTS):
                    data = [ gtab[v] ]
                    dev.set_brightness_synced(i, data)
                    n = n + 1
                for v in range(NBRIGHTS-1,-1,-1):
                    data = [ gtab[v] ]
                    dev.set_brightness_synced(i, data)
                    n = n + 1
            t1 = time.clock()
            print "mean time ", (t1 - t) / n
            print "get request error status"
            stat = dev.get_request_error_status()
            print GetCommErrMsg(stat)
            print "get reply error status"
            stat = dev.get_reply_error_status()
            print GetCommErrMsg(stat)

        if 0:
            print 'set brighness'
            dev.set_pwm_freq(100)
            f = dev.get_pwm_freq()
            print "freq: ", f
            m = dev.get_max_pwm_value()
            print "max pwm: ", m
            gtab = calc_gamma_tab(2.2, m)
            rows = list()
            for i in range(256):
                data = list()
                for c in range(30):
                    v = i + c
                    if v >= NBRIGHTS:
                        v = v - NBRIGHTS
                    data.append(gtab[v])
                rows.append(data)
                data = list()
                for c in range(30):
                    v = NBRIGHTS - i - c - 1
                    if v < 0:
                        v = v + NBRIGHTS
                    data.append(gtab[v])
                rows.append(data)
            while 1:
                t = time.clock()
                n = 0
                for data in rows:
                    dev.set_brightness(0, data)
                    n = n + 1
                t1 = time.clock()
                print "mean time ", (t1 - t) / n
                stat = dev.get_request_error_status()
                if stat:
                    print "get request error status"
                    print GetCommErrMsg(stat)
                stat = dev.get_reply_error_status()
                if stat:
                    print "get reply error status"
                    print GetCommErrMsg(stat)

        if 0:
            print 'get channel map'
            data = dev.get_channel_map(0, NCHANNELS)
            print data
            
        if 0:
            print "common brightness test"
            data = [ 255, 255, 255, 255, 255, 255, 255, 255, 255 ]
            dev.set_brightness(0, data)
            for v in range(NBRIGHTS-1,-1,-1):
                print v
                dev.set_common_brightness(v)
                time.sleep(0.01)
            time.sleep(1)
            for v in range(NBRIGHTS):
                dev.set_common_brightness(v)
                time.sleep(0.01)

        if 0:
            print "reset setup"
            dev.reset_setup()
        
        if 0:
            print "store setup"
            dev.store_setup()
        
        if 0:
            print "get request error status"
            stat = dev.get_request_error_status()
            print GetCommErrMsg(stat)

        if 1:
            print "get reply error status"
            stat = dev.get_reply_error_status()
            print GetCommErrMsg(stat)
    else:
        print "No controller found!"
    
    

