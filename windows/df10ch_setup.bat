REM -- Start DF10CH Setup
REM Expand PATH so that libusb-1.0.dll could be found
set PATH=.;%PATH%
.\df10ch_setup.exe %1 %2 %3
