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

class SetupDialog:
    
    def __init__(self, master, side=LEFT):
        
        self.activeSheet = None
        self.count = 0
        self.choice = IntVar(0)

        if side in (TOP, BOTTOM):
            self.side = LEFT
        else:
            self.side = TOP

        self.tabsMaster = Frame(master, borderwidth=2, relief=RIDGE)
        self.tabsMaster.pack(side=side, fill=BOTH)
        self.sheetMaster = Frame(master, borderwidth=2, relief=RIDGE)
        self.sheetMaster.pack(fill=BOTH)
        

    def addSheet(self, sheet, title):
        b = Radiobutton(self.tabsMaster, text=title, padx=5, pady=10, indicatoron=0, \
            variable=self.choice, value=self.count, \
            command=lambda: self.displaySheet(sheet))
        b.pack(fill=BOTH, side=self.side)
        if not self.activeSheet:
            sheet.pack(fill=BOTH, expand=1)
            self.activeSheet = sheet
        self.count += 1


    def displaySheet(self, sheet):
        self.activeSheet.forget()
        sheet.pack(fill=BOTH, expand=1)
        self.activeSheet = sheet
