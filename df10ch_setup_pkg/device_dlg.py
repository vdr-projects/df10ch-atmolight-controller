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
import tkFileDialog
import usb
import pickle
import string
import time

import device_drv
import firmware

class DeviceDialog:
    def __init__(self, layoutDlg, master=None, **args):
        self.layoutDlg = layoutDlg
        self.selectedConfig = None
        self.selectedDeviceIdx = -1
        self.echo_test_running = False
        
        root = Frame(master, **args)
        self.root = root
        root.bind("<Map>", self.cbSheetSelected)

        Label(root, text="Device Control", font=tkFont.Font(weight="bold")).grid(row=0, column=0, columnspan=7, padx=5, pady=5)

        self.varDeviceList = StringVar()
        self.lbDevices = Listbox(root, selectmode=SINGLE, activestyle=NONE, width=20, height=8, listvariable=self.varDeviceList)
        self.lbDevices.grid(row=1, column=0, columnspan=2, rowspan=4, padx=5, pady=5, sticky=N+S+E+W)
        self.lbDevices.bind("<ButtonRelease-1>", self.cbSelectDevice)

        self.varVersion = StringVar()
        Label(root, text="Version:").grid(row=1, column=2, sticky=E)
        self.etVersion = Label(root, textvariable=self.varVersion, anchor=W, relief=SUNKEN)
        self.etVersion.grid(row=1, column=3, columnspan=4, padx=5, pady=5, sticky=W+E)
        
        self.varPWMRes = StringVar()
        Label(root, text="PWM Resolution:").grid(row=2, column=2, sticky=E)
        self.etPWMRes = Label(root, textvariable=self.varPWMRes, anchor=W, relief=SUNKEN)
        self.etPWMRes.grid(row=2, column=3, columnspan=4, padx=5, pady=5, sticky=W+E)
        
        self.varPWMFreq = IntVar()
        Label(root, text="PWM Frequency:").grid(row=3, column=2, sticky=E)
        self.varPWMFreq.set(device_drv.MIN_PWM_FREQ)
        self.scPWMFreq = Scale(root, length=250, from_=device_drv.MIN_PWM_FREQ, to=device_drv.MAX_PWM_FREQ, resolution=1, tickinterval=50, orient=HORIZONTAL, variable=self.varPWMFreq, command=self.cbSetPWMFreq)
        self.scPWMFreq.grid(row=3, column=3, columnspan=4, padx=5, pady=5, sticky="W")

        self.varCommonBright = IntVar()
        Label(root, text="Common Brightness:").grid(row=4, column=2, sticky=E)
        self.varCommonBright.set(0)
        self.scCommonBright = Scale(root, length=250, from_=0, to=255, resolution=1, tickinterval=50, orient=HORIZONTAL, variable=self.varCommonBright, command=self.cbSetCommonBrightness)
        self.scCommonBright.grid(row=4, column=3, columnspan=4, padx=5, pady=5, sticky=W)

        self.btScanDevices = Button(root, text="Scan Devices", command=self.cbScanDevices)
        self.btScanDevices.grid(row=5, column=0, padx=5, pady=5, ipadx=5)

        self.btShowStatus = Button(root, text="Show Status", command=self.cbShowStatus)
        self.btShowStatus.grid(row=6, column=0, padx=5, pady=5, ipadx=5)

        self.btStoreSetup = Button(root, text="Backup", command=self.cbBackupSetup)
        self.btStoreSetup.grid(row=5, column=1, padx=5, pady=5, ipadx=5)

        self.btStoreSetup = Button(root, text="Restore", command=self.cbRestoreSetup)
        self.btStoreSetup.grid(row=6, column=1, padx=5, pady=5, ipadx=5)

        self.btResetSetup = Button(root, text="Firmware update", command=self.cbFirmwareUpdate)
        self.btResetSetup.grid(row=5, column=2, columnspan=4, padx=5, pady=5, ipadx=5)

        self.btEchoTest = Button(root, text="Start echo test", command=self.cbEchoTest)
        self.btEchoTest.grid(row=6, column=2, columnspan=4, padx=5, pady=5, ipadx=5)

        self.btResetSetup = Button(root, text="Reset Setup", command=self.cbResetSetup)
        self.btResetSetup.grid(row=5, column=6, padx=5, pady=5, ipadx=5)

        self.btStoreSetup = Button(root, text="Store Setup", command=self.cbStoreSetup)
        self.btStoreSetup.grid(row=6, column=6, padx=5, pady=5, ipadx=5)

        self.varStatus = StringVar()
        self.lbStatus = Label(root, textvariable=self.varStatus, anchor=W, relief=RIDGE)
        self.lbStatus.grid(row=7, column=0, columnspan=7, padx=0, pady=0, sticky=W+E)
        

    def cbSheetSelected(self, event):
        if self.selectedConfig:
            self.loadDeviceValues()

    def cbShowStatus(self):
        if len(device_drv.DeviceList):
            self.showStatus()

    def cbEchoTest(self):
        if self.echo_test_running:
            self.echo_test_running = False
        else:
            if self.selectedDeviceIdx != -1:
                self.echoTest()
        
    def cbFirmwareUpdate(self):
        if len(device_drv.DeviceList):
            self.firmwareUpdate()

    def cbResetSetup(self):
        if len(device_drv.ConfigMap):
            self.resetSetup()
        if self.selectedConfig:
            self.loadDeviceValues()

    def cbStoreSetup(self):
        if len(device_drv.ConfigMap):
            self.storeSetup()
        if self.selectedConfig:
            self.loadDeviceValues()

    def cbBackupSetup(self):
        if self.selectedConfig:
            self.backupSetup()

    def cbRestoreSetup(self):
        if self.selectedConfig:
            self.restoreSetup()

    def cbSetCommonBrightness(self, val):
        if self.selectedConfig:
            try:
                self.selectedConfig.setCommonBright(int(val))
            except device_drv.AtmoControllerError as err:
                tkMessageBox.showerror(self.root.winfo_toplevel().title(), err.__str__())

    def cbSetPWMFreq(self, val):
        if self.selectedConfig:
            try:
                self.selectedConfig.setPWMFreq(int(val))
                self.varPWMRes.set(self.selectedConfig.pwmRes)
            except device_drv.AtmoControllerError as err:
                tkMessageBox.showerror(self.root.winfo_toplevel().title(), err.__str__())
 
    def cbSelectDevice(self, event):
        s = self.lbDevices.curselection()
        if len(s) == 1:
            self.selectDevice(int(s[0]))
    
    def cbScanDevices(self):
        self.scanDevices()

    def scanDevices(self):
        self.selectedConfig = None
        self.selectedDeviceIdx = -1
        retry = True
        while retry:
            try:
                device_drv.LoadConfigs()
            except (device_drv.AtmoControllerError, usb.USBError) as err:        
                if not tkMessageBox.askretrycancel(self.root.winfo_toplevel().title(), "Scanning for controllers fails:" + err.__str__(), icon=tkMessageBox.ERROR):
                    if len(device_drv.DeviceList):
                        retry = False
                    else:
                        return False
            else:
                if len(device_drv.DeviceList):
                    retry = False
                else:
                    if not tkMessageBox.askretrycancel(self.root.winfo_toplevel().title(), "No Controllers found!", icon=tkMessageBox.ERROR):
                        return False

        idList = ""
        for dev in device_drv.DeviceList:
            if len(idList) > 0:
                idList = idList + " "
            idList = idList + dev.id
        self.varDeviceList.set(idList)

        self.layoutDlg.setLayoutFromConfig()
        self.selectDevice(0)
        return True
        
    def selectDevice(self, i):
        self.selectedDeviceIdx = i
        dev = device_drv.DeviceList[i]
        id = dev.id
        if id in device_drv.ConfigMap:
            config = device_drv.ConfigMap[id]
            if self.selectedConfig != config:
                self.selectedConfig = config
                self.scCommonBright.configure(to=self.selectedConfig.commonPWMRes)
                self.loadDeviceValues()
        else:
            if dev.bootloader_mode():
                s = "Bootloader USB:{0}".format(dev.version)
            else:
                s = "USB:{0} Bootloader PWM:{1:04X}".format(dev.version, dev.get_pwm_version())
            self.varVersion.set(s)
        self.lbDevices.selection_clear(0, END)
        self.lbDevices.selection_set(i)
        self.lbDevices.see(i)
        
    def loadDeviceValues(self):
        self.varVersion.set(self.selectedConfig.version)
        self.varPWMRes.set(self.selectedConfig.pwmRes)
        self.varPWMFreq.set(self.selectedConfig.pwmFreq)
        self.varCommonBright.set(self.selectedConfig.commonBright)
 
    def storeAndQuit(self, root):
        if len(device_drv.ConfigMap):
            if tkMessageBox.askokcancel(self.root.winfo_toplevel().title(), "Store Setup?", icon=tkMessageBox.QUESTION):
                self.storeSetup()
            self.resetDevices()
        device_drv.ReleaseDevices()
        root.quit()
        
    def storeSetup(self):
        self.layoutDlg.setConfigFromLayout()
        try:
            for id in device_drv.ConfigMap.keys():
                config = device_drv.ConfigMap[id]
                config.write()
        except device_drv.AtmoControllerError as err:
            tkMessageBox.showerror(self.root.winfo_toplevel().title(), err.__str__())

    def resetSetup(self):
        if tkMessageBox.askokcancel(self.root.winfo_toplevel().title(), "Really reset setup of all controllers?", default="cancel", icon=tkMessageBox.QUESTION):
            try:
                for id in device_drv.ConfigMap.keys():
                    config = device_drv.ConfigMap[id]
                    config.reset()
            except device_drv.AtmoControllerError as err:
                tkMessageBox.showerror(self.root.winfo_toplevel().title(), err.__str__())

    def resetDevices(self):
        try:
            for id in device_drv.ConfigMap.keys():
                config = device_drv.ConfigMap[id]
                config.ctrl.reset_pwm_ctrl()
        except device_drv.AtmoControllerError as err:
            tkMessageBox.showerror(self.root.winfo_toplevel().title(), err.__str__())
            
    def backupSetup(self):
        self.layoutDlg.setConfigFromLayout()
        ctrl = self.selectedConfig.ctrl
        initialfile = ctrl.id
        initialfile = string.replace(initialfile, "[", "(")
        initialfile = string.replace(initialfile, "]", ")")
        initialfile = string.replace(initialfile, ",", "_")
        initialfile = initialfile + ".dfc"
        self.selectedConfig.ctrl = None
        file = None
        try:
            file = tkFileDialog.asksaveasfile("w", title="Backup Configuration for " + self.selectedConfig.id, defaultextension=".dfc", filetypes=[ ("DF10CH Config", "*.dfc") ], initialfile=initialfile)
            if file:
                pickle.dump(self.selectedConfig, file)
        except IOError:
            tkMessageBox.showerror(self.root.winfo_toplevel().title(), "Could not save configuration to file!")
        finally:
            self.selectedConfig.ctrl = ctrl
            if file:
                file.close()
    
    def restoreSetup(self):
        file = None
        try:
            file = tkFileDialog.askopenfile("r", title="Restore Configuration for " + self.selectedConfig.id, defaultextension=".dfc", filetypes=[ ("DF10CH Config", "*.dfc") ])
            if file:
                config = pickle.load(file)
            else:
                return
        except IOError:
            tkMessageBox.showerror(self.root.winfo_toplevel().title(), "Could not read configuration from file!")
            return
        finally:
            if file:
                file.close()
            
        config.id = self.selectedConfig.id
        config.ctrl = self.selectedConfig.ctrl
        
        try:
            config.ctrl.set_common_brightness(config.commonBright)
            config.ctrl.set_pwm_freq(config.pwmFreq)
            config.write()
        except device_drv.AtmoControllerError as err:
            tkMessageBox.showerror(self.root.winfo_toplevel().title(), err.__str__())

        device_drv.ConfigMap[config.id] = config
        self.selectedConfig = config
        self.layoutDlg.setLayoutFromConfig()
        self.scCommonBright.configure(to=self.selectedConfig.commonPWMRes)
        self.loadDeviceValues()

    def firmwareUpdate(self):
        try:
            filename = tkFileDialog.askopenfilename(title="Select firmware", defaultextension=".dff", filetypes=[ ("DF10CH Firmware", "*.dff") ])
            if not filename or len(filename) == 0:
                return
            fw = firmware.FlashMem(filename, 64, True)
        except (IOError, firmware.FirmwareFlashError) as err:
            tkMessageBox.showerror(self.root.winfo_toplevel().title(), err.__str__())
            return
        
        target = fw.target
        if target != "DF10CH-USB" and target != "DF10CH-PWM":
            tkMessageBox.showerror(self.root.winfo_toplevel().title(), "Unknown firmware target '{0}'!".format(target))
            return

        if target == "DF10CH-PWM":
            for ctrl in device_drv.DeviceList:
                if ctrl.bootloader_mode():
                    tkMessageBox.showerror(self.root.winfo_toplevel().title(), "{0}: Firmware of USB controller must be installed first!".format(ctrl.id))
                    return
                
        if not tkMessageBox.askokcancel(self.root.winfo_toplevel().title(), "Target controller: {0}, Firmware version: {1}. Really start firmware update?".format(target, fw.version), default="cancel", icon=tkMessageBox.QUESTION):
            return

        self.displayStatus("Start bootloaders...")

        doFlash = True
        doRefresh = False
        try:
            for ctrl in device_drv.DeviceList:
                if target == "DF10CH-USB":
                    if not ctrl.bootloader_mode():
                        doRefresh = True
                        ctrl.start_bootloader()
                else:
                    if not ctrl.get_pwm_bootloader_mode():
                        ctrl.start_pwm_ctrl_bootloader()
        except device_drv.AtmoControllerError as err:
            tkMessageBox.showerror(self.root.winfo_toplevel().title(), err.__str__())
            doFlash = False

        if doRefresh:
            time.sleep(5.0)
            try:
                device_drv.FindDevices()
            except (device_drv.AtmoControllerError, usb.USBError) as err:
                tkMessageBox.showerror(self.root.winfo_toplevel().title(), err.__str__())
                doFlash = False

        for ctrl in device_drv.DeviceList:
            try:
                if target == "DF10CH-USB":
                    if ctrl.bootloader_mode():
                        if doFlash:
                            pageSize = ctrl.get_flash_page_size()
                            if pageSize != fw.pageSize:
                                fw = firmware.FlashMem(filename, pageSize)
                            firstPage = fw.getPageForAddr(0x0000)
                            i = 1
                            if firstPage:
                                fp = firmware.FlashPage(0x0000, pageSize)
                                ctrl.write_flash_page(fp.baseAddr, fp.data)
                                i = 2
                            n = len(fw.pageList)
                            for fp in fw.pageList:
                                if fp != firstPage:
                                    self.displayStatus("Flashing USB controller {0}: {1}%".format(ctrl.id, i * 100 / n))
                                    ctrl.write_flash_page(fp.baseAddr, fp.data)
                                    i = i + 1
                            if firstPage:
                                ctrl.write_flash_page(firstPage.baseAddr, firstPage.data)
                            time.sleep(3.0)

                            i = 1
                            for fp in fw.pageList:
                                self.displayStatus("Verifying USB controller {0}: {1}%".format(ctrl.id, i * 100 / n))
                                data = ctrl.read_flash(fp.baseAddr, fp.pageSize)
                                fp.verify(data)
                                i = i + 1
                            time.sleep(3.0)
                    else:
                        tkMessageBox.showerror(self.root.winfo_toplevel().title(), "{0}: Bootloader of USB controller does not start!".format(ctrl.id))
                        doFlash = False
                else:
                    if ctrl.get_pwm_bootloader_mode():
                        if doFlash:
                            pageSize = ctrl.get_pwm_flash_page_size()
                            if pageSize != fw.pageSize:
                                fw = firmware.FlashMem(filename, pageSize)
                            firstPage = fw.getPageForAddr(0x0000)
                            i = 1
                            if firstPage:
                                fp = firmware.FlashPage(0x0000, pageSize)
                                ctrl.write_pwm_flash_page(fp.baseAddr, fp.data)
                                i = 2
                            n = len(fw.pageList)
                            for fp in fw.pageList:
                                if fp != firstPage:
                                    self.displayStatus("Flashing PWM controller {0}: {1}%".format(ctrl.id, i * 100 / n))
                                    ctrl.write_pwm_flash_page(fp.baseAddr, fp.data)
                                    i = i + 1
                            if firstPage:
                                ctrl.write_pwm_flash_page(firstPage.baseAddr, firstPage.data)
                            time.sleep(3.0)

                            i = 1
                            for fp in fw.pageList:
                                self.displayStatus("Verifying PWM controller {0}: {1}%".format(ctrl.id, i * 100 / n))
                                data = ctrl.read_pwm_flash(fp.baseAddr, fp.pageSize)
                                fp.verify(data)
                                i = i + 1
                            time.sleep(3.0)
                    else:
                        tkMessageBox.showerror(self.root.winfo_toplevel().title(), "{0}: Bootloader of PWM controller does not start!".format(ctrl.id))
                        doFlash = False
            except (device_drv.AtmoControllerError, firmware.FirmwareFlashError) as err:
                tkMessageBox.showerror(self.root.winfo_toplevel().title(), err.__str__())
                doFlash = False
                    
        doRefresh = False
        for ctrl in device_drv.DeviceList:
            try:
                if target == "DF10CH-USB":
                    if ctrl.bootloader_mode():
                        doRefresh = True
                        ctrl.start_appl()
                else:
                    if ctrl.get_pwm_bootloader_mode():
                        ctrl.reset_pwm_ctrl()
            except device_drv.AtmoControllerError as err:
                tkMessageBox.showerror(self.root.winfo_toplevel().title(), err.__str__())

        if doRefresh:
            self.displayStatus("Start firmware...")
            time.sleep(5.0)
        self.displayStatus("")
        self.scanDevices()
        
    def displayStatus(self, msg):
        self.varStatus.set(msg)
        self.root.update_idletasks()

    def showStatus(self):
        msg = ""
        for dev in device_drv.DeviceList:
            request_stat = "N/A"
            reply_stat = "N/A"
            try:
                rc = dev.get_reply_error_status()
            except device_drv.AtmoControllerError as err:
                pass
            else:
                reply_stat = device_drv.GetCommErrMsg(rc)

            try:
                rc = dev.get_request_error_status()
            except device_drv.AtmoControllerError as err:
                pass
            else:
                request_stat = device_drv.GetCommErrMsg(rc)

            msg = msg + "{0}: ERR:{1} USB:{2} PWM:{3}\n".format(dev.id, dev.error_count, reply_stat, request_stat)
        tkMessageBox.showinfo(self.root.winfo_toplevel().title() + " Communication status", msg)

    def echoTest(self):
        self.echo_test_running = True
        self.btEchoTest['text'] = "Stop echo test"
        dev = device_drv.DeviceList[self.selectedDeviceIdx]
        testValue = 0
        while testValue < 0x7FFFFFFF:
            self.varStatus.set("Testing {0}: {1}".format(dev.id, testValue))
            self.root.update()
            if not self.echo_test_running:
                break
            try:
                dev.pwm_echo_test(testValue)
            except device_drv.AtmoControllerError as err:
                tkMessageBox.showerror(self.root.winfo_toplevel().title(), err.__str__())
            testValue = testValue + 1
        self.varStatus.set("")
        self.btEchoTest['text'] = "Start echo test"
