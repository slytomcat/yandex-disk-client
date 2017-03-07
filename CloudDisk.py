#!/usr/bin/env python3
#
# Yandex.disk client engine
#
#  Copyright 2016,2017 Sly_tom_cat <slytomcat@mail.ru>
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
#  along with this program. If not, see <http://www.gnu.org/licenses/>.

from os import stat as file_info, chmod
from os.path import join as path_join, relpath, exists as pathExists
from Cloud import Cloud as _Cloud
from jconfig import Config
from tempfile import NamedTemporaryFile as tempFile
from shutil import move as fileMove
from datetime import datetime
from logging import debug, info, warning, error, critical

class Cloud(_Cloud):
  '''
    Redefined cloud class for implement application level logic
    - all paths in parameters are absolute paths only
    - download/upload have only 1 parameter - absolute path of file
    - getList converted to generator that yields individual file
    - download is performed through the temporary file
    - upload stores uid, gid, mode of file in custom_properties
    - download restores uid, gid, mode from custom_properties of file
    - history data updates according to the success operations

    The task method can be called with following parameters:
    'list' - returns generator that yields all cloud files individually
    'prop', path - returns path properties
    'getm', path - returns cloud file access mode (previously stored)
    'setm', path - stores local access mode to cloud
    'down', path - downloads corresponding cloud file to local path
    'up', path   - uploads local file to corresponding cloud file
      and with other commands of original cloud class but all paths are full local paths.
  '''

  def __init__(self, token, path, work_dir):
    self.h_data = Config(path_join(work_dir, 'hist.data'))  # History data {path: lastModifiedDateTime}
    self.path = path
    self.work_dir = work_dir
    super().__init__(token)

  def task(self, cmd, *args, **kwargs):
    func = {'list' : self._getList,
            'res'  : self._getResult,
            'mkdir': self._mkDir,
            'del'  : self._delete,
            'move' : self._move,
            'down' : self._download,
            'up'   : self._upload,
            'getm' : self._getMode,
            'setm' : self._setMode}.get(cmd)
    if func is None:
      return super().task(cmd, *args, **kwargs)
    else:
      return func(cmd, *args, **kwargs)

  def _reformat(self, item):
    item['path'] = path_join(self.path, item['path'])
    item['modified'] = int(datetime.strptime(item['modified'].replace(':', ''),
                                             '%Y-%m-%dT%H%M%S%z').timestamp())

  def _getList(self, cmd, chunk=None):  # getList is a generator that yields individual file
    offset = 0
    chunk = chunk or 30
    while True:
      status, result = super().task(cmd, path, chunk, offset)
      if status:
        l = len(result)
        if l:
          for i in result:
            self._reformat(i)
            yield True, i
          if l < chunk:
            break
          else:
            offset += chunk
        else:
          break

  def _getResource(self, cmd, path):
    status, result = super().task(cmd, relpath(path, start=self.path))
    if status:
      self._reformat(result)
    return status, result

  def _getMode(self, cmd, path):
    st, f_res = self._getResource('res', path)
    if st:
      props = f_res.get("custom_properties")
      if props is not None:
        return props.get("mode")
    return None

  def _setMode(self, cmd, path):
    return self._r_setMode('prop', relpath(path, start=self.path), file_info(path).st_mode)

  def _r_setMode(self, cmd, r_path, mode):
    return super().task('prop', r_path, mode=mode)

  def _download(self, cmd, path):    # download via temporary file to make it in transaction manner
    with tempFile(suffix='.temp', delete=False, dir=self.work_dir) as f:
      temp = f.name
    r_path = relpath(path, start=self.path)
    status, res = super().task(cmd, r_path, temp)
    if status:
      try:
        fileMove(temp, path)
        self.h_data[path] = int(file_info(path).st_mtime)
        chmod(path, self._getMode(path))
      except:
        status = False
    return status, res

  def _upload(self, cmd, path):
    r_path = relpath(path, start=self.path)
    status, res = super().task(cmd, r_path, path)
    if status and pathExists(path):
      fst = file_info(path)
      self.h_data[path] = int(fst.st_mtime)
      self._r_setMode(r_path, fst.st_mode)
    return status, res

  def _delete(self, cmd, path):
    status, res = super().task(cmd, relpath(path, start=self.path))
    if status:
      # remove all subdirectories and files in the path if path is a directory or
      # remove just the path if it is a file
      to_remove = [p for p in iter(self.h_data) if p.startswith(path)]
      for p in to_remove:
        self.h_data.pop(p, None)
    return status, res

  def _move(self, cmd, pathto, pathfrom):
    status, res = super().task(cmd, relpath(pathto, start=self.path),
                               relpath(pathfrom, start=self.path))
    if status:
      # update history date too
      p = self.h_data.pop(pathfrom, None)
      if p is not None:
        self.h_data[pathto] = p
      else:
        if pathExists(pathto):
          self.h_data[pathto] = int(file_info(pathto).st_mtime)
    return status, res

  def _mkDir(self, cmd, path):
    status, res = super().task(cmd, relpath(path, start=self.path))
    if status:
      self.h_data[path] = int(file_info(path).st_mtime)
    return status, res


