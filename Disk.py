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
from Cloud import Cloud as _Cloud
from time import time, gmtime, strftime
from hashlib import sha256
from glob import iglob
from tempfile import NamedTemporaryFile as tempFile
from shutil import move as fileMove

class Cloud(_Cloud):    # redefined cloud class for implement some application level logic
  ''' - all paths are absolute paths only (download/upload by 1 parameter - absolute path)
      - getFullList converter to generator that yields fill list by chunks paths
      - download is performed through the temporary file
  '''
  def __init__(self, token, hdata, path):
    self.data = Config(hdata)
    self.path = path
    _Cloud.__init__(self, token)

  def getFullList(self, chunk=None):  # getFullList is a generator that yields file list by chunks
    offset = 0
    chunk = chunk or 20
    while True:
      status, res = _Cloud.getFullList(self, chunk, offset)
      if status:
        l = len(res)
        if l:
          yield True, [{'path': path_join(self.path, i['path']),
                        'modified': i['modified'],
                        'type': i['type'],
                        'sha256': i['sha256']
                       } for i in res]
          if l < chunk:
            break
          else:
            offset += chunk
        else:
          break
      else:
        return status, res

  def download(self, path):    # download via temporary file to make it in transaction manner
    with tempFile(suffix='.yandex-disk-client', delete=False) as f:
      temp = f.name
    status, res = _Cloud.download(self, relpath(path, start=self.path), temp)
    if status:
      try:
        fileMove(temp, path)
        self.data[path] = getModified(path)
      except:
        status = False
    return status, res

  def upload(self, path):
    status, res = _Cloud.upload(self, path, relpath(path, start=self.path))
    if status:
      self.data[path] = getModified(path)
    return status, res

  def delete(self, path):
    status, res = _Cloud.delete(self, relpath(path, start=self.path))
    if status:
      del self.data[path]
    return status, res

  def move(self, pathfrom, pathto):
    pathto = relpath(pathto, start=self.path)
    pathfrom = relpath(pathfrom, start=self.path)
    status, res = _Cloud.move(self, pathfrom, pathto)
    if status:
      self.data[pathto] = self.data[pathfrom]
      del self.data[pathfrom]
    return status, res

  def mkDir(self, path):
    status, res = _Cloud.mkDir(self, relpath(path, start=self.path))
    if status:
      self.data[path] = True
    return status, res

