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
# Df10CH setup program installation script
#

from distutils.core import setup
setup(name='df10ch_setup',
      version='1',
      description='DF10CH Setup program',
      author='Andreas Auras',
      author_email='yak54@gmx.net',
      url='http://www.vdr-wiki.de/wiki/index.php/VDR_Wiki:DF10CH_Atmolight_Kontroller',
      requires=[ 'usb', 'TKinter' ],
      scripts=[ 'df10ch_setup.py' ],
      packages = [ 'df10ch_setup_pkg' ],
      )

