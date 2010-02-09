#!/usr/bin/python
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
# DF10CH setup program main script
#

import os
from optparse import OptionParser
from Tkinter import *

from df10ch_setup_pkg.setup_dlg import SetupDialog
from df10ch_setup_pkg.areas_dlg import AreasDialog
from df10ch_setup_pkg.layout_dlg import LayoutDialog
from df10ch_setup_pkg.device_dlg import DeviceDialog
from df10ch_setup_pkg.map_dlg import ChannelMapDialog
from df10ch_setup_pkg.white_cal_dlg import WhiteCalDialog
from df10ch_setup_pkg.bright_dlg import BrightDialog
import df10ch_setup_pkg.device_drv

TITLE = "DF10CH Setup V1"
print 
parser = OptionParser(version=TITLE)
parser.add_option("-s", "--simulate", action="store", type="int", dest="simulate", default=0, help="Set simulated number of DF10CH controller's")
parser.add_option("-d", "--debug", action="store", type="int", dest="debug", default=0, help="Set debug level")
(options, args) = parser.parse_args()

df10ch_setup_pkg.device_drv.SimulatedControllers = options.simulate

root = Tk()
root.title(TITLE)

width = root.winfo_screenwidth()
height = root.winfo_screenheight()
fullscreen = 1
if options.debug >= 1:
    width=1280
    height=720
    fullscreen = 0
#root.overrideredirect(1)
#root.geometry("%dx%d+0+0" % (width, height))

top = Toplevel()
if os.name == "nt":
    top.wm_attributes("-fullscreen", fullscreen, "-topmost", 0)
    root.wm_attributes("-topmost", 1)
else:
    top.wm_attributes("-fullscreen", fullscreen)
    root.transient(top)

areasDlg = AreasDialog(top, width=width, height=height, bd=0, bg="black")
areasDlg.root.grid(row=0, column=0)

setupDlg = SetupDialog(root)
layoutDlg = LayoutDialog(areasDlg, setupDlg.sheetMaster)
mapDlg = ChannelMapDialog(areasDlg, setupDlg.sheetMaster)
whiteCalDlg = WhiteCalDialog(areasDlg, setupDlg.sheetMaster)
deviceDlg = DeviceDialog(layoutDlg, setupDlg.sheetMaster)
brightDlg = BrightDialog(areasDlg, setupDlg.sheetMaster)

setupDlg.addSheet(deviceDlg.root, "Devices")
setupDlg.addSheet(layoutDlg.root, "RGB-Areas")
setupDlg.addSheet(mapDlg.root, "Mapping")
setupDlg.addSheet(whiteCalDlg.root, "White Calibration")
setupDlg.addSheet(brightDlg.root, "Common Brightness")

root.protocol("WM_DELETE_WINDOW", lambda: deviceDlg.storeAndQuit(root))

root.update_idletasks()
if deviceDlg.scanDevices():
    root.mainloop()