def getModified(path):
  f_st = file_info(path)      # follow symlink by default ???
  return strftime('%Y-%m-%dT%H:%M:%S', gmtime(f_st.st_mtime))

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
    self.cloud = Cloud(self.user['auth'],
                       path_join(self.path, dataFolder, 'hist.data'),
                       self.path)
    self.executor = ThreadPoolExecutor()
    self.shutdown = False
    self.downloads = set()
    self.EH = Thread(target=self._eventHandler)
    self.EH.name = 'EventHandler'
    self.watch = self._PathWatcher(self.path,
                                   [path_join(self.path, e)
                                     for e in self.user['exclude'] + ['.yandex-disk-client']])
    self.EH.start()
    #self.listener = XMPPListener('%s\00%s' % (user[login], user[auth]))
    # Status treatment staff
    self.prevStatus = 'none'
    self.status = 'none'
    self.error = False
    self.progress = ''
    self.cloudStatus = dict()
    self.changes = {'init'}
    self.statusQueue = Queue()
    self.SU = Thread(target=self._statusUpdater)
    self.SU.name = 'StatusUpdater'
    self.SU.start()
    # connect if it required
    if self.user.setdefault('start', True):
      self.connect()

  def _setStatus(self, status):
    if status != self.status:
      self.prevStatus = self.status
      self.status = status
      self.statusQueue.put((status, self.prevStatus))

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
    if self.cloudStatus.get('total', False):
      if ((self.cloudStatus['used'] != used) or
          (self.cloudStatus['trash'] != trash) or
          (self.cloudStatus['total'] != total)):
        self.changes.add('prop')
      else:
        self.changes.add('prop')
    self.cloudStatus['total'] = total
    self.cloudStatus['used'] = used
    self.cloudStatus['trash'] = trash
    # get last synchronized list
    stat, res = self.cloud.getLast()
    last = res if stat else []
    if last != self.cloudStatus.get('last', None):
      self.changes.add('last')
    self.cloudStatus['last'] = last

  def _statusUpdater(self):     # Thread that reacts on status changes
    stime = time()
    while not self.shutdown:
      status, prevStatus = self.statusQueue.get()
      self.changes.add('stat')
      if status == 'busy':
        stime = time()
      if prevStatus == 'busy':
        print('Finished in %s sec.' % (time() - stime))
        self.updateInfo()
      sync = False
      if status == 'idle':
        self.cloud.data.save()
        if self.error:
          print('ERROR WAS DETECTED!!!!!!! --> fillSync')
          sync = True
          self.error = False
      self.updateInfo()
      if self.changes:
        changes = self.changes
        self.changes = set()
        self.changed(changes)
      if sync:
        self.fullSync()

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
            'total': self.cloudStatus['total'],
            'used': self.cloudStatus['used'],
            'trash': self.cloudStatus['trash'],
            'last': self.cloudStatus['last'],
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
        print(self.cloudStatus['last'])
      elif e == 'prop':
        s = ''
        for t in ['total', 'used', 'trash']:
          s += '%s: %s ' % (t, self.cloudStatus[t])
        print(s)

  def _submit(self, task, args):

    def taskCB(ft):
      res = ft.result()
      unf = self.executor.unfinished()
      stat, path = res
      if not stat:
        self.error = True
      print('Done: %s, %d unfinished' % (str(res), unf))
      if path:
        # Remove downloaded file from downloads
        self.downloads -= {path}
      if unf == 0:
        self._setStatus('idle')

    ft = self.executor.submit(task, *args)
    ft.add_done_callback(taskCB)
    if self.status != 'busy':
      self._setStatus('busy')
    print('submit %s %s' % (findall(r'Cloud\.\w*', str(task))[0] , str(args)))

  def fullSync(self):
    ignore = set()  # set of files that shouldn't be synced or alredy in sync
    exclude = set(self.watch.exclude)
    data = dict()
    # colud - local -> download from cloud ... or  delete from cloud???
    # (cloud & local) and hashes are equal = ignore
    # (cloud & local) and hashes not equal -> decide upload/download depending on the update
    # time... or it is a conflict ???
    for stat, items in self.cloud.getFullList(chunk=20):
      if stat:
        for i in items:
          path = i['path']
          p, _ = path_split(path)
          if p in exclude:
            continue
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
                # remember modified data-time of matched path and it's folder
                self.cloud.data[path] = getModified(path)
                if p != path:
                  self.cloud.data[p] = True
                continue
              else:
                # Need to decide what to do: upload, download, or it is conflict.
                # In order to find the conflict the 'modified' date-time
                # from previous upload/download have to be stored somewhere.... Where to store it???
                # Without this info the only two solutions are possible:
                # - download if the cloud file newer than the local, or
                # - upload if the local file newer than the cloud file.
                c_t = i['modified'][:19]    # remove time zone as it is always GMT (+00:00)
                l_t = getModified(path)
                h_t = self.cloud.data.get(path, l_t)
                if l_t != h_t and c_t != h_t:     # conflict
                  print('conflict')
                elif l_t > c_t:
                  # upload (as file exists the dir exists too - no need to create dir in cloud)
                  self._submit(self.cloud.upload, (path,))
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
          # connected to cloud).
          if self.cloud.data.get(path, False):  # do we have history data for this path?
            # as we have history info for path but local path doesn't exists then we have to
            # delete it from cloud
            if not pathExists(p):   # containing directory is also removed?
              d = p
              while True:           # go down to the shortest removed directory
                p_, _ = path_split(d)
                if pathExists(p_):
                  break
                d = p_
              self.cloud.data[d] = True
              self._submit(self.cloud.delete, (d,))
              exclude.add(p)        # add deleted directory in exceptions to avoid unnecessary checks
            else:                   # delete only file
              self._submit(self.cloud.delete, (path,))
          else:   # local file have to be updated (downloaded from the cloud)
            if i['type'] == 'file':
              if not pathExists(p):
                self.downloads.add(p)             # store new dir in dowloads to avoud upload
                makedirs(p, exist_ok=True)
                self.cloud.data[p] = True
              ignore.add(p)
              self.downloads.add(path)            # store downloaded file in dowloads to avoud upload
              self._submit(self.cloud.download, (path,))
              ignore.add(path)
            else:                                 # directory not exists
              self.downloads.add(path)            # store new dir in dowloads to avoud upload
              makedirs(path, exist_ok=True)
              ignore.add(path)
    self.cloud.data.save()
    # (local - ignored) -> upload to cloud
    for root, dirs, files in walk(self.path):
      ex = False
      for p in exclude:
        if root[:len(p)] == p:
          ex = True
          break
      if ex:
        continue
      for d in dirs:
        d = path_join(root, d)
        if d not in ignore | exclude:
          # directory have to be created before start of uploading a file in it
          # do it inline as it rather fast operation
          s, r = self.cloud.mkDir(d)
          print('done inline', s, r)
      for f in files:
        f = path_join(root, f)
        if f not in ignore:
          self._submit(self.cloud.upload, (f,))

  def _eventHandler(self):      # Thread that handles iNotify watcher events

    def new(event):
      if event.dir:
        if event.pathname in self.downloads:
          # this dir was created localy within fullSync it ia already exists in the cloud
          self.downloads -= {event.pathname}
        else:
          # create newly created local dir in the cloud
          self._submit(self.cloud.mkDir, (event.pathname,))
      else:   # it is file
        # do not start upload for downloading file
        if event.pathname not in self.downloads:
          self._submit(self.cloud.upload, (event.pathname,))

    def moved(event):
      if event.mask & IN_MOVED_TO:  # moved in = new
        new(event)
      else:  # moved out = deleted
        self._submit(self.cloud.delete, (event.pathname,))

    IN_MOVED = IN_MOVED_FROM | IN_MOVED_TO
    while not self.shutdown:
      event = self.watch.get()
      if event is not None:
        ''' event.pathname - full path
        '''
        while event.mask & IN_MOVED:
          try:
            event2 = self.watch.get(timeout=0.1)
            try:
              cookie = event2.cookie
            except AttributeError:
              cookie = ''
            if event.cookie == cookie:
              # greate! we've found the move operatin (file moved within the synced path)
              self._submit(self.cloud.move, (event.pathname, event2.pathname))
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
          self._submit(self.cloud.delete, (event.pathname,))
        elif event.mask & IN_MODIFY:
          # do not start upload for downloading file
          if event.pathname not in self.downloads:
            self._submit(self.cloud.upload, (event.pathname,))
        elif event.mask & IN_ATTRIB:
          # do not start upload for downloading file
          if event.pathname not in self.downloads:
            self._submit(self.cloud.upload, (event.pathname,))

  class _PathWatcher(Queue):    # iNotify watcher for directory
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
      #self.exclude = exclude or self.exclude
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
    self._setStatus('exit')
    self.SU.join()

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
  dataFolder = '.yandex-disk-client'
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
      path = expanduser(user['path'])
      if not pathExists(path):
        try:
          makedirs(path_join(path, dataFolder), exist_ok=True)
        except:
          appExit(_("Error: Can't access the local folder %s" % path))
      disks.append(Disk(user))
    if disks:
      break
    else:
      path = ''
      print(_('No accounts configured'))
      if input(_('Do you want to configure new account (Y/n):')).lower() not in ('', 'y'):
        appExit(_('Exit.'))
      else:
        while not pathExists(path):
          path = input(_('Enter the path to local folder '
                         'which will by synchronized with cloud disk. (Default: ~/YandexDisk):'))
          path = expanduser(path)
          if not pathExists(path):
            try:
              makedirs(path_join(path, dataFolder), exist_ok=True)
            except:
              print('Error: Incorrect folder path specified (no access or wrong path name).')
        token = getToken('389b4420fc6e4f509cda3b533ca0f3fd', '5145f7a99e7943c28659d769752f6dae')
        login = getLogin(token)
        config['disks'][login] = {'login': login, 'auth': token, 'path': path, 'start': True,
                                  'ro': False, 'ow': False, 'exclude': []}
        config.save()

  signal(SIGTERM, lambda _signo, _stack_frame: appExit('Killed'))
  signal(SIGINT, lambda _signo, _stack_frame: appExit('CTRL-C Pressed'))

  # main thread.
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
