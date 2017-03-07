#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  test-CloudDisk.py
#
#  Copyright 2017 Sly_tom_cat <slytomcat@mail.ru>
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
from os import remove, makedirs, getenv, stat as file_info, chmod
from os.path import join as path_join, expanduser, exists as pathExists
from shutil import rmtree
from re import findall
from CloudDisk import Cloud

class Test_CloudDisk(unittest.TestCase):
  path = expanduser('~/yd_')
  w_path = path_join(path, '.yd')
  makedirs(w_path, exist_ok=True)
  cloud = Cloud(getenv('API_TOKEN') if getenv('CIRCLE_ENV') == 'test' else
                findall(r'API_TOKEN: (.*)', open('OAuth.info', 'rt').read())[0].strip(),
                path, w_path)

  def test_CDisk00_list(self):
    l = self.cloud.task('list')
    self.assertTrue(str(type(l)) == "<class 'generator'>")
    cnt = 0
    for stat, res in l:
      cnt += 1
    self.assertTrue(cnt > 0)
    self.assertIs(type(res), dict)
    self.assertTrue(res['path'].startswith(expanduser('~/yd_')))

  def test_CDisk10_mkdir(self):
    p = path_join(self.path, 'testdir')
    makedirs(p, exist_ok=True)
    stat, res = self.cloud.task('mkdir', p)
    self.assertTrue(stat)
    self.assertTrue(res == ('mkdir', 'testdir'))
    self.assertTrue(self.cloud.h_data.get(p))
    # create the same new folder again
    stat, res = self.cloud.task('mkdir', p)
    self.assertTrue(stat)    # this error should be ignored
    self.assertTrue(res == ('mkdir', 'testdir'))
    # try to create new folder within non-existing folder
    stat, res = self.cloud.task('mkdir', path_join(self.path, 'not_existing_dir/bla-bla/dir'))
    self.assertFalse(stat)
    self.assertTrue(res[:2] == ('mkdir', 'not_existing_dir/bla-bla/dir'))
    self.assertIs(type(res[-1]), dict)

  def test_CDisk20_move(self):
    # move from existing folder 'testdir' to non-existing folder 'newtestdir'
    p = path_join(self.path, 'testdir')
    p1 = path_join(self.path, 'newtestdir')
    makedirs(p1, exist_ok=True)
    stat, res = self.cloud.task('move', p1, p)
    self.assertTrue(stat)
    self.assertTrue(res == ('move', 'newtestdir', 'testdir'))
    self.assertTrue(self.cloud.h_data.get(p1))
    self.assertFalse(self.cloud.h_data.get(p))
    # try to move existing folder to non-existing folder
    stat, res = self.cloud.task('move', path_join(self.path, 'not_existing_dir/bla-bla/dir'), 'newtestdir')
    self.assertFalse(stat)
    self.assertTrue(res[:2] == ('move', 'not_existing_dir/bla-bla/dir'))
    self.assertIs(type(res[-1]), dict)
    # try to move from non-existing folder to non-existing one
    stat, res = self.cloud.task('move', path_join(self.path, 'not_existing_dir/bla-bla/dir'), 'testdir', )
    self.assertFalse(stat)
    self.assertTrue(res[:2] == ('move', 'not_existing_dir/bla-bla/dir'))
    self.assertIs(type(res[-1]), dict)

  def test_CDisk30_del(self):
    # remove existing folder
    p = path_join(self.path, 'testdir')
    p1 = path_join(self.path, 'newtestdir')
    stat, res = self.cloud.task('del', p1)
    self.assertTrue(stat)
    self.assertTrue(res == ('del', 'newtestdir'))
    self.assertFalse(self.cloud.h_data.get(p1))
    # remove non-existing folder
    stat, res = self.cloud.task('del', path_join(self.path, 'not_existing_dir/bla-bla'))
    self.assertFalse(stat)
    self.assertTrue(res[:2] == ('del', 'not_existing_dir/bla-bla'))
    self.assertIs(type(res[-1]), dict)
    rmtree(p)
    rmtree(p1)

  def test_CDisk40_up(self):
    p = path_join(self.path, 'testfile')
    with open(p, 'wt') as f:
      f.write('test test file file ' * 20)
    stat, res = self.cloud.task('up', p)
    self.assertTrue(stat)
    self.assertTrue(res == ('up', 'testfile'))
    self.assertTrue(self.cloud.h_data.get(p))

  def test_CDisk50_down(self):
    p = path_join(self.path, 'testfile')
    remove(p)
    self.cloud.h_data.pop(p, None)
    stat, res = self.cloud.task('down', p)
    self.assertTrue(stat)
    self.assertTrue(res == ('down', 'testfile'))
    self.assertTrue(self.cloud.h_data.get(p))

  def test_CDisk60_modeSet(self):
    p = path_join(self.path, 'testfile')
    chmod(p, 0o100640)
    stat, res = self.cloud.task('setm', p)
    self.assertTrue(stat)
    self.assertTrue(res == ('setm', 'testfile'))

  def test_CDisk70_modeGet(self):
    p = path_join(self.path, 'testfile')
    chmod(p, 0o100666)
    stat, res = self.cloud.task('getm', p)
    self.assertTrue(stat)
    self.assertTrue(res == ('getm', 'testfile'))
    self.assertTrue(file_info(p).st_mode == 0o100640)

  def test_CDisk80_res(self):
    p = path_join(self.path, 'testfile')
    stat, res = self.cloud.task('res', p)
    self.assertTrue(stat)
    self.assertIs(type(res), dict)

  def test_CDisk99_clean(self):
    p = path_join(self.path, 'testfile')
    remove(p)
    self.cloud.task('del', p)
    rmtree(self.path)


if __name__ == '__main__':

  unittest.main()
