#!/usr/bin/env python3
#
#  test_Cloud.py
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
from re import findall
from os import remove, getenv
from Cloud import Cloud

class test_Cloud(unittest.TestCase):
  '''Local test token have to be store_requestd in file 'OAuth.info' with following format:
     CLOUD_TOKEN/API_TOKEN:  <OAuth token>
     CircleCi token is in the environment variable CLOUD_TOKEN/API_TOKEN
  '''
  cloud = Cloud(getenv('API_TOKEN') if getenv('CIRCLE_ENV') == 'test' else
                findall(r'API_TOKEN: (.*)', open('OAuth.info', 'rt').read())[0].strip())

  def test_Cloud00_DiskInfo(self):
    stat, res = self.cloud.task('info')
    self.assertTrue(stat)
    self.assertIs(type(res), dict)

  def test_Cloud10_Dir_1Create(self):
    # create new folder
    stat, res = self.cloud.task('mkdir', 'testdir')
    self.assertTrue(stat)
    self.assertTrue(res == ('mkdir', 'testdir'))
    # create the same new folder again
    stat, res = self.cloud.task('mkdir', 'testdir')
    self.assertTrue(stat)    # this error should be ignored
    self.assertTrue(res == ('mkdir', 'testdir'))
    # try to create new folder within non-existing folder
    stat, res = self.cloud.task('mkdir', 'not_existing_dir/bla-bla/dir')
    self.assertFalse(stat)
    self.assertTrue(res[:2] == ('mkdir', 'not_existing_dir/bla-bla/dir'))
    self.assertIs(type(res[-1]), dict)

  def test_Cloud10_Dir_2move(self):
    # move from existing folder 'testdir' to non-existing folder 'newtestdir'
    stat, res = self.cloud.task('move', 'newtestdir', 'testdir')
    self.assertTrue(stat)
    self.assertTrue(res == ('move', 'newtestdir', 'testdir'))
    # try to move existing folder to non-existing folder
    stat, res = self.cloud.task('move', 'not_existing_dir/bla-bla', 'newtestdir')
    self.assertFalse(stat)
    self.assertTrue(res[:2] == ('move', 'not_existing_dir/bla-bla'))
    self.assertIs(type(res[-1]), dict)
    # try to move from non-existing folder to non-existing one
    stat, res = self.cloud.task('move', 'not_existing_dir/bla-bla', 'testdir', )
    self.assertFalse(stat)
    self.assertTrue(res[:2] == ('move', 'not_existing_dir/bla-bla'))
    self.assertIs(type(res[-1]), dict)


  def test_Cloud10_Dir_3copy(self):
    # copy from existing folder 'newtestdir' to non-existing folder 'testdir'
    stat, res = self.cloud.task('copy', 'testdir', 'newtestdir')
    self.assertTrue(stat)
    self.assertTrue(res == ('copy', 'testdir', 'newtestdir'))
    # try to copy existing folder to non-existing folder
    stat, res = self.cloud.task('copy', 'not_existing_dir/bla-bla', 'newtestdir')
    self.assertFalse(stat)
    self.assertTrue(res[:2] == ('copy', 'not_existing_dir/bla-bla'))
    self.assertIs(type(res[-1]), dict)
    # try to copy from non-existing folder to non-existing one
    stat, res = self.cloud.task('copy', 'not_existing_dir/bla-bla', 'testdir_1', )
    self.assertFalse(stat)
    self.assertTrue(res[:2] == ('copy', 'not_existing_dir/bla-bla'))
    self.assertIs(type(res[-1]), dict)

  def test_Cloud10_Dir_4del(self):
    # remove existing folder
    stat, res = self.cloud.task('del', 'newtestdir')
    self.assertTrue(stat)
    self.assertTrue(res == ('del', 'newtestdir'))
    # remove another existing folder
    stat, res = self.cloud.task('del', 'testdir')
    self.assertTrue(stat)
    self.assertTrue(res == ('del', 'testdir'))
    # remove non-existing folder
    stat, res = self.cloud.task('del', 'not_existing_dir/bla-bla')
    self.assertFalse(stat)
    self.assertTrue(res[:2] == ('del', 'not_existing_dir/bla-bla'))
    self.assertIs(type(res[-1]), dict)

  def test_Cloud20_bigDir_1copy(self):
    stat, res = self.cloud.task('copy', 'MusicTest', 'Music')
    self.assertTrue(stat)
    self.assertTrue(res == ('copy', 'MusicTest', 'Music'))


  def test_Cloud20_bigDir_2move(self):
    stat, res = self.cloud.task('move', 'MusicTestTest', 'MusicTest')
    self.assertTrue(stat)
    self.assertTrue(res == ('move', 'MusicTestTest', 'MusicTest'))

  def test_Cloud20_bigDir_3delete(self):
    stat, res = self.cloud.task('del', 'MusicTestTest')
    self.assertTrue(stat)
    self.assertTrue(res == ('del', 'MusicTestTest'))


  def test_Cloud30_props_1set(self):
    stat, res = self.cloud.task('prop', 'Sea.jpg', uid=1000, gid=1000, mode=33204)
    self.assertTrue(stat)
    self.assertTrue(res == ('prop', 'Sea.jpg'))

  def test_Cloud30_props_2get(self):
    stat, res = self.cloud.task('res', 'Sea.jpg')
    self.assertTrue(stat)
    self.assertIs(type(res), dict)
    props = res.get("custom_properties")
    self.assertFalse(props is None)
    self.assertEqual(props.get('uid'), 1000)
    self.assertEqual(props.get('gid'), 1000)
    self.assertEqual(props.get('mode'), 33204)

  def test_Cloud40_wrong_res(self):
    stat, res = self.cloud.task('res', 'not_existing_file.bla_bla')
    self.assertIs(type(res), tuple)
    self.assertFalse(stat)
    self.assertTrue(res[:2] == ('res', 'not_existing_file.bla_bla'))
    self.assertIs(type(res[-1]), dict)

  def _trush(self):
    stat, res = self.cloud.task('trash')
    self.assertTrue(stat)
    stat, res = self.cloud.task('info')
    self.assertTrue(stat)
    self.assertEqual(res.get('trash_size'), 0)

  def test_Cloud50_trush(self):
    self._trush()
    self._trush()

  def test_Cloud60_1up(self):
    stat, res = self.cloud.task('up', 'README.md', 'README.md')
    self.assertTrue(stat)

  def test_Cloud60_2down(self):
    stat, res = self.cloud.task('down', 'README.md', '/tmp/README.md')
    self.assertTrue(stat)
    remove('/tmp/README.md')
    self.cloud.task('del', 'README.md')

  def test_Cloud70_last(self):
    stat, res = self.cloud.task('last')
    self.assertTrue(stat)
    self.assertIs(type(res), list)

  def test_Cloud80_list(self):
    stat, res = self.cloud.task('list', 5, 0)
    self.assertTrue(stat)
    self.assertIs(type(res), list)
    self.assertEqual(len(res), 5)

  def test_Cloud80_wrong_list(self):
    stat, res = self.cloud.task('list', 7777777777, 0)
    self.assertFalse(stat)

  def test_Cloud90_wrong_delete(self):
    stat, res = self.cloud.task('del', 'not_existing_file.bla_bla')
    self.assertFalse(stat)

if __name__ == '__main__':
  unittest.main()
