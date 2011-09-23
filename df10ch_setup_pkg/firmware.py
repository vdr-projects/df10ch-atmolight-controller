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

import fileinput
import string

class FirmwareFlashError(Exception):
    def __init__(self, msg = None):
        self.message = msg

    def __str__(self):
        return self.message


class FlashPage:
    
    def __init__(self, addr, pageSize):
        self.pageSize = pageSize
        self.baseAddr = addr - addr % pageSize
        self.data = bytearray([ 0xFF ] * pageSize)

    def insert(self, addr, value):
        self.data[addr % self.pageSize] = value

    def verify(self, data):
        for i in range(self.pageSize):
            if data[i] != self.data[i]:
                raise FirmwareFlashError("verify of flash data against firmware fails at {0:04X}: {1:02X} <> {2:02X}".format(self.baseAddr + i, data[i], self.data[i]))

    def __str__(self):
        s = "{0:04X}: ".format(self.baseAddr)
        for v in self.data:
            s = s + "{0:02X} ".format(v)
        return s


class FlashMem:
    
    def __init__(self, fileName, pageSize, targetInfoMustExist = False):
        self.pageSize = pageSize
        self.pageList = list()
        self.lastLookupPage = None
        self.target = None
        self.version = None
        self.loadFromHexFile(fileName)
        if targetInfoMustExist and (not self.target or not self.version):
            raise FirmwareFlashError("no target and/or version information found!")
        
    def getPageForAddr(self, addr):
        baseAddr = addr - addr % self.pageSize
        if self.lastLookupPage and self.lastLookupPage.baseAddr == baseAddr:
            return self.lastLookupPage;
        for p in self.pageList:
            if p.baseAddr == baseAddr:
                self.lastLookupPage = p
                return p
        return None
    
    def insert(self, addr, value):
        p = self.getPageForAddr(addr)
        if not p:
            p = FlashPage(addr, self.pageSize)
            self.pageList.append(p)
        p.insert(addr, value)

    def loadFromHexFile(self, fileName):
        file = None
        try:
            file = fileinput.FileInput(fileName)
            for line in file:
                line = string.rstrip(line)
                lineLen = len(line)
                if not lineLen:
                    continue
                lineType = line[0:1]
                if lineType == "#":
                    continue
                if lineType == "@":
                    try:
                        self.target, self.version = string.split(line[1:])
                    except:
                        raise FirmwareFlashError()
                    continue
                if lineLen < 9 or lineType != ":":
                    raise FirmwareFlashError()
                try:
                    n = int(line[1:3], 16)
                    addr = int(line[3:7], 16)
                    type = int(line[7:9], 16)
                except:
                    raise FirmwareFlashError()
                if type != 0:
                    break
                if n > 0:
                    if lineLen < (9 + 2 * n):
                        raise FirmwareFlashError()
                    for i in range(n):
                        try:
                            data = int(line[i * 2 + 9: i * 2 + 11], 16)
                        except:
                            raise FirmwareFlashError()
                        self.insert(addr + i, data)
        except IOError as err:
            raise FirmwareFlashError("could not read firmware file '{0}': {1}".format(fileName, err.__str__()))
        except FirmwareFlashError:
            raise FirmwareFlashError("could not read firmware file '{0}': syntax error at line {1}".format(fileName, file.lineno()))
        finally:
            if file:
                file.close()

if __name__ == "__main__":
    m = FlashMem("10ch_usb_ctrl.hex", 16)
    print "target:", m.target, "version:", m.version
    for p in m.pageList:
        print p