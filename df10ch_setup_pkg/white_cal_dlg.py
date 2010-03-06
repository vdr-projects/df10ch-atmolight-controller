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


class WhiteCalDialog:
    def __init__(self, areasDlg, master=None, **args):
        self.areasMap = None
        self.selectedArea = None
        
        self.areasDlg = areasDlg
        areasDlg.selectCallbacks.append(self)

        root = Frame(master, **args)
        self.root = root
        root.bind("<Map>", self.cbSheetSelected)

        Label(root, text="White Calibration", font=tkFont.Font(weight="bold")).grid(row=0, column=0, columnspan=5, padx=5, pady=5)
        Label(root, text="Max. value:").grid(row=1, column=0, sticky=E)
        Label(root, text="Gamma value:").grid(row=2, column=0, sticky=E)


        self.varWhiteCal = DoubleVar(), DoubleVar(), DoubleVar()
        self.scRed = Scale(root, label="Red", bg="red", length=200, from_=1.0, to=0.0, resolution=0.01, orient=VERTICAL, variable=self.varWhiteCal[device_drv.ColorIndex("red")], command=self.cbSetWhiteCal)
        self.scRed.grid(row=1, column=1, rowspan=1, padx=5, pady=5)
        self.scGreen = Scale(root, label="Green", bg="green", length=200, from_=1.0, to=0.0, resolution=0.01, orient=VERTICAL, variable=self.varWhiteCal[device_drv.ColorIndex("green")], command=self.cbSetWhiteCal)
        self.scGreen.grid(row=1, column=2, rowspan=1, padx=5, pady=5)
        self.scBlue = Scale(root, label="Blue", bg="blue", length=200, from_=1.0, to=0.0, resolution=0.01, orient=VERTICAL, variable=self.varWhiteCal[device_drv.ColorIndex("blue")], command=self.cbSetWhiteCal)
        self.scBlue.grid(row=1, column=3, rowspan=1, padx=5, pady=5)

        self.varGamma = StringVar(), StringVar(), StringVar()
        self.sbRed = Spinbox(root, textvariable=self.varGamma[device_drv.ColorIndex("red")], from_=device_drv.MIN_GAMMA_VAL/10.0, to=device_drv.MAX_GAMMA_VAL/10.0, format='%2.1f', increment=0.1, width=2, command=self.cbSetGamma)
        self.sbRed.grid(row=2, column=1, padx=5, pady=5, sticky=W+E)
        self.sbGreen = Spinbox(root, textvariable=self.varGamma[device_drv.ColorIndex("green")], from_=device_drv.MIN_GAMMA_VAL/10.0, to=device_drv.MAX_GAMMA_VAL/10.0, format='%2.1f', increment=0.1, width=2, command=self.cbSetGamma)
        self.sbGreen.grid(row=2, column=2, padx=5, pady=5, sticky=W+E)
        self.sbBlue = Spinbox(root, textvariable=self.varGamma[device_drv.ColorIndex("blue")], from_=device_drv.MIN_GAMMA_VAL/10.0, to=device_drv.MAX_GAMMA_VAL/10.0, format='%2.1f', increment=0.1, width=2, command=self.cbSetGamma)
        self.sbBlue.grid(row=2, column=3, padx=5, pady=5, sticky=W+E)

        self.varBright = DoubleVar()
        self.scBright = Scale(root, label="Brightness", length=200, from_=1.00, to=0.0, resolution=0.01, orient=VERTICAL, variable=self.varBright, command=self.cbSetBright)
        self.scBright.grid(row=1, column=4, rowspan=1, padx=20, pady=5)
        self.varBright.set(1.0)

        self.varSelectAll = IntVar()
        self.btSelectAll = Checkbutton(root, text="Select All", command=self.cbSelectAll, variable=self.varSelectAll)
        self.btSelectAll.grid(row=2, column=4, padx=20, pady=20, ipadx=5, sticky=W+E)


    def cbSelectAll(self):
        self.setBright()

    def cbSheetSelected(self, event):
        self.loadValues()

    def cbSetWhiteCal(self, val):
        self.update()
        
    def cbSetGamma(self):
        self.update()
        
    def cbSetBright(self, val):
        self.setBright()
        
    def cbAreaSelected(self):
        if self.root.winfo_ismapped():
            self.selectArea(self.areasDlg.selectedArea)

    def loadValues(self):
        self.areasMap = dict()
        area = None
        for ctrlId in device_drv.ConfigMap.keys():
            config = device_drv.ConfigMap[ctrlId]
            pwmChannelMap = list()
            brightList = list()
            reqChannel = 0
            for portName in config.channelMap.keys():
                configMapRec = config.channelMap[portName]
                if configMapRec:
                    port, pin = device_drv.PORT_NAME_MAP[portName]
                    pwmChannelMap.append(dict(channel=reqChannel, port=port, pins=pin))
                    area = configMapRec['area']
                    gamma = configMapRec['gamma'] / 10.0
                    whiteCal = configMapRec['whiteCal']
                    bright = int(round(pow(self.varBright.get(), gamma) * whiteCal))
                    brightList.append(bright)
                    cRec = dict(ctrlId=ctrlId, portName=portName, configMapRec=configMapRec, reqChannel=reqChannel)
                    if not area in self.areasMap: self.areasMap[area] = list()
                    self.areasMap[area].append(cRec)
                    reqChannel = reqChannel + 1

            while reqChannel < device_drv.NCHANNELS:
                brightList.append(0)
                pwmChannelMap.append(dict(channel=0, port=0, pins=0))
                reqChannel = reqChannel + 1
                
            try:
                config.ctrl.set_channel_map(0, pwmChannelMap)
                config.ctrl.set_brightness(0, brightList)
            except device_drv.AtmoControllerError as err:
                tkMessageBox.showerror(self.root.winfo_toplevel().title(), err.__str__())
                return

        self.areasDlg.hideEdgeWeighting()
        if area:
            self.selectArea(area)
        self.setBright()
        
    def setBright(self):
        self.areasDlg.initAreas("#{0:02X}{0:02X}{0:02X}".format(int(round(self.varBright.get() * 255.0))))
        if not self.varSelectAll.get() and self.selectedArea:
            self.areasDlg.selectArea(self.selectedArea)
        self.update()
    
    def selectArea(self, area):
        if area in self.areasMap:
            self.varSelectAll.set(0)
            self.selectedArea = area
            self.areasDlg.selectArea(area)
            for cRec in self.areasMap[area]:
                ctrlId = cRec['ctrlId']
                config = device_drv.ConfigMap[ctrlId]
                configMapRec = cRec['configMapRec']
                color = configMapRec['color']
                whiteCal = float(configMapRec['whiteCal']) / float(config.pwmRes)
                gamma = float(configMapRec['gamma']) / 10.0
                self.varGamma[color].set(gamma)
                self.varWhiteCal[color].set(whiteCal)

    def update(self):
        for area in self.areasMap.keys():
            for cRec in self.areasMap[area]:
                ctrlId = cRec['ctrlId']
                reqChannel = cRec['reqChannel']
                configMapRec = cRec['configMapRec']
                color = configMapRec['color']
                config = device_drv.ConfigMap[ctrlId]
                if self.varSelectAll.get() or self.selectedArea == area:
                    gamma = float(self.varGamma[color].get())
                    whiteCal = int(self.varWhiteCal[color].get() * config.pwmRes)
                    configMapRec['gamma'] = int(gamma * 10.0)
                    configMapRec['whiteCal'] = whiteCal
                else:
                    gamma = float(configMapRec['gamma']) / 10.0
                    whiteCal = configMapRec['whiteCal']
                bright = int(round(pow(self.varBright.get(), gamma) * whiteCal))
                try:
                    config.ctrl.set_brightness(reqChannel, [ bright ])
                except device_drv.AtmoControllerError as err:
                    tkMessageBox.showerror(self.root.winfo_toplevel().title(), err.__str__())
                    return
