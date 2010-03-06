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

from Tkinter import *
import tkFont
import tkMessageBox
import device_drv


class BrightDialog:
    def __init__(self, areasDlg, master=None, **args):
        self.areasDlg = areasDlg
        
        root = Frame(master, **args)
        self.root = root
        root.bind("<Map>", self.cbSheetSelected)

        Label(root, text="Common Brightness Calibration", font=tkFont.Font(weight="bold")).grid(row=0, column=0, columnspan=5, padx=5, pady=5)

        self.varBright = DoubleVar()
        self.scBright = Scale(root, label="Brightness", length=200, from_=0, to=1.0, resolution=0.01, orient=HORIZONTAL, variable=self.varBright, command=self.cbSetBright)
        self.scBright.grid(row=1, column=0, rowspan=1, padx=20, pady=5)
        self.varBright.set(0.0)

    def cbSheetSelected(self, event):
        self.loadValues()

    def cbSetBright(self, val):
        self.setBright()
        
    def loadValues(self):
        for ctrlId in device_drv.ConfigMap.keys():
            config = device_drv.ConfigMap[ctrlId]
            pwmChannelMap = list()
            for portName in config.channelMap.keys():
                configMapRec = config.channelMap[portName]
                if configMapRec:
                    port, pin = device_drv.PORT_NAME_MAP[portName]
                    pwmChannelMap.append(dict(channel=0, port=port, pins=pin))

            bright = float(config.commonBright) / float(config.commonPWMRes)
            self.varBright.set(bright)

            while len(pwmChannelMap) < device_drv.NCHANNELS:
                pwmChannelMap.append(dict(channel=0, port=0, pins=0))
                
            try:
                config.ctrl.set_channel_map(0, pwmChannelMap)
                config.ctrl.set_brightness(0, [ config.pwmRes ] + [ 0 ] * (device_drv.NCHANNELS - 1))
            except device_drv.AtmoControllerError as err:
                tkMessageBox.showerror(self.root.winfo_toplevel().title(), err.__str__())
                return

        self.areasDlg.hideEdgeWeighting()
        self.areasDlg.initAreas("black")
        self.setBright()
        
    def setBright(self):
        try:
            for ctrlId in device_drv.ConfigMap.keys():
                config = device_drv.ConfigMap[ctrlId]
                config.setCommonBright(int(round(self.varBright.get() * config.commonPWMRes)))
        except device_drv.AtmoControllerError as err:
            tkMessageBox.showerror(self.root.winfo_toplevel().title(), err.__str__())
                
