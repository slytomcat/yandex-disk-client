#!/usr/bin/env python3
#
#  jconfig_test.py
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
from os.path import exists
from os import remove
from jconfig import Config

class Test_jconfig(unittest.TestCase):
  def setUp(self):
    self.path = 'cfg.cfg'
    if exists(self.path):
      remove(self.path)

  def test_jconfig(self):
    defConf = {'type': 'std',
               'disks': {'stc': {'login': 'stc',
                                 'path': '~/ydd',
                                 'auth': '87816741346',
                                 'start': True,
                                 'exclude': ['tests', 'other/private'],
                                 'ro': False,
                                 'ow': False },
                         'stc1':{'login': 'stc',
                                 'path': '~/yd',
                                 'auth': '84458090987',
                                 'start': True,
                                 'exclude': ['new'],
                                 'ro': True,
                                 'ow': False }
                        }
              }
    config = Config(self.path, load=False)
    self.assertEqual(len(config), 0)
    self.assertFalse(config.loaded)
    config.append(defConf)
    self.assertEqual(len(config), 2)
    self.assertTrue(config.changed)
    if config.changed:
      config.save()
    self.assertFalse(config.changed)
    newConfig = Config(self.path)
    self.assertTrue(newConfig.loaded)
    self.assertEqual(config, newConfig)

  def test_wrong_file(self):
    config = Config('not_existing_file')
    self.assertFalse(config.loaded)
    res = config.load('another_not_existing_file')
    self.assertFalse(res)
    self.assertFalse(config.loaded)
    res = config.save('/root/not_accesseble_file')
    self.assertFalse(res)

  def tearDown(self):
    if exists(self.path):
      remove(self.path)

if __name__ == '__main__':
  unittest.main()
