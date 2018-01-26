#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  interactive.py
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
#  along with this program. If not, see <http://www.gnu.org/licenses/>.

from Disk import Disk
from jconfig import Config
from OAuth import getToken, getLogin
from sys import exit as sysExit
from gettext import translation
from signal import signal, SIGTERM, SIGINT
from logging import basicConfig as logConfig
from os.path import join as path_join, expanduser, exists as pathExists
from os import makedirs

def appExit(msg=None):
  for disk in disks:
    disk.exit()
  sysExit(msg)

''' Interactive execution code
'''

if __name__ == '__main__':
  logConfig(level=10, format='%(asctime)s %(levelname)s %(message)s')
  appName = 'yd-client'
  # read or make new configuration file
  confHome = expanduser(path_join('~', '.config', appName))
  config = Config(path_join(confHome, 'client.conf'))
  if not config.loaded:
    makedirs(confHome, exist_ok=True)
    config.changed = True
  config.setdefault('type', 'std')
  config.setdefault('disks', {})
  if config.changed:
    config.save()
  # Setup localization
  translation(appName, '/usr/share/locale', fallback=True).install()

  disks = []
  while True:
    for user in config['disks'].values():
      disks.append(Disk(user))
    if disks:
      break
    else:
      from OAuth import getToken, getLogin
      print(_('No accounts configured'))
      if input(_('Do you want to configure new account (Y/n):')).lower() not in ('', 'y'):
        appExit(_('Exit.'))
      else:
        while True:
          path = ''
          while not pathExists(path):
            path = input(_('Enter the path to local folder '
                           'which will by synchronized with cloud disk. (Default: ~/YandexDisk):'))
            if not path:
              path = '~/YandexDisk'
            path = expanduser(path)
            if not pathExists(path):
              try:
                makedirs(path_join(path, dataFolder), exist_ok=True)
              except:
                print('Error: Incorrect folder path specified (no access or wrong path name).')
                continue
          token = getToken('389b4420fc6e4f509cda3b533ca0f3fd', '5145f7a99e7943c28659d769752f6dae')
          login = getLogin(token)
          config['disks'][login] = {'login': login, 'auth': token, 'path': path, 'start': True,
                                    'ro': False, 'ow': False, 'exclude': []}
          config.save()
          if input(_('Do you want to and one more account (y/N):')).lower() in ('', 'n'):
            break

  # main thread final activity

  signal(SIGTERM, lambda _signo, _stack_frame: appExit('Killed'))
  signal(SIGINT, lambda _signo, _stack_frame: appExit('CTRL-C Pressed'))

  msg = ('Commands:\n с - connect\n d - disconnect\n s - get status\n t - clear trash\n'
         ' f - full sync\n e - exit\n ')
  print(msg, 'connected:', disks[0].connected())
  while True:
    cmd = input()
    if cmd == 'd':
      disks[0].disconnect()
    elif cmd == 'c':
      disks[0].connect()
    elif cmd == 't':
      disks[0].trash()
    elif cmd == 's':
      print(disks[0].getStatus())
    elif cmd == 'f':
      disks[0].fullSync()
    elif cmd == 'e':
      appExit()
    print(msg, 'connected:', disks[0].connected())
