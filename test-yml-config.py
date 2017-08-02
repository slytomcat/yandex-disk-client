#!/usr/bin/env python3
#
#  test-yml-config.py
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
from os.path import exists, expanduser
from os import remove
from YmlConfig import Config

class Test_jconfig(unittest.TestCase):
  defConf = {'type': 'std',
             'disks': {'stc': {'login': 'stc',
                               'path': '~/ydd',
                               'auth': '87816741346',
                               'start': True,
                               'exclude': ['tests', 'other/private'],
                               'ro': False,
                               'ow': False },
                       'stc1':{'login': 'stc1',
                               'path': '~/yd',
                               'auth': '84458090987',
                               'start': True,
                               'exclude': ['new'],
                               'ro': True,
                               'ow': False }
                      }
            }

  path = '~/cfg.cfg'

  def test_jconfig_10_create_append_save(self):
    config = Config(self.path, load=False)
    self.assertEqual(len(config), 0)
    self.assertFalse(config.loaded)
    config.append(self.defConf)
    self.assertEqual(len(config), 2)
    self.assertTrue(config.changed)
    if config.changed:
      self.assertTrue(config.save())
    self.assertFalse(config.changed)

  def test_jconfig_20_load_check_clear(self):
    config = Config(self.path)
    self.assertTrue(config.loaded)
    self.assertEqual(config, self.defConf)
    config.erase()
    self.assertTrue(config.changed)

  def test_jconfig_30_wrong_file(self):
    config = Config('not_existing_file')
    self.assertFalse(config.loaded)
    self.assertFalse(config.load('another_not_existing_file'))
    self.assertFalse(config.loaded)
    config.changed = True
    self.assertFalse(config.save('/root/not_accesseble_file'))
    self.assertTrue(config.changed)

if __name__ == '__main__':
  unittest.main()