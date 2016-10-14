# -*- coding: utf-8 -*-
#
# Yandex.disk client engine
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
#  along with this program. If not, see <http://www.gnu.org/licenses/>.

from os import remove, makedirs, getpid, geteuid, getenv
from pyinotify import ProcessEvent, WatchManager, Notifier, ThreadedNotifier,\
                      IN_MODIFY, IN_DELETE, IN_CREATE, IN_MOVED_FROM, IN_MOVED_TO, IN_ATTRIB
from threading import Thread, Event
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
from Cloud import Cloud

class Disk(object):
  '''High-level Yandex.disk client interface.
     It can have following statuses:
      - busy - when some activities are currntly performed
      - idle - no activities are currntly performed
      - none - not connected
      - no_net - network connection is not available
      - error - some error
  '''
  def __init__(self, user):
    self.user = user
    self.status = 'none'
    self.cloud = Cloud(self.user['auth'])
    self.path = self.user['path'].replace('~', osUserHome)
    self.watch = self._PathWatcher(self.path)
    self.executor = ThreadPoolExecutor()   # set number of working threads automatically
    self.shutdown = Event()
    self.handler = Thread(target=self._eventHandler)
    self.handler.start()
    self.changed({'init'})
    if self.user.setdefault('start', True):
      self.connect()

  def exit(self):
    if self.status != 'none':
      self.disconnect()
    self.shutdown.set()
    self.executor.shutdown(wait=True)

  def fullSync(self):
    '''
    cSet = {for item.pathname in self.cloud.getFullList():}
    lSet = {} # need recurcive list of local folder
    for path in cSet - lSet:
      ft = self.executor.submit(self.cloud.download, (path, self.path + '/' + path))
      ft.add_done_callback(taskCB)
    for path in lSetc - cSet:
      ft = self.executor.submit(self.cloud.upload, (self.path + '/' + path, path))
      ft.add_done_callback(taskCB)
    '''
    pass

  def _eventHandler(self):

    def new(event):
      if event.dir:
        submit(self.cloud.mkDir, (localpath(event.pathname),))
      else:
        submit(self.cloud.upload,
               (event.pathname, localpath(event.pathname)))

    def moved(event):
      if event.mask & IN_MOVED_TO:  # moved in = new
        new(event)
      else:  # moved out = deleted
        submit(self.cloud.delete, (localpath(event.pathname),))

    def taskCB(ft):
      if ft.done():
        print('done:', ft.result())
        #e = ft.exception()
        #if e is not None:
        #  print(e)

    def submit(task, args):
      ft = self.executor.submit(task, *args)
      ft.add_done_callback(taskCB)

    def localpath(path):
      return path[len(self.path)+1:]

    while not self.shutdown.is_set():
      event = self.watch.get()
      print(event)
      if event.mask & (IN_MOVED_FROM | IN_MOVED_TO):
        try:
          event2 = self.watch.get(timeout=0.01)
          print(event2)
          if event.cookie == event2.cookie:
            submit(self.cloud.move, (localpath(event.pathname),
                                     localpath(event2.pathname)))
          else:
            moved(event)
            moved(event2)
        except:
          moved(event)
      elif event.mask & (IN_CREATE):
        new(event)
      elif event.mask & (IN_DELETE):
        submit(self.cloud.delete, (localpath(event.pathname),))
      elif event.mask & IN_MODIFY:
        submit(self.cloud.upload, (event.pathname, localpath(event.pathname)))
      elif event.mask & IN_ATTRIB:
        submit(self.cloud.upload, (event.pathname, localpath(event.pathname)))


  class _PathWatcher(Queue):               # iNotify watcher for directory
    '''
    iNotify watcher object for monitor of changes in directory.
    '''
    FLAGS = IN_MODIFY|IN_DELETE|IN_CREATE|IN_MOVED_FROM|IN_MOVED_TO|IN_ATTRIB
    def __init__(self, path):

      class _EH(ProcessEvent):
        def process_default(self, event):
          _handleEvent(event)

      Queue.__init__(self)
      self._path = path + '/'
      _handleEvent = self.put
      self._watchMngr = WatchManager()
      self._iNotifier = ThreadedNotifier(self._watchMngr, _EH())

    def start(self):
      # Add watch and start watching
      self._watch = self._watchMngr.add_watch(self._path, self.FLAGS, rec=True)
      self._iNotifier.start()

    def stop(self):
      # Remove watch and stop watching
      self._watchMngr.rm_watch(self._watch.values())
      self._iNotifier.stop()

  def connect(self):
    '''Activate synchronizations with Yandex.disk'''
    if self.status == 'none':
      self.watch.start()

      #openListenSocket(user[auth])

      self.status = 'idle'
      self.changed({'stat'})
      self.fullSync()

  def disconnect(self):
    '''Deactivate synchronizations with Yandex.disk'''
    if self.status != 'none':
      self.watch.stop()

      #closeListenSocket(user[auth])

      self.status = 'none'
      self.changed({'stat'})


  def status(self):
    '''Return the current synchronization status'''
    return  ''.join(['login: %s  ' % self.user['login'],
                     'path: %s  ' % self.user['path'],
                     'status: %s  ' % (('' if self.connected else 'not') + 'connected'),
                     ''])

  def changed(self, change={}):
    '''Redefined class method for catch the client status changes.
       It has change parameter that is the set of changed aspects of the client.
       Client changed aspects can be:
        - 'status'    when synchronization status changed
        - 'progress'  when synchronization progress changed
        - 'last'      when last synchronized items changed
        - 'props'     when user properties changed (total disk size or used space)
        - 'init'      when synchronization initialized
    '''
    print(change)

def appExit(msg=None):
  from sys import exit as sysExit

  for disk in disks:
    disk.exit()
  sysExit(msg)

if __name__ == '__main__':
  from jconfig import Config
  from gettext import translation
  from time import sleep
  from OAuth import getToken, getLogin
  from os.path import exists as pathExists, relpath as relativePath
  from re import findall

  appName = 'yd-client'
  osUserHome = getenv("HOME")
  confHome = osUserHome + '/.config/' + appName
  config = Config(confHome + '/client.conf')
  if not config.loaded:
    try:
      makedirs(confHome)
    except FileExistsError:
      pass
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
      fullpath = user['path'].replace('~', osUserHome)
      if not pathExists(fullpath):
        try:
          makedirs(fullpath)
        except:
          appExit(_("Error: Can't access the local folder %s" % fullpath))
      disks.append(Disk(user))
    if disks:
      break
    else:
      print(_('No accounts configured'))
      if input(_('Do you want to configure new account (Y/n):')).lower() not in ('', 'y'):
        appExit(_('Exit.'))
      else:
        with open('OAuth.info', 'rt') as f:
          buf = f.read()
        fullpath = ''
        while not pathExists(fullpath):
          path = input('Enter the path to local folder '
                       'which will by synchronized with cloud disk. (Default: ~/Yandex.Disk):')
          fullpath = path.replace('~', osUserHome)
          if not pathExists(fullpath):
            try:
              makedirs(fullpath)
            except:
              print('Error: Incorrect path specified.')
        token = getToken(findall(r'AppID: (.*)', buf)[0].strip(),
                         findall(r'AppSecret: (.*)', buf)[0].strip())
        login = getLogin(token)
        config['disks'][login] = {'login': login, 'auth': token, 'path': path, 'start': True,
                                  'ro': False, 'ow': False, 'exclude': []}
        config.save()

  while True:
    sleep(3)
    #print(disks[0].status(), end='\r')
