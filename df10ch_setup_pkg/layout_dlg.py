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

import device_drv


class LayoutDialog:
    def __init__(self, areasDlg, master=None, **args):
        self.areasDlg = areasDlg
        self.numAreas = [ 0 ] * device_drv.NumBaseAreas()
        self.varNumAreas = list()
        for i in range(device_drv.NumBaseAreas()):
            self.varNumAreas.append(StringVar())

        root = Frame(master, **args)
        self.root = root

        Label(root, text="Configure RGB-Areas", font=tkFont.Font(weight="bold")).grid(row=0, column=0, columnspan=5, padx=5, pady=5)
        Label(root, text="Top").grid(row=1, column=2)
        Label(root, text="TopLeft").grid(row=1, column=0, sticky=E)
        Label(root, text="Left").grid(row=3, column=0, sticky=E)
        Label(root, text="BottomLeft").grid(row=5, column=0, sticky=E)
        Label(root, text="TopRight").grid(row=1, column=4, sticky=W)
        Label(root, text="Right").grid(row=3, column=4, sticky=W)
        Label(root, text="BottomRight").grid(row=5, column=4, sticky=W)
        Label(root, text="Bottom").grid(row=5, column=2)

        i = device_drv.AreaIndex("TopLeft")
        self.sbTopLeft = Spinbox(root, textvariable=self.varNumAreas[i], from_=0, to=device_drv.MAX_AREAS[i], width=2)
        self.sbTopLeft.grid(row=2, column=1, padx=5, pady=5)
        
        i = device_drv.AreaIndex("TopRight")
        self.sbTopRight = Spinbox(root, textvariable=self.varNumAreas[i], from_=0, to=device_drv.MAX_AREAS[i], width=2)
        self.sbTopRight.grid(row=2, column=3, padx=5, pady=5)
        
        i = device_drv.AreaIndex("BottomLeft")
        self.sbBottomLeft = Spinbox(root, textvariable=self.varNumAreas[i], from_=0, to=device_drv.MAX_AREAS[i], width=2)
        self.sbBottomLeft.grid(row=4, column=1, padx=5, pady=5)
        
        i = device_drv.AreaIndex("BottomRight")
        self.sbBottomRight = Spinbox(root, textvariable=self.varNumAreas[i], from_=0, to=device_drv.MAX_AREAS[i], width=2)
        self.sbBottomRight.grid(row=4, column=3, padx=5, pady=5)
        
        i = device_drv.AreaIndex("Center")
        self.sbCenter = Spinbox(root, textvariable=self.varNumAreas[i], from_=0, to=device_drv.MAX_AREAS[i], width=2)
        self.sbCenter.grid(row=3, column=2, padx=20, pady=20)
        
        i = device_drv.AreaIndex("Top")
        self.sbTop = Spinbox(root, textvariable=self.varNumAreas[i], from_=0, to=device_drv.MAX_AREAS[i], increment=1, width=3)
        self.sbTop.grid(row=2, column=2, padx=5, pady=5)
        
        i = device_drv.AreaIndex("Bottom")
        self.sbBottom = Spinbox(root, textvariable=self.varNumAreas[i], from_=0, to=device_drv.MAX_AREAS[i], increment=1, width=3)
        self.sbBottom.grid(row=4, column=2, padx=5, pady=5)
        
        i = device_drv.AreaIndex("Left")
        self.sbLeft = Spinbox(root, textvariable=self.varNumAreas[i], from_=0, to=device_drv.MAX_AREAS[i], increment=1, width=3)
        self.sbLeft.grid(row=3, column=1, padx=5, pady=5)
        
        i = device_drv.AreaIndex("Right")
        self.sbRight = Spinbox(root, textvariable=self.varNumAreas[i], from_=0, to=device_drv.MAX_AREAS[i], increment=1, width=3)
        self.sbRight.grid(row=3, column=3, padx=5, pady=5)
        
        self.btApply = Button(root, text="Apply", command=self.cbApply)
        self.btApply.grid(row=6, column=4, padx=20, pady=20, ipadx=5)

    def cbApply(self):
        for i in range(device_drv.NumBaseAreas()):
            self.numAreas[i] = int(self.varNumAreas[i].get())
        self.areasDlg.configAreas(self.numAreas)

    def setLayoutFromConfig(self):
        for i in range(device_drv.NumBaseAreas()):
            self.numAreas[i] = 0
        for ctrlId in device_drv.ConfigMap.keys():
            config = device_drv.ConfigMap[ctrlId]
            for i in range(device_drv.NumBaseAreas()):
                if config.numAreas[i] > self.numAreas[i]:
                    self.numAreas[i] = config.numAreas[i]
        for i in range(device_drv.NumBaseAreas()):
            self.varNumAreas[i].set(self.numAreas[i])
        self.areasDlg.configAreas(self.numAreas)

    def setConfigFromLayout(self):
        for ctrlId in device_drv.ConfigMap.keys():
            config = device_drv.ConfigMap[ctrlId]
            for i in range(device_drv.NumBaseAreas()):
                config.numAreas[i] = self.numAreas[i]

