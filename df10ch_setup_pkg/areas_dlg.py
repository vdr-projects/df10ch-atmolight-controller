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
import device_drv

class AreasDialog:
    def __init__(self, master=None, **args):
        self.root = Canvas(master, **args)
        self.selectedArea = None
        self.selectCallbacks = list()
        
    def configAreas(self, numAreas):
        nTopLeft = numAreas[device_drv.AreaIndex("TopLeft")]
        nTopRight = numAreas[device_drv.AreaIndex("TopRight")]
        nBottomLeft = numAreas[device_drv.AreaIndex("BottomLeft")]
        nBottomRight = numAreas[device_drv.AreaIndex("BottomRight")]
        nCenter = numAreas[device_drv.AreaIndex("Center")]
        nTop = numAreas[device_drv.AreaIndex("Top")]
        nBottom = numAreas[device_drv.AreaIndex("Bottom")]
        nLeft = numAreas[device_drv.AreaIndex("Left")]
        nRight = numAreas[device_drv.AreaIndex("Right")]

        cv = self.root
        size = 0
        width = int(cv["width"])
        height = int(cv["height"])
        
        sTop = nTop + nTopLeft + nTopRight
        if sTop:
            topSize = int(width / sTop)
            topSizeEnd = width - topSize * (sTop - 1)
            if not size or topSize < size:
                size = topSize
            
        sBottom = nBottom + nBottomLeft + nBottomRight
        if sBottom:
            bottomSize = int(width / sBottom)
            bottomSizeEnd = width - bottomSize * (sBottom - 1)
            if not size or bottomSize < size:
                size = bottomSize
        
        sLeft = nLeft + nTopLeft + nBottomLeft
        if sLeft:
            leftSize = int(height / sLeft)
            leftSizeEnd = height - leftSize * (sLeft - 1)
            if not size or leftSize < size:
                size = leftSize

        sRight = nRight + nTopRight + nBottomRight
        if sRight:
            rightSize = int(height / sRight)
            rightSizeEnd = height - rightSize * (sRight - 1)
            if not size or rightSize < size:
                size = rightSize

        if not size or int(width / 2) < size:
            size = int(width / 2)
        if not size or int(height / 2) < size:
            size = int(height / 2)
            
        pTop = [ None ] * nTop
        x = 0
        
            # top left corner
        if nTopLeft:
            pTopLeft = [ 0, 0, topSize, 0, topSize, size, size, size, size, leftSize, 0, leftSize ]
            x = topSize
        elif nTop == 1:
            pTop[0] = [ 0, 0, width, 0, width - size, size, size, size ]
        elif nTop > 1:
            pTop[0] = [ 0, 0, topSize, 0, topSize, size, size, size ]

            # top right corner
        if nTopRight:
            pTopRight = [ width, 0, width, rightSize, width - size, rightSize, width - size, size, width - topSizeEnd, size, width - topSizeEnd, 0 ]
        elif nTop > 1:
            pTop[nTop - 1] = [ width, 0, width - size, size, width - topSizeEnd, size, width - topSizeEnd, 0 ]

            # top
        for i in range(nTop):
            if pTop[i] == None:
                pTop[i] = [ x, 0, x + topSize, 0, x + topSize, size, x, size ]
            x = x + topSize

        pBottom = [ None ] * nBottom
        x = 0
        
            # bottom left corner
        if nBottomLeft:
            pBottomLeft = [ 0, height, 0, height - leftSizeEnd, size, height - leftSizeEnd, size, height - size, bottomSize, height - size, bottomSize, height ]
            x = bottomSize
        elif nBottom == 1:
            pBottom[0] = [ 0, height, size, height - size, width - size, height - size, width, height ]
        elif nBottom > 1:
            pBottom[0] = [ 0, height, size, height - size, bottomSize, height - size, bottomSize, height ]

            # bottom right corner
        if nBottomRight:
            pBottomRight = [ width, height, width - bottomSizeEnd, height, width - bottomSizeEnd, height - size, width - size, height - size, width - size, height - rightSizeEnd, width, height - rightSizeEnd ]
        elif nBottom > 1:
            pBottom[nBottom - 1] = [ width, height, width - bottomSizeEnd, height, width - bottomSizeEnd, height - size, width - size, height - size ]

            # bottom
        for i in range(nBottom):
            if pBottom[i] == None:
                pBottom[i] = [ x, height, x, height - size, x + bottomSize, height - size, x + bottomSize, height ]
            x = x + bottomSize

        pLeft = [ None ] * nLeft
        y = 0

            # left top corner
        if nTopLeft:
            y = leftSize
        elif nLeft == 1:
            pLeft[0] = [ 0, 0, size, size, size, height - size, 0, height ]
        elif nLeft > 1:
            pLeft[0] = [ 0, 0, size, size, size, leftSize, 0, leftSize ]

            # left bottom corner
        if not nBottomLeft and nLeft > 1:
            pLeft[nLeft - 1] = [ 0, height, 0, height - leftSizeEnd, size, height - leftSizeEnd, size, height - size ]

            # left
        for i in range(nLeft):    
            if pLeft[i] == None:
                pLeft[i] = [ 0, y, size, y, size, y + leftSize, 0, y + leftSize ]
            y = y + leftSize
            
        pRight = [ None ] * nRight
        y = 0

            # right top corner
        if nTopRight:
            y = rightSize
        elif nRight == 1:
            pRight[0] = [ width, 0, width, height, width - size, height - size, width - size, size ]
        elif nRight > 1:
            pRight[0] = [ width, 0, width, rightSize, width - size, rightSize, width - size, size ]

            # right bottom corner
        if not nBottomRight and nRight > 1:
            pRight[nRight - 1] = [ width, height, width - size, height - size, width - size, height - rightSizeEnd, width, height - rightSizeEnd ]

            # right
        for i in range(nRight):    
            if pRight[i] == None:
                pRight[i] = [ width, y, width, y + rightSize, width - size, y + rightSize, width - size, y ]
            y = y + rightSize

            # center
        if nCenter:
            pCenter = [ size, size, width - size, size, width - size, height - size, size, height - size ]

            # Build canvas items
        cv.delete(ALL)
        
        if nTopLeft:
            cv.create_polygon(pTopLeft, tags="TopLeft")
        if nTopRight:
            cv.create_polygon(pTopRight, tags="TopRight")
        if nBottomLeft:
            cv.create_polygon(pBottomLeft, tags="BottomLeft")
        if nBottomRight:
            cv.create_polygon(pBottomRight, tags="BottomRight")
        if nCenter:
            cv.create_polygon(pCenter, tags="Center")
        
        for i in range(nTop):
            cv.create_polygon(pTop[i], tags="Top-{0}".format(i + 1))
        for i in range(nBottom):
            cv.create_polygon(pBottom[i], tags="Bottom-{0}".format(i + 1))
        for i in range(nLeft):
            cv.create_polygon(pLeft[i], tags="Left-{0}".format(i + 1))
        for i in range(nRight):
            cv.create_polygon(pRight[i], tags="Right-{0}".format(i + 1))
            
        for id in cv.find_all():
            cv.itemconfigure(id, outline="#808080", width=3)
            cv.tag_bind(id, "<Button-1>", self.cbSelectArea)

    def initAreas(self, color):
        self.root.configure(background=color)
        for id in self.root.find_all():
            self.root.itemconfigure(id, fill=color, outline="#808080")
        self.selectedArea = None
        
    def setAreaColor(self, area, color):
        self.root.itemconfigure(area, fill=color)

    def selectArea(self, area):
        if self.selectedArea != area:
            cv = self.root
            if self.selectedArea:
                cv.itemconfigure(self.selectedArea, outline="#808080")
            idList = cv.find_withtag(area)
            if len(idList):
                id = idList[0]
                cv.tag_raise(id)
                cv.itemconfigure(id, outline="yellow")
                self.selectedArea = area

    def cbSelectArea(self, event):
        cv = self.root
        idList = cv.find_closest(cv.canvasx(event.x), cv.canvasx(event.y))
        if len(idList):
            id = idList[0]
            if self.selectedArea:
                cv.itemconfigure(self.selectedArea, outline="#808080")
            self.selectedArea = cv.gettags(id)[0]
            cv.tag_raise(id)
            cv.itemconfigure(id, outline="yellow")

        for cb in self.selectCallbacks:
            cb.cbAreaSelected()
