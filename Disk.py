#!/usr/bin/env python3
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

from os import remove, makedirs, getpid, geteuid, getenv, cpu_count, walk, stat as file_info
from os.path import join as path_join, expanduser, relpath, split as path_split
from pyinotify import ProcessEvent, WatchManager, Notifier, ThreadedNotifier, ExcludeFilter,\
                      IN_MODIFY, IN_DELETE, IN_CREATE, IN_MOVED_FROM, IN_MOVED_TO, IN_ATTRIB
from threading import Thread, Event, enumerate
from queue import Queue, Empty
from PoolExecutor import ThreadPoolExecutor
from Cloud import Cloud
from time import time, gmtime, strftime
from hashlib import sha256
from glob import iglob


class Disk(object):
  '''High-level Yandex.disk client interface.
     It can have following statuses:
      - busy - when some activities are currently performed
      - idle - no activities are currently performed
      - none - not connected
      - no_net - network connection is not available
      - error - some error
  '''
  def __init__(self, user):
    self.user = user
    self.path = expanduser(self.user['path'])
    self.cloud = Cloud(self.user['auth'])
    self.executor = ThreadPoolExecutor()
    self.shutdown = False
    self.downloads = set()
    self.error = False
    self.EH = Thread(target=self._eventHandler)
    self.EH.name = 'EventHandler'
    self.watch = self._PathWatcher(self.path,
                                   [path_join(self.path, e) for e in self.user['exclude']])
    self.EH.start()
    #self.listener = XMPPListener('%s\00%s' % (user[login], user[auth]))
    self.prevStatus = 'none'
    self.status = 'none'
    self.progress = ''
    self.CDstatus = dict()
    self.changes = {'init'}
    self.statusEvent = Event()
    self.statusEvent.set()
    self.SW = Thread(target=self._updateCDstatus)
    self.SW.name = 'StatusUpdater'
    self.SW.start()
    if self.user.setdefault('start', True):
      self.connect()

  def _setStatus(self, status):
    if status != self.status:
      self.prevStatus = self.status
      self.status = status
      self.statusEvent.set()

  def updateInfo(self):
    # get disk statistics
    stat, res = self.cloud.getDiskInfo()
    if stat:
      total = res['total_space']
      used = res['used_space']
      trash = res['trash_size']
    else:
      total = '...'
      used = '...'
      trash = '...'
    if self.CDstatus.get('total', False):
      if ((self.CDstatus['used'] != used) or
          (self.CDstatus['trash'] != trash) or
          (self.CDstatus['total'] != total)):
        self.changes.add('prop')
      else:
        self.changes.add('prop')
    self.CDstatus['total'] = total
    self.CDstatus['used'] = used
    self.CDstatus['trash'] = trash
    # get last synchronized list
    stat, res = self.cloud.getLast()
    last = res if stat else []
    if last != self.CDstatus.get('last', None):
      self.changes.add('last')
    self.CDstatus['last'] = last

  def _updateCDstatus(self):
    timeout = None # 1
    stime = time()
    while not self.shutdown:
      #print(timeout)
      self.statusEvent.wait(timeout=timeout)
      #if not self.statusEvent.is_set():
      #  timeout = timeout if timeout > 9 else timeout + 2
      #else:
      #  timeout = 1
      if self.prevStatus != self.status:
        self.changes.add('stat')
        if self.status == 'busy':
          stime = time()
        if self.prevStatus == 'busy':
          print('Finished in %s sec.' % (time() - stime))
          self.updateInfo()
        if self.prevStatus == 'error':
          self.fullSync()
      #if self.prevStatus == 'none':
      self.updateInfo()
      if self.changes:
        self.changed(self.changes)
      self.changes = set()
      self.statusEvent.clear()

  def getStatus(self):
    '''Return the current disk status
       The returned status dict contain the following items:
         { 'status': <current status (one of: 'none', 'idle', 'busy', 'error', 'no_net')>,
           'progress': <current activity progress (it si actual only for 'busy' status)>,
           'login': <Cloud disk user login>
           'total': <total cloud disk size>,
           'used': <used cloud disk space>,
           'trash': <trash size>,
           'path': <synchronized local path>,
           'last': <up to 10 last synchronized items>
         }
    '''
    self.updateInfo()
    return {'status': self.status,
            'progress': self.progress,
            'login': self.user['login'],
            'total': self.CDstatus['total'],
            'used': self.CDstatus['used'],
            'trash': self.CDstatus['trash'],
            'last': self.CDstatus['last'],
            'path': self.user['path']
           }

  def changed(self, change={}):
    '''Class method for catch the client status changes.
       It can be redefined in super class to organize the change event flow to the recipient.
       It has change parameter that is the set of change events set of the client.
       Client changed event can be:
        - 'status'    when synchronization status changed
        - 'progress'  when synchronization progress changed
        - 'last'      when last synchronized items changed
        - 'prop'      when user properties changed (total disk size or used space)
        - 'init'      when synchronization initialized
    '''
    # log status change as debug message
    print('status: %s  path: %s  event: %s' % (self.status, self.user['path'], str(change)))
    for e in change:
      if e == 'last':
        print(self.CDstatus['last'])
      elif e == 'prop':
        s = ''
        for t in ['total', 'used', 'trash']:
          s += '%s: %s ' % (t, self.CDstatus[t])
        print(s)

  def _submit(self, task, args):

    def taskCB(ft):
      res = ft.result()
      unf = self.executor.unfinished()
      print('Done: %s, %d unfinished' % (str(res), unf))
      stat, path = res
      if path:
        # Remove downloaded file from downloads
        self.downloads -= {path}
      if not stat and self.status != 'error':
        self._setStatus('error')
      if unf == 0:
        self._setStatus('idle')

    ft = self.executor.submit(task, *args)
    ft.add_done_callback(taskCB)
    if self.status != 'busy':
      self._setStatus('busy')
    print('submit %s %s' % (findall(r'Cloud\.\w*', str(task))[0] , str(args)))

  def fullSync(self):
    ignore = set(self.watch.exclude)  # set of files that shouldn't be synced or alredy in sync
    # colud - local -> download from cloud ... or  delete from cloud???
    # (cloud & local) and hashes are equal = ignore
    # (cloud & local) and hashes not equal -> decide upload/download depending on the update
    # time... or it is a conflict ???
    for stat, items in self.cloud.getFullList(chunk=20):
      if stat:
        for i in items:
          path = path_join(self.path, i['path'])
          if path in ignore:
            continue
          p, _ = path_split(path)
          if pathExists(path):
            if i['type'] == 'file':
              try:
                with open(path, 'rb') as f:
                  hh = sha256(f.read()).hexdigest()
              except:
                hh = ''
              if hh == i['sha256']:
                # Cloud and local hashes are equal
                ignore.add(path)
                ignore.add(p)
                continue
              else:
                # Need to decide what to do: upload, download, or it is conflict.
                # In order to find the conflict the 'modified' date-time
                # from previous upload/download have to be stored somewhere.... Where to store it???
                # Without this info the only two solutions are possible:
                # - download if the cloud file newer than the local, or
                # - upload if the local file newer than the cloud file.
                c_t = i['modified'][:19]    # remove time zone as it is always GMT (+00:00)
                f_st = file_info(path)      # follow symlink by default ???
                l_t = strftime('%Y-%m-%dT%H:%M:%S', gmtime(f_st.st_mtime))
                if l_t > c_t:
                  # upload (as file exists the dir exists too - no need to create dir in cloud)
                  self._submit(self.cloud.upload, (path, i['path']))
                  ignore.add(path)
                  ignore.add(p)
                  continue
                #else:  # download - it is performed below
            else:  # it is existing directory
              # there is nothing to check for directories
              ignore.add(path)
              continue
          # the file has to be downloaded or.... deleted from the cloud when local file
          # was deleted and this deletion was not catched by active client (client was not
          # connected to cloud). But in order to have a reasons for such decision the
          # history info is required.
          if i['type'] == 'file':
            if not pathExists(p):
              self.downloads.add(p)             # store new dir in dowloads to avoud upload
              makedirs(p, exist_ok=True)
            ignore.add(p)
            self.downloads.add(path)            # store downloaded file in dowloads to avoud upload
            self._submit(self.cloud.download, (i['path'], path))
            ignore.add(path)
          else:                                 # directory not exists
            self.downloads.add(path)            # store new dir in dowloads to avoud upload
            makedirs(path, exist_ok=True)
            ignore.add(path)
    # (local - ignored) -> upload to cloud
    for root, dirs, files in walk(self.path):
      for d in dirs:
        d = path_join(root, d)
        if d not in ignore:
          # directory have to be created before start of uploading a file in it
          # do it inline as it rather fast operation
          s, r = self.cloud.mkDir(relpath(d, start=self.path))
          print('done inline', s, r)
      for f in files:
        f = path_join(root, f)
        if f not in ignore:
          self._submit(self.cloud.upload, (f, relpath(f, start=self.path)))

  def _eventHandler(self):

    def new(event):
      if event.dir:
        if event.pathname in self.downloads:
          # this dir was created localy within fullSync it ia already exists in the cloud
          self.downloads -= {event.pathname}
        else:
          # create newly created local dir in the cloud
          self._submit(self.cloud.mkDir, (event.path,))
      else:   # it is file
        # do not start upload for downloading file
        if event.pathname not in self.downloads:
          self._submit(self.cloud.upload, (event.pathname, event.path))

    def moved(event):
      if event.mask & IN_MOVED_TO:  # moved in = new
        new(event)
      else:  # moved out = deleted
        self._submit(self.cloud.delete, (event.path,))

    IN_MOVED = IN_MOVED_FROM | IN_MOVED_TO
    while not self.shutdown:
      event = self.watch.get()
      if event is not None:
        # make relative path from full path from event.pathname
        event.path = relpath(event.pathname, start=self.path)
        ''' event.pathname - full path
            event.path - relative path
        '''
        while event.mask & IN_MOVED:
          try:
            event2 = self.watch.get(timeout=0.1)
            event2.path = relpath(event2.pathname, start=self.path)
            try:
              cookie = event2.cookie
            except AttributeError:
              cookie = ''
            if event.cookie == cookie:
              # greate! we've found the move operatin (file moved within the synced path)
              self._submit(self.cloud.move, (event.path, event2.path))
              break
            else:
              moved(event)
              event = event2
              if not (event.mask & IN_MOVED):
                break     # treat it as not IN_MOVE event
          except Empty:
            moved(event)
            break
        # treat not IN_MOVE event
        if event.mask & IN_CREATE:
          new(event)
        elif event.mask & IN_DELETE:
          self._submit(self.cloud.delete, (event.path,))
        elif event.mask & IN_MODIFY:
          # do not start upload for downloading file
          if event.pathname not in self.downloads:
            self._submit(self.cloud.upload, (event.pathname, event.path))
        elif event.mask & IN_ATTRIB:
          # do not start upload for downloading file
          if event.pathname not in self.downloads:
            self._submit(self.cloud.upload, (event.pathname, event.path))

  class _PathWatcher(Queue):               # iNotify watcher for directory
    '''
    iNotify watcher object for monitor of changes in directory.
    '''
    FLAGS = IN_MODIFY|IN_DELETE|IN_CREATE|IN_MOVED_FROM|IN_MOVED_TO  #|IN_ATTRIB

    def __init__(self, path, exclude = None):

      class _EH(ProcessEvent):
        def process_default(self, event):
          _handleEvent(event)

      Queue.__init__(self)
      self._path = path
      self.exclude = exclude or []
      _handleEvent = self.put
      self._wm = WatchManager()
      self._iNotifier = ThreadedNotifier(self._wm, _EH(), timeout=10)
      self._iNotifier.start()


    def start(self, exclude = None):
      # Add watch and start watching
      self.exclude = exclude or self.exclude
      excl = ExcludeFilter(self.exclude)

      self._watch = self._wm.add_watch(self._path, self.FLAGS, exclude_filter=excl,
                                       auto_add=True, rec=True, do_glob=False)

    def stop(self):
      # Remove watch and stop watching
      self._wm.rm_watch(self._watch[self._path], rec=True)

    def exit(self):
      self._iNotifier.stop()

  def connect(self):
    '''Activate synchronizations with Yandex.disk'''
    if self.status == 'none':
      print('connecting')
      self.watch.start()
      #self.listener.start()
      self._setStatus('idle')
      self.fullSync()

  def disconnect(self):
    '''Deactivate synchronizations with Yandex.disk'''
    if self.status != 'none':
      self.watch.stop()
      #self.listener.stop()
      self._setStatus('none')

  def trash(self):
    stat, _ = self.cloud.trash()
    return stat

  def exit(self):
    if self.status != 'none':
      self.disconnect()
    self.shutdown = True
    self.watch.exit()
    self.watch.put(None)
    self.EH.join()
    self.executor.shutdown(wait=True)
    self.statusEvent.set()
    self.SW.join()

