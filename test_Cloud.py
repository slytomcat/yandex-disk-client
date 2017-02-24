#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  test_Cloud.py
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
  def setUp(self):
    try:
      '''Local test token have to be store_requestd in file 'OAuth.info' with following format:
         devtoken:  <OAuth token>
      '''
      with open('OAuth.info', 'rt') as f:
        token = findall(r'devtoken: (.*)', f.read())[0].strip()
        #print ('Token: %s'%(token))
    except:
      ''' CircleCi token is in the environment variable API_TOKEN
      '''
      token = getenv('API_TOKEN')
    self.cloud = Cloud(token)

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
    stat, res = self.cloud.delete('newtestdir')
    self.assertTrue(stat)

  def test_bigDir_ops(self):
    stat, res = self.cloud.copy('Music', 'MusicTest')
    self.assertTrue(stat)
    stat, res = self.cloud.move('MusicTest', 'MusicTest2')
    self.assertTrue(stat)
    stat, res = self.cloud.delete('MusicTest2')
    self.assertTrue(stat)

  def test_props(self):
    stat, res = self.cloud.setProps('Sea.jpg', uid=1000, gid=1000, mode=33204)
    self.assertTrue(stat)
    stat, res = self.cloud.getResource('Sea.jpg')
    self.assertTrue(stat)
    props = res.get("custom_properties")
    self.assertEqual(props.get('uid'), 1000)
    self.assertEqual(props.get('gid'), 1000)
    self.assertEqual(props.get('mode'), 33204)

  def test_trush(self):
    stat, res = self.cloud.trash()
    self.assertTrue(stat)
    stat, res = self.cloud.getDiskInfo()
    self.assertTrue(stat)
    self.assertEqual(res.get('trash_size'), 0)

  def test_up_down(self):
    stat, res = self.cloud.upload('README.md', 'README_.md')
    self.assertTrue(stat)
    self.cloud.download('README_.md', 'README_.md')
    self.assertTrue(stat)
    remove('README_.md')
    stat, res = self.cloud.delete('README_.md')
    self.assertTrue(stat)

  def test_last(self):
    stat, res = self.cloud.getLast()
    self.assertTrue(stat)
    self.assertIs(type(res), list)

  def test_list(self):
    stat, res = self.cloud.getList(chunk=5)
    self.assertTrue(stat)
    self.assertIs(type(res), list)
    self.assertEqual(len(res), 5)

if __name__ == '__main__':
  unittest.main()
