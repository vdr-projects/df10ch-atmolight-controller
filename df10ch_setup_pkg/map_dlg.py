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
import string

class ChannelMapDialog:
    def __init__(self, areasDlg, master=None, **args):
        self.areasDlg = areasDlg
        areasDlg.selectCallbacks.append(self)

        self.actualIdx = None
        self.actualCtrlId = None
        self.actualPortName = None
        self.actualArea = None
        self.actualColor = None
        self.channelList = None
        
        root = Frame(master, **args)
        self.root = root
        root.bind("<Map>", self.cbSheetSelected)

        Label(root, text="Channel Mapping", font=tkFont.Font(weight="bold")).grid(row=0, column=0, columnspan=4, padx=5, pady=5)

        self.yScroll = Scrollbar (root, orient=VERTICAL)
        self.yScroll.grid(row=1, column=1, rowspan=4, sticky=N+S)
        self.lbChannels = Listbox(root, selectmode=SINGLE, activestyle=NONE, width=35, height=30, yscrollcommand=self.yScroll.set)
        self.lbChannels.grid(row=1, column=0, rowspan=4, padx=5, pady=5, sticky=N+S+W+E)
        self.lbChannels.bind("<ButtonRelease-1>", self.cbSelectChannel)
        self.yScroll["command"] = self.lbChannels.yview

        frSingleColor = Frame(root, borderwidth=5, relief=RIDGE, padx=0, pady=0)
        frSingleColor.grid(row=2, column = 2, columnspan = 2, padx=5, pady=5, sticky=W+E)

        Label(frSingleColor, text="Set color for channel:").grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky="W")

        self.btRed = Button(frSingleColor, text="Red", bg="red", command=lambda: self.cbSetColor("red"))
        self.btRed.grid(row=1, column=0, padx=5, pady=5, ipadx=5, sticky=W+E)

        self.btGreen = Button(frSingleColor, text="Green", bg="green", command=lambda: self.cbSetColor("green"))
        self.btGreen.grid(row=1, column=1, padx=5, pady=5, ipadx = 5, sticky=W+E)

        self.btBlue = Button(frSingleColor, text="Blue", bg="blue", command=lambda: self.cbSetColor("blue"))
        self.btBlue.grid(row=1, column=2, padx=5, pady=5, ipadx = 5, sticky=W+E)

        frGroupColor = Frame(root, borderwidth=5, relief=RIDGE, padx=0, pady=0)
        frGroupColor.grid(row = 3, column = 2, columnspan = 2, padx=5, pady=5, sticky=W+E)

        Label(frGroupColor, text="Set color for channel group:").grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky="W")

        self.btRGB = Button(frGroupColor, text="RGB", command=lambda: self.cbSetGroupColor("red", "green", "blue"))
        self.btRGB.grid(row=1, column=0, padx=5, pady=5, ipadx = 5, sticky=W+E)

        self.btRBG = Button(frGroupColor, text="RBG", command=lambda: self.cbSetGroupColor("red", "blue", "green"))
        self.btRBG.grid(row=1, column=1, padx=5, pady=5, ipadx = 5, sticky=W+E)

        self.btBRG = Button(frGroupColor, text="GRB", command=lambda: self.cbSetGroupColor("green", "red", "blue"))
        self.btBRG.grid(row=1, column=2, padx=5, pady=5, ipadx = 5, sticky=W+E)

        self.btGRB = Button(frGroupColor, text="BRG", command=lambda: self.cbSetGroupColor("blue", "red", "green"))
        self.btGRB.grid(row=2, column=0, padx=5, pady=5, ipadx = 5, sticky=W+E)

        self.btBGR = Button(frGroupColor, text="GBR", command=lambda: self.cbSetGroupColor("green", "blue", "red"))
        self.btBGR.grid(row=2, column=1, padx=5, pady=5, ipadx = 5, sticky=W+E)

        self.btGBR = Button(frGroupColor, text="BGR", command=lambda: self.cbSetGroupColor("blue", "green", "red"))
        self.btGBR.grid(row=2, column=2, padx=5, pady=5, ipadx = 5, sticky=W)

        #frNavi = Frame(root, padx=0, pady=0)
        #frNavi.grid(row = 1, column = 2, columnspan = 2, padx=5, pady=5, sticky=N+S+W+E)

        self.btNext = Button(root, text="Next Ch", command=self.cbNext)
        self.btNext.grid(row=1, column=2, padx=5, pady=5, ipadx=5, sticky=W+E)

        self.btPrev = Button(root, text="Prev Ch", command=self.cbPrev)
        self.btPrev.grid(row=1, column=3, padx=5, pady=5, ipadx=5, sticky=W+E)

        self.btDelete = Button(root, text="Delete mapping", command=self.cbDelete)
        self.btDelete.grid(row=4, column=2, columnspan=2, padx=5, pady=5, ipadx = 5, sticky=W+E)


    def cbSelectChannel(self, event):
        s = self.lbChannels.curselection()
        if len(s) == 1:
            self.selectChannel(int(s[0]))

    def cbAreaSelected(self):
        if self.root.winfo_ismapped() and self.actualIdx != None:
            self.selectArea(self.areasDlg.selectedArea, self.actualColor)
            self.storeActual()
    
    def cbSetGroupColor(self, *colors):
        actIdx = self.actualIdx
        if actIdx != None:
            port, p = string.split(self.actualPortName, ".")
            for pinNum in range(3):
                portName = "{0}.{1}".format(port, pinNum + 1)
                for i, mapRec in enumerate(self.channelList):
                    if mapRec['ctrlId'] == self.actualCtrlId and mapRec['portName'] == portName:
                        self.actualPortName = portName
                        self.actualColor = colors[pinNum]
                        self.actualIdx = i
                        self.storeActual()
                        break
            self.selectChannel(actIdx)
    
    def cbSetColor(self, color):
        if self.actualIdx != None:
            self.selectArea(self.actualArea, color)
            self.storeActual()
    
    def cbDelete(self):
        if self.actualIdx != None:
            self.storeActual(True)
    
    def cbNext(self):
        if self.actualIdx != None:
            i = self.actualIdx + 1
            if i == len(self.channelList):
                i = 0
            self.selectChannel(i)

    def cbPrev(self):
        if self.actualIdx != None:
            i = self.actualIdx - 1
            if i < 0:
                i = len(self.channelList) - 1
            self.selectChannel(i)

    def cbSheetSelected(self, event):
        self.loadValues()

    def storeActual(self, delete=False):
        config = device_drv.ConfigMap[self.actualCtrlId]
        if delete:
            config.channelMap[self.actualPortName] = None
            self.channelList[self.actualIdx] = dict(ctrlId=self.actualCtrlId, portName=self.actualPortName, area=None, color=None)
        else:
            self.channelList[self.actualIdx] = dict(ctrlId=self.actualCtrlId, portName=self.actualPortName, area=self.actualArea, color=self.actualColor)
 
        if not delete and self.actualArea and self.actualColor:
            configMapRec = config.channelMap[self.actualPortName]
            if configMapRec:
                configMapRec['area'] = self.actualArea
                configMapRec['color'] = device_drv.ColorIndex(self.actualColor)
            else:
                configMapRec = dict(area=self.actualArea, color=device_drv.ColorIndex(self.actualColor), gamma=device_drv.DEFAULT_GAMMA_VAL, whiteCal=config.pwmRes)
            config.channelMap[self.actualPortName] = configMapRec
            text = "{0}: {1} -> {2}: {3}".format(self.actualCtrlId, self.actualPortName, self.actualArea, self.actualColor)
        else:
            text = "{0}: {1}".format(self.actualCtrlId, self.actualPortName)

        self.lbChannels.delete(self.actualIdx, self.actualIdx)
        self.lbChannels.insert(self.actualIdx, text)
        self.lbChannels.selection_set(self.actualIdx)
        
    def loadValues(self):
        self.actualIdx = None
        self.channelList = list()
        self.lbChannels.delete(0, END)
        for ctrlId in sorted(device_drv.ConfigMap.keys()):
            config = device_drv.ConfigMap[ctrlId]
            for portName in sorted(config.channelMap.keys()):
                configMapRec = config.channelMap[portName]
                if configMapRec:
                    area = configMapRec['area']
                    color = device_drv.ColorName(configMapRec['color'])
                    text = "{0}: {1} -> {2}: {3}".format(ctrlId, portName, area, color)
                else:
                    area = None
                    color = None
                    text = "{0}: {1}".format(ctrlId, portName)
                self.channelList.append(dict(ctrlId=ctrlId, portName=portName, area=area, color=color))
                self.lbChannels.insert(END, text)

            pwmChannelMap = list()
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
        self.actualCtrlId = None
        self.actualPortName = None
        if len(self.channelList):
            self.selectChannel(0)

    def selectChannel(self, i):
        self.actualIdx = i
        
        self.lbChannels.selection_clear(0, END)
        self.lbChannels.selection_set(i)
        self.lbChannels.see(i)

        mapRec = self.channelList[i]
        self.selectLight(mapRec['ctrlId'], mapRec['portName'])
        self.selectArea(mapRec['area'], mapRec['color'])
        
    def selectLight(self, ctrlId, portName):
        if ctrlId != self.actualCtrlId or portName != self.actualPortName:
            if self.actualCtrlId and ctrlId != self.actualCtrlId:
                config = device_drv.ConfigMap[self.actualCtrlId]
                try:
                    config.ctrl.set_channel_map(0, [ dict(channel=0, port=0, pins=0) ])
                except device_drv.AtmoControllerError as err:
                    tkMessageBox.showerror(self.root.winfo_toplevel().title(), err.__str__())
                    return

            port, pin = device_drv.PORT_NAME_MAP[portName]
            config = device_drv.ConfigMap[ctrlId]
            try:
                config.ctrl.set_channel_map(0, [ dict(channel=0, port=port, pins=pin) ])
            except device_drv.AtmoControllerError as err:
                tkMessageBox.showerror(self.root.winfo_toplevel().title(), err.__str__())
                return

            self.actualCtrlId = ctrlId
            self.actualPortName = portName
        
    def selectArea(self, area, color):
        if self.actualArea:
            self.areasDlg.setAreaColor(self.actualArea, "black")
        self.actualColor = color
        if area:
            self.actualArea = area
            if not color:
                color = "black"
            self.areasDlg.setAreaColor(area, color)
            self.areasDlg.selectArea(area)
