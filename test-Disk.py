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
from subprocess import call
from re import findall
from Disk import Disk
from time import sleep
from os import getenv
from threading import enumerate
CIRCLE_ENV = getenv('CIRCLE_ENV') == 'test'

class test_Disk(unittest.TestCase):

  @unittest.skipUnless(CIRCLE_ENV, "Only for CircleCI environment")
  def test_00_notStarted(self):
    self.Disk = Disk({'login': 'stc.yd', 'auth': getenv('API_TOKEN'), 'path': '~/yd', 'start': False,
                      'ro': False, 'ow': False, 'exclude': ['excluded_folder']})
    sleep(10)
    self.assertTrue(self.Disk.status == 'none')
    self.Disk.exit()
    self.assertEqual(len(enumerate()), 1)

  @unittest.skipUnless(CIRCLE_ENV, "Only for CircleCI environment")
  def test_01_noAccess(self):
    self.Disk = Disk({'login': 'stc.yd', 'auth': getenv('API_TOKEN'), 'path': '/root', 'start': True,
                      'ro': False, 'ow': False, 'exclude': ['excluded_folder']})
    sleep(10)
    self.assertTrue(self.Disk.status == 'fault')
    self.Disk.exit()
    self.assertEqual(len(enumerate()), 1)

  @unittest.skipUnless(CIRCLE_ENV, "Only for CircleCI environment")
  def test_1_InitialSync(self):
    global Disk
    Disk = Disk({'login': 'stc.yd', 'auth': getenv('API_TOKEN'), 'path': '~/yd', 'start': True,
                 'ro': False, 'ow': False, 'exclude': ['excluded_folder']})
    sleep(60)
    self.assertTrue(Disk.status == 'idle')

  @unittest.skipUnless(CIRCLE_ENV, "Only for CircleCI environment")
  def test_2_TestSequence(self):
    global Disk
    call(['bash', '/home/ubuntu/yd/test.sh'])
    sleep(30)
    self.assertTrue(Disk.status == 'idle')

  @unittest.skipUnless(CIRCLE_ENV, "Only for CircleCI environment")
  def test_3_Trush(self):
    global Disk
    Disk.trash()
    sleep(10)
    self.assertTrue(Disk.status == 'idle')

  @unittest.skipUnless(CIRCLE_ENV, "Only for CircleCI environment")
  def test_4_Exit(self):
    global Disk
    Disk.exit()
    self.assumeEqual(len(enumerate()), 1)

if __name__ == '__main__':
  unittest.main()
