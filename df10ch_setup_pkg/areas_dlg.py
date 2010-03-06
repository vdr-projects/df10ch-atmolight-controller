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
import Image
import ImageTk
import ImageDraw
import device_drv

class AreasDialog:
    def __init__(self, master=None, **args):
        self.width = args["width"]
        self.height = args["height"]
        self.parent = master
        self.root = Canvas(master, **args)
        self.selectedArea = None
        self.selectCallbacks = list()
        self.edgeWeighting = -1

    def cvX(self, x):
        return int((self.cvWidth * x) / self.aWidth)
        
    def cvY(self, y):
        return int((self.cvHeight * y) / self.aHeight)

    def cvXY(self, l):
        r = list()
        for i in range(0, len(l), 2):
            r.append(self.cvX(l[i]))
            r.append(self.cvY(l[i + 1]))
        return r
            
    def configAreas(self, numAreas, overscan, analyzeSize):
        self.edgeWeighting = -1
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

            # Calculate overscan and resulting canvas size
        ovx = (self.width * overscan) / 1000
        ovy = (self.height * overscan) / 1000
        width = self.width - 2 * ovx
        height = self.height - 2 * ovy
        self.cvWidth = width
        self.cvHeight = height

            # Apply overscan and canvas size
        cv["width"] = width
        cv["height"] = height
        cv["background"] = "black"
        self.parent["padx"] = ovx
        self.parent["pady"] = ovy
        self.parent["background"] = "cyan"
        
            # Calculate analyze window size
        aWidth = (analyzeSize + 1) * 64
        aHeight = (aWidth * self.height) / self.width
        self.aWidth = aWidth
        self.aHeight = aHeight

            # Calculate number of areas for each border
        sTop = nTop + nTopLeft + nTopRight
        sBottom = nBottom + nBottomLeft + nBottomRight
        sLeft = nLeft + nTopLeft + nBottomLeft
        sRight = nRight + nTopRight + nBottomRight
        self.sTop = sTop
        self.sBottom = sBottom
        self.sLeft = sLeft
        self.sRight = sRight

            # Calculate area width for each border
        if sTop:
            topSizeX = int(aWidth / sTop)
            topLastX = int((aWidth * (sTop - 1)) / sTop)
        else:
            topSizeX = 0
            topLastX = 0
            
        if sBottom:
            bottomSizeX = int(aWidth / sBottom)
            bottomLastX = int((aWidth * (sBottom - 1)) / sBottom)
        else:
            bottomSizeX = 0
            bottomLastX = 0
            
        if sLeft:
            leftSizeY = int(aHeight / sLeft)
            leftLastY = int((aHeight * (sLeft - 1)) / sLeft)
        else:
            leftSizeY = 0
            leftLastY = 0
    
        if sRight:
            rightSizeY = int(aHeight / sRight)
            rightLastY = int((aHeight * (sRight - 1)) / sRight)
        else:
            rightSizeY = 0
            rightLastY = 0
            
            # Calculate depth (border towards center length) for each border
        topSizeY = int(aHeight / 2)
        if leftSizeY and leftSizeY < topSizeY:
            topSizeY = leftSizeY
        if rightSizeY and rightSizeY < topSizeY:
            topSizeY = rightSizeY

        bottomSizeY = aHeight - int(aHeight / 2)
        if leftLastY > bottomSizeY:
            bottomSizeY = leftLastY
        if rightLastY > bottomSizeY:
            bottomSizeY = rightLastY
            
        leftSizeX = int(aWidth / 2)
        if topSizeX and topSizeX < leftSizeX:
            leftSizeX = topSizeX
        if bottomSizeX and bottomSizeX < leftSizeX:
            leftSizeX = bottomSizeX
        
        rightSizeX = aWidth - int(aWidth / 2)
        if topLastX > rightSizeX:
            rightSizeX = topLastX
        if bottomLastX > rightSizeX:
            rightSizeX = bottomLastX
            
            
        pTop = [ None ] * nTop
        x = 0
        
            # top left corner
        if nTopLeft:
            pTopLeft = [ 0, 0, topSizeX, 0, topSizeX, topSizeY, leftSizeX, topSizeY, leftSizeX, leftSizeY, 0, leftSizeY ]
            x = topSizeX
        elif nTop == 1:
            pTop[0] = [ 0, 0, aWidth, 0, rightSizeX, topSizeY, leftSizeX, topSizeY ]
        elif nTop > 1:
            pTop[0] = [ 0, 0, topSizeX, 0, topSizeX, topSizeY, leftSizeX, topSizeY ]

            # top right corner
        if nTopRight:
            pTopRight = [ aWidth, 0, aWidth, rightSizeY, rightSizeX, rightSizeY, rightSizeX, topSizeY, topLastX, topSizeY, topLastX, 0 ]
        elif nTop > 1:
            pTop[nTop - 1] = [ aWidth, 0, rightSizeX, topSizeY, topLastX, topSizeY, topLastX, 0 ]

            # top
        for i in range(nTop):
            x2 = int((aWidth * (i + nTopLeft + 1)) / sTop)
            if pTop[i] == None:
                pTop[i] = [ x, 0, x2, 0, x2, topSizeY, x, topSizeY ]
            x = x2

        pBottom = [ None ] * nBottom
        x = 0
        
            # bottom left corner
        if nBottomLeft:
            pBottomLeft = [ 0, aHeight, 0, leftLastY, leftSizeX, leftLastY, leftSizeX, bottomSizeY, bottomSizeX, bottomSizeY, bottomSizeX, aHeight ]
            x = bottomSizeX
        elif nBottom == 1:
            pBottom[0] = [ 0, aHeight, leftSizeX, bottomSizeY, rightSizeX, bottomSizeY, aWidth, aHeight ]
        elif nBottom > 1:
            pBottom[0] = [ 0, aHeight, leftSizeX, bottomSizeY, bottomSizeX, bottomSizeY, bottomSizeX, aHeight ]

            # bottom right corner
        if nBottomRight:
            pBottomRight = [ aWidth, aHeight, bottomLastX, aHeight, bottomLastX, bottomSizeY, rightSizeX, bottomSizeY, rightSizeX, rightLastY, aWidth, rightLastY ]
        elif nBottom > 1:
            pBottom[nBottom - 1] = [ aWidth, aHeight, bottomLastX, aHeight, bottomLastX, bottomSizeY, rightSizeX, bottomSizeY ]

            # bottom
        for i in range(nBottom):
            x2 = int((aWidth * (i + nBottomLeft + 1)) / sBottom)
            if pBottom[i] == None:
                pBottom[i] = [ x, aHeight, x, bottomSizeY, x2, bottomSizeY, x2, aHeight ]
            x = x2

        pLeft = [ None ] * nLeft
        y = 0

            # left top corner
        if nTopLeft:
            y = leftSizeY
        elif nLeft == 1:
            pLeft[0] = [ 0, 0, leftSizeX, topSizeY, leftSizeX, bottomSizeY, 0, aHeight ]
        elif nLeft > 1:
            pLeft[0] = [ 0, 0, leftSizeX, topSizeY, leftSizeX, leftSizeY, 0, leftSizeY ]

            # left bottom corner
        if not nBottomLeft and nLeft > 1:
            pLeft[nLeft - 1] = [ 0, aHeight, 0, leftLastY, leftSizeX, leftLastY, leftSizeX, bottomSizeY ]

            # left
        for i in range(nLeft):    
            y2 = int((aHeight * (i + nTopLeft + 1)) / sLeft)
            if pLeft[i] == None:
                pLeft[i] = [ 0, y, leftSizeX, y, leftSizeX, y2, 0, y2 ]
            y = y2
            
        pRight = [ None ] * nRight
        y = 0

            # right top corner
        if nTopRight:
            y = rightSizeY
        elif nRight == 1:
            pRight[0] = [ aWidth, 0, aWidth, aHeight, rightSizeX, bottomSizeY, rightSizeX, topSizeY ]
        elif nRight > 1:
            pRight[0] = [ aWidth, 0, aWidth, rightSizeY, rightSizeX, rightSizeY, rightSizeX, topSizeY ]

            # right bottom corner
        if not nBottomRight and nRight > 1:
            pRight[nRight - 1] = [ aWidth, aHeight, rightSizeX, bottomSizeY, rightSizeX, rightLastY, aWidth, rightLastY ]

            # right
        for i in range(nRight):    
            y2 = int((aHeight * (i + nTopRight + 1)) / sRight)
            if pRight[i] == None:
                pRight[i] = [ width, y, width, y2, rightSizeX, y2, rightSizeX, y ]
            y = y2

            # center
        if nCenter:
            pCenter = [ leftSizeX, topSizeY, rightSizeX, topSizeY, rightSizeX, bottomSizeY, leftSizeX, bottomSizeY ]

            # Build canvas items
        cv.delete(ALL)

        self.weightImg = Image.new("L", (width, height), color="black")
        self.weightDraw = ImageDraw.Draw(self.weightImg)
        cv.weightImg = ImageTk.PhotoImage(self.weightImg)
        self.weightImgId = cv.create_image(0, 0, image=cv.weightImg, anchor=NW, state=HIDDEN)
        
        if nTopLeft:
            cv.create_polygon(self.cvXY(pTopLeft), tags="TopLeft")
        if nTopRight:
            cv.create_polygon(self.cvXY(pTopRight), tags="TopRight")
        if nBottomLeft:
            cv.create_polygon(self.cvXY(pBottomLeft), tags="BottomLeft")
        if nBottomRight:
            cv.create_polygon(self.cvXY(pBottomRight), tags="BottomRight")
        if nCenter:
            cv.create_polygon(self.cvXY(pCenter), tags="Center")
        
        for i in range(nTop):
            cv.create_polygon(self.cvXY(pTop[i]), tags="Top-{0}".format(i + 1))
        for i in range(nBottom):
            cv.create_polygon(self.cvXY(pBottom[i]), tags="Bottom-{0}".format(i + 1))
        for i in range(nLeft):
            cv.create_polygon(self.cvXY(pLeft[i]), tags="Left-{0}".format(i + 1))
        for i in range(nRight):
            cv.create_polygon(self.cvXY(pRight[i]), tags="Right-{0}".format(i + 1))
            
        for id in cv.find_all():
            if id != self.weightImgId:
                cv.itemconfigure(id, fill="", outline="#808080", width=3)
                cv.tag_bind(id, "<Button-1>", self.cbSelectArea)

    def calcEdgeWeighting(self, edgeWeighting):
        w = float(edgeWeighting) / 10.0
        fHeight = float(self.aHeight - 1)
        fWidth = float(self.aWidth - 1)
        centerY = self.aHeight / 2
        centerX = self.aWidth / 2
        for y in range(self.aHeight):
            yNorm = float(y) / fHeight
            if self.sTop:
                wTop = pow(1.0 - yNorm, w)
            if self.sBottom:
                wBottom = pow(yNorm, w)
            for x in range(self.aWidth):
                xNorm = float(x) / fWidth
                weight = 0.0
                if self.sLeft and x < centerX:
                    weight = pow(1.0 - xNorm, w)
                if self.sRight and x >= centerX:
                    weight = max(weight, pow(xNorm, w))
                if self.sTop and y < centerY:
                    weight = max(weight, wTop)
                if self.sBottom and y >= centerY:
                    weight = max(weight, wBottom)   
                bright = int(255.0 * weight)
                px = self.cvX(x)
                px2 = self.cvX(x + 1)
                py = self.cvY(y)
                py2 = self.cvY(y + 1)
                if bright > 32:
                    bBright = bright - 32
                else:
                    bBright = 0
                self.weightDraw.polygon([(px, py), (px2, py), (px2, py2), (px, py2)], fill=bright, outline=bBright)
        self.root.weightImg.paste(self.weightImg)
        self.edgeWeighting = edgeWeighting
        
    def showEdgeWeighting(self, edgeWeighting, topWin):
        if self.edgeWeighting != edgeWeighting:
            cursor = topWin["cursor"]
            topWin["cursor"] = "watch"
            self.root.update_idletasks()
            self.calcEdgeWeighting(edgeWeighting)
            topWin["cursor"] = cursor
        if self.edgeWeighting == edgeWeighting:
            self.root.itemconfigure(self.weightImgId, state=NORMAL)

    def hideEdgeWeighting(self):
        self.root.itemconfigure(self.weightImgId, state=HIDDEN)
        
    def resetAreas(self):
        self.parent["background"] = "cyan"
        self.root["background"] = "black"
        for id in self.root.find_all():
            if id != self.weightImgId:
                self.root.itemconfigure(id, fill="", outline="#808080")
        self.selectedArea = None
        
    def initAreas(self, color):
        self.parent["background"] = color
        self.root["background"] = color
        for id in self.root.find_all():
            if id != self.weightImgId:
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
            if id != self.weightImgId:
                if self.selectedArea:
                    cv.itemconfigure(self.selectedArea, outline="#808080")
                self.selectedArea = cv.gettags(id)[0]
                cv.tag_raise(id)
                cv.itemconfigure(id, outline="yellow")

        for cb in self.selectCallbacks:
            cb.cbAreaSelected()
