#!/usr/bin/env python3
#
#  yml-config.py
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
from os.path import expanduser
from logging import info, error, debug, critical, warning
from yaml import load as yload, dump as ydump

class Config(dict):
  ''' General purpose configuration class.
      The value of the config (dict) corresponds to the configuration file where config value is
      saved in JSON format.

      Methods:

        config = Config(filePath) - creates new config object and loads it from the file.

          Automatic file loading can be disabled via False value in the optional parameter 'load'.

        config.append(dictOfValues) - add values from dictOfValues to config object.

        config.erase() - clear config object.

        status = config.load(filePath) - loads the config object from file. Returns True on success.

        status = config.save(filePath) - saves the config into the file. Returns True on success.

          Returned value from load and save is the status of operation: True in case of success
          and False in case of any failure.

          Parameter filePath is optional for load and save methods, if it is missed then
          the filePath which was passed to the constructor is used.

      The configuration values can be accessed by any method of dict type. For example:

        config[key] - returns the value of key or raises Exception if key not in config

        config.get(key, [default]) - returns the value of key if key exists otherway it returns
           default on None if no default provided.

        config.setdefault(key, default) returns result similar to get methd but in additional
           it sets the key as the default value it it was not defined before.

        del config[key] - removes key: value pair from the config object

        config.pop(key) - returns the value of key and removes the key:value pair from config object

        config[key] = value - sets the value for key
        ...


      Properties:

        config.loaded - True when configuration object is loaded from file. False == not loaded.

        config.changed - Indicator of changes in the object that are not yet saved to the file.
                         Application can use it for tracing of changes to avoid unnecessary
                         save operations. Within the class this flag is cleared (set to False)
                         after successful save or load and it set to True after append or clear.
  '''
  def __init__(self, filePath, load=True):
    self._filePath = expanduser(filePath)
    self.changed = False
    if load:
      self.load()
    else:
      self.loaded = False

  def append(self, dictVal):
    if type(dictVal) is dict:
      self.update(dictVal)
      self.changed = True

  def load(self, filePath=None):
    self._filePath = expanduser(filePath or self._filePath)
    try:
      with open(self._filePath, 'rt') as f:
        self.append(yload(f))
      self.changed = False
      self.loaded = True
      ok = True
    except:
      warning("File %s can't be read" % self._filePath)
      self.loaded = False
      ok = False
    return ok

  def save(self, filePath=None):
    self._filePath = expanduser(filePath or self._filePath)
    try:
      with open(self._filePath, 'wt') as f:
        ydump(self.copy(), f)
      self.changed = False
      return True
    except:
      warning("File %s can't be written" % self._filePath)
      return False

  def erase(self):
    if self != dict():
      self.clear()
      self.changed = True
