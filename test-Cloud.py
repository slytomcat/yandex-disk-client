#!/usr/bin/env python3
#
#  test_self.cloud.py
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
from re import findall
from os import remove, getenv
from Cloud import Cloud

class test_Cloud(unittest.TestCase):
  '''Local test token have to be store_requestd in file 'OAuth.info' with following format:
     CLOUD_TOKEN:  <OAuth token>
     CircleCi token is in the environment variable CLOUD_TOKEN
  '''
  cloud = Cloud(getenv('CLOUD_TOKEN') if getenv('CIRCLE_ENV') == 'test' else
                findall(r'CLOUD_TOKEN: (.*)', open('OAuth.info', 'rt').read())[0].strip())

  def test_DiskInfo(self):
    stat, res = self.cloud.getDiskInfo()
    self.assertTrue(stat)
    self.assertIs(type(res), dict)

  def test_Dir_ops(self):
    stat, res = self.cloud.mkDir('testdir')
    self.assertTrue(stat)
    stat, res = self.cloud.move('testdir', 'newtestdir')
    self.assertTrue(stat)
    stat, res = self.cloud.getResource('newtestdir')
    self.assertTrue(stat)
    stat, res = self.cloud.move('newtestdir', 'not_existing_dir/bla-bla')
    self.assertFalse(stat)
    stat, res = self.cloud.copy('newtestdir', 'not_existing_dir/bla-bla')
    self.assertFalse(stat)
    stat, res = self.cloud.mkDir('not_existing_dir/bla-bla/dir')
    self.assertFalse(stat)
    stat, res = self.cloud.delete('newtestdir')
    self.assertTrue(stat)

  def test_bigDir_1copy(self):
    stat, res = self.cloud.copy('Music', 'MusicTest')
    self.assertTrue(stat)

  def test_bigDir_2move(self):
    stat, res = self.cloud.move('MusicTest', 'MusicTestTest')
    self.assertTrue(stat)

  def test_bigDir_3delete(self):
    stat, res = self.cloud.delete('MusicTestTest')
    self.assertTrue(stat)

  def test_props_1set(self):
    stat, res = self.cloud.setProps('Sea.jpg', uid=1000, gid=1000, mode=33204)
    self.assertTrue(stat)

  def test_props_2get(self):
    stat, res = self.cloud.getResource('Sea.jpg')
    self.assertTrue(stat)
    props = res.get("custom_properties")
    self.assertFalse(props is None)
    self.assertEqual(props.get('uid'), 1000)
    self.assertEqual(props.get('gid'), 1000)
    self.assertEqual(props.get('mode'), 33204)

  def test_wrong_res(self):
    stat, res = self.cloud.getResource('not_existing_file.bla_bla')
    self.assertFalse(stat)

  def trush(self):
    stat, res = self.cloud.trash()
    self.assertTrue(stat)
    stat, res = self.cloud.getDiskInfo()
    self.assertTrue(stat)
    self.assertEqual(res.get('trash_size'), 0)

  def test_trush(self):
    self.trush()
    self.trush()

  def test_up_down1_up(self):
    stat, res = self.cloud.upload('README.md', 'README.md')
    self.assertTrue(stat)

  def test_up_down2_down(self):
    stat, res = self.cloud.download('README.md', '/tmp/README.md')
    self.assertTrue(stat)
    remove('/tmp/README.md')
    self.cloud.delete('README.md')

  def test_last(self):
    stat, res = self.cloud.getLast()
    self.assertTrue(stat)
    self.assertIs(type(res), list)

  def test_list(self):
    stat, res = self.cloud.getList(chunk=5)
    self.assertTrue(stat)
    self.assertIs(type(res), list)
    self.assertEqual(len(res), 5)

  def test_wrong_list(self):
    stat, res = self.cloud.getList(chunk=7777777777)
    self.assertFalse(stat)

  def test_wrong_delete(self):
    stat, res = self.cloud.delete('not_existing_file.bla_bla')
    self.assertFalse(stat)


if __name__ == '__main__':

  unittest.main()
