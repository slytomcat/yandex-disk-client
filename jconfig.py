#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  jconfig.py
#
#  Copyright 2016 Sly_tom_cat <slytomcat@mail.ru>
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
from json import dump as jdump, load as jload

class Config(dict):
  ''' General purpose configuration class.
      The value of the config (dict) corresponds to the configuration file where config value is
      saved in JSON format.

      Methods:

        config = Config(filePath) - creates new config object and loads it from the file.

          Automatic file loading can be disabled via False value in the optional parameter 'load'.

        config.append(dictValue) - add values from dictValue to config object.

        status = config.load(filePath) - loads the config object from file.

        status = config.save(filePath) - saves the config into the file.

          Returned value from load and save is the status of operation: True in case of sucsess
          and False in case of any failure.

          Parameter filePath is optional for load and save methods, if it is missed then
          the filePath which was passed to the constructor is used.

      Properties:

        config.loaded - True when config object is loaded from file. False - object is not loaded.

        config.changed - Indicator of changes in the object that are not yet saved to the file.
                         Application can use it for tracing of changes to avoid unnecessary
                         save operations. Within the class this flag is cleared (set to False)
                         after successful save or load and it is raised (set to True) after append.
  '''
  def __init__(self, filePath, load=True):
    self._filePath = filePath
    self.changed = False
    if load:
      self.load()
    else:
      self.loaded = False

  def load(self, filePath=None):
    if filePath is not None:
      self._filePath = filePath
    try:
      with open(self._filePath, 'rt') as f:
        self.append(jload(f))
      self.changed = False
      self.loaded = True
      ok = True
    except:
      self.loaded = False
      ok = False
    return ok

  def save(self, filePath=None):
    if filePath is not None:
      self._filePath = filePath
    try:
      with open(self._filePath, 'wt') as f:
        jdump(self, f, indent=2)
      self.changed = False
      ok = True
    except:
      ok = False
    return ok

  def append(self, dictVal):
    if dictVal:
      for key, val in dictVal.items():
        self[key] = val
      self.changed = True

if __name__ == '__main__':
  # tests
  from os import remove
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
  path = 'cfg.cfg'
  try:
    remove('cfg.cfg')
  except:
    pass

  config = Config(path, load=False)
  res = []
  res.append(len(config) == 0)
  print('len of not loaded config is 0              :', res[-1])
  res.append(config.loaded == False)
  print('config.loaded of not loaded config is False:', res[-1])
  config.append(defConf)
  res.append(len(config) == 2)
  print('len of appended config is 2                :', res[-1])
  res.append(config.changed == True)
  print('config.cannged of appended config is True  :', res[-1])
  if config.changed:
    config.save()
  res.append(config.changed == False)
  print('config.cannged of saved config is False    :', res[-1])
  newConfig = Config(path)
  res.append(newConfig.loaded == True)
  print('config.loaded of loaded config is True     :', res[-1])
  res.append((config == newConfig) == True)
  print('comparison test passed                     :', res[-1])
  remove('cfg.cfg')
  for stat in res:
    if not stat:
      raise NameError('Something wrong with it.')
