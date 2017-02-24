#!/usr/bin/env python3
#
#  test-Disk.py
#
#  Copyright 2017 Sly_tom_cat <stc@stc-nb>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#

import unittest
from subprocess import check_output
from re import findall

class test_Disk(unittest.TestCase):
  def test_Disk(self):
    output = check_output('./disk_test.sh', shell=True)
    self.assertEqual(len(findall(r'Traceback', output)), 0)

if __name__ == '__main__':
  unittest.main()
