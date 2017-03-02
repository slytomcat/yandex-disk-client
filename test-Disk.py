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
from time import sleep as _sleep
from os import getenv, chdir, getcwd, remove, makedirs
from os.path import join as path_join, exists as pathExists
from shutil import rmtree

sleep = _sleep
'''
def sleep(timeout):
  if getenv('CIRCLE_ENV') == 'test':
    _sleep(timeout)
  else:
    input('>>>>')
'''

class test_Disk(unittest.TestCase):
  token = (getenv('API_TOKEN') if getenv('CIRCLE_ENV') == 'test' else
           findall(r'API_TOKEN: (.*)', open('OAuth.info', 'rt').read())[0].strip())
  disk = None

  def setUp(self):
    pass

  def test_00_notStarted(self):
    test_Disk.disk = Disk({'login': 'stc.yd', 'auth': self.token, 'path': '~/yd', 'start': False,
                           'ro': False, 'ow': False, 'exclude': ['excluded_folder']})
    sleep(2)
    self.assertTrue(self.disk.status == 'none')
    self.assertEqual(self.disk.exit(), 0)

  def test_01_noAccess(self):
    test_Disk.disk = Disk({'login': 'stc.yd', 'auth': self.token, 'path': '/root', 'start': True,
                           'ro': False, 'ow': False, 'exclude': ['excluded_folder']})
    sleep(2)
    self.assertTrue(self.disk.status == 'fault')
    self.assertEqual(self.disk.exit(), 0)

  def test_10_InitialSync(self):
    test_Disk.disk = Disk({'login': 'stc.yd', 'auth': self.token, 'path': '~/yd', 'start': True,
                           'ro': False, 'ow': False, 'exclude': ['excluded_folder']})
    sleep(50)
    self.assertTrue(self.disk.status == 'idle')

  def test_20_TestSequence(self):
    chdir(self.disk.path)
    call(['bash', 'test.sh'])
    sleep(30)
    self.assertTrue(self.disk.status == 'idle')

  def test_25_FullSync(self):
    self.disk.fullSync()
    sleep(30)
    self.assertTrue(self.disk.status == 'idle')

  def test_30_Trush(self):
    self.disk.trash()
    sleep(30)
    self.assertTrue(self.disk.status == 'idle')

  def test_40_GetStatus(self):
    res = self.disk.getStatus()
    sleep(1)
    self.assertTrue(type(res) == dict)

  def test_50_DownloadNew(self):
    self.disk.disconnect()
    remove(self.disk.cloud.h_data._filePath) # remove history
    self.disk.cloud.h_data.clear()           # reset it in memory
    path = path_join(self.disk.path, 'word.docx')
    remove(path)
    self.disk.connect()
    sleep(30)
    self.assertTrue(pathExists(path))
    self.assertTrue(self.disk.status == 'idle')

  def test_60_Remove(self):
    self.disk.disconnect()
    rmtree(path_join(self.disk.path, 'd1'))
    self.disk.connect()
    sleep(30)
    stat, _ = self.disk.cloud.getResource('d1')
    self.assertFalse(stat)
    self.assertTrue(self.disk.status == 'idle')

  def test_70_UplodNew_offLine(self):
    self.disk.disconnect()
    path = path_join(self.disk.path, 'd1', 'd2')
    makedirs(path)
    path = path_join(path, 'file')
    with open(path, 'wt') as f:
      f.write('test test file file')
    self.disk.connect()
    sleep(30)
    stat, _ = self.disk.cloud.getResource('d1/d2/file')
    self.assertTrue(stat)
    self.assertTrue(self.disk.status == 'idle')

  def test_75_UplodUpd_onLine(self):
    with open('d1/d2/file', 'wt') as f:
      f.write('test file')
    sleep(30)
    stat, _ = self.disk.cloud.getResource('d1/d2/file')
    self.assertTrue(stat)
    self.assertTrue(self.disk.status == 'idle')

  def test_80_list(self):
    l = 0
    for i in self.disk.cloud.getList(chunk=5):
      l += 1
    self.assertTrue(l > 0)

  def test_90_Exit(self):
    self.assertEqual(self.disk.exit(), 0)

  def test_99_clean(self):
    rmtree(self.disk.path, ignore_errors=True)

if __name__ == '__main__':
  unittest.main()
