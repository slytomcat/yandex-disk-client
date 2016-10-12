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
                      IN_MODIFY, IN_DELETE, IN_CREATE, IN_MOVED_FROM, IN_MOVED_TO
from threading import Thread
from queue import Queue
from concurrent.futures import ThreadPoolExecutor

class Disk(object):
  '''High-level Yandex.disk client interface
  '''
  def __init__(self, user):
    self.user = user
    self.connected = False
    self.watch = self._PathWatcher(self.user['path'].replace('~', osUserHome))
    self.executor = ThreadPoolExecutor(3) # number of working threads
    self.handler = Thread(target=self._eventHandler)
    self.handler.start()
    self.changed({'init'})
    if self.user.setdefault('start', True):
      self.connect()

  def exit(self):
    self.watch.stop()
    if self.connected:
      self.stop()
    self.executor.shutdown(wait=True)

  def _eventHandler(self):
    def moveCloudObj(event):
      print('move from %s, to %s'% (event.pathname, event.path), event)
    def updateCloudObj(event):
      print('update %s' % event.pathname, event)
    def deleteCloudObj(event):
      print('delete %s' % event.pathname, event)
    def createCloudObj(event):
      print('new %s' % event.pathname, event)

    while True:
      event = self.watch.get()
      if event.mask & (IN_MOVED_TO | IN_MOVED_FROM):
        try:
          event2 = self.watch.get(timeout=0.01)
          if event.cookie == event2.cookie:
            event.path = event2.pathname
            self.executor.submit(moveCloudObj, event)
        except:
          if event.mask & IN_MOVED_TO:
            self.executor.submit(createCloudObj, event)
          else:
            self.executor.submit(deleteCloudObj, event)
      elif event.mask & (IN_CREATE):
        self.executor.submit(createCloudObj, event)
      elif event.mask & (IN_DELETE):
        self.executor.submit(deleteCloudObj, event)
      elif event.mask & IN_MODIFY:
        self.executor.submit(updateCloudObj, event)


  class _PathWatcher(Queue):               # iNotify watcher for directory
    '''
    iNotify watcher object for monitor of changes in directory.
    '''
    def __init__(self, path):

      class _EH(ProcessEvent):
        def process_default(self, event):
          _handleEvent(event)

      Queue.__init__(self)
      self._path = path
      _handleEvent = self.put
      self._watchMngr = WatchManager()
      self._iNotifier = ThreadedNotifier(self._watchMngr, _EH())

    def start(self):
      # Add watch and start watching
      self._watch = self._watchMngr.add_watch(self._path,
                                              IN_MODIFY|IN_DELETE|IN_CREATE|
                                              IN_MOVED_FROM|IN_MOVED_TO,
                                              rec=True)
      self._iNotifier.start()

    def stop(self):
      # Remove watch and stop watching
      self._watchMngr.rm_watch(self._watch.values())
      self._iNotifier.stop()


  def connect(self):
    '''Activate synchronizations with Yandex.disk'''
    if not self.connected:
      self.watch.start()

      #openListenSocket(user[auth])

      self.connected = True
      self.changed({'stat'})

  def disconnect(self):
    '''Deactivate synchronizations with Yandex.disk'''
    if self.connected:
      self.watch.stop()

      #closeListenSocket(user[auth])

      self.connected = False
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

  appName = 'yd-client'
  osUserHome = getenv("HOME")
  confHome = osUserHome + '/.config/' + appName
  config = Config(confHome + '/client.conf')
  if not config.loaded:
    makedirs(confHome)
    config.changed = True
  config.setdefault('type', 'std')
  config.setdefault('disks', {})
  if config.changed:
    config.save()
  print(config)
  # Setup localization
  translation(appName, '/usr/share/locale', fallback=True).install()

  disks = []
  for user in config['disks'].values():
    disks.append(Disk(user))
  if not disks:
    appExit(_('No accounts configred'))
  while True:
    sleep(3)
    print(disks[0].status(), end='\r')