def appExit(msg=None):
  print(enumerate())
  for disk in disks:
    disk.exit()
  print('msg: %s' % msg)
  print(enumerate())
  input('exit')
  sysExit(msg)

if __name__ == '__main__':
  from sys import exit as sysExit
  from jconfig import Config
  from gettext import translation
  from time import sleep
  from OAuth import getToken, getLogin
  from os.path import exists as pathExists
  from re import findall
  from signal import signal, SIGTERM, SIGINT


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
        while not pathExists(fullpath):
          path = input('Enter the path to local folder '
                       'which will by synchronized with cloud disk. (Default: ~/Yandex.Disk):')
          fullpath = path.replace('~', osUserHome)
          if not pathExists(fullpath):
            try:
              makedirs(fullpath)
            except:
              print('Error: Incorrect path specified.')
        token = getToken('389b4420fc6e4f509cda3b533ca0f3fd', '5145f7a99e7943c28659d769752f6dae')
        login = getLogin(token)
        config['disks'][login] = {'login': login, 'auth': token, 'path': path, 'start': True,
                                  'ro': False, 'ow': False, 'exclude': []}
        config.save()

  signal(SIGTERM, lambda _signo, _stack_frame: appExit('Killed'))
  signal(SIGINT, lambda _signo, _stack_frame: appExit('CTRL-C Pressed'))

  print('Commands:\n с - connect\n d - disconnect\n s - get status\n t - clear trash\n'
        ' e - exit\n ')
  while True:
    cmd = input()
    if cmd == 'd':
      disks[0].disconnect()
    elif cmd == 'c':
      disks[0].connect()
    elif cmd == 't':
      print(disks[0].trash())
    elif cmd == 's':
      print(disks[0].getStatus())
    elif cmd == 'e':
      appExit()

