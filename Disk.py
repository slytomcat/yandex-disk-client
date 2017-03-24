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

from os import remove, makedirs, walk, stat as file_info, chown, chmod, utime
from os.path import join as path_join, expanduser, relpath, split as path_split, exists as pathExists
from pyinotify import ProcessEvent, WatchManager, Notifier, ThreadedNotifier, ExcludeFilter,\
                      IN_MODIFY, IN_DELETE, IN_CREATE, IN_MOVED_FROM, IN_MOVED_TO, IN_ATTRIB
from threading import Thread, Event, enumerate
from queue import Queue, Empty
from PoolExecutor import ThreadPoolExecutor
from CloudDisk import Cloud
from jconfig import Config
from hashlib import sha256
from tempfile import NamedTemporaryFile as tempFile
from shutil import move as fileMove
from datetime import datetime
from time import time
from logging import debug, info, warning, error, critical


def in_paths(path, paths):
  '''Check that path is within one of paths
     Examples:
        /home/disk/folder1/ex_folder/some_flie is within /home/disk/folder1/ex_folder,
        but not within /home/disk/folder2'''
  for p in paths:
    if path.startswith(p):
      return True         # yes if p is a left part of checked path
  return False

class Disk(Cloud):
  '''High-level Yandex.disk client interface.
     It can have following statuses (self.status updates by thread StatusUpdater):
      - fault - when disk can't access local folder (disk in this state is not operational)
      - busy - when some activities are currently performed
      - idle - no activities are currently performed
      - none - not connected
      - no_net - network connection is not available (try to reconnect it later)
      - error - some error (inspect the errorReason and try to fix it)
     All working paths within this class are absolute paths.
  '''
  def __init__(self, user):
    self.user = user  # dictionary with user configuration
    path = expanduser(self.user['path'])
    dataFolder = '.yandex-disk-client'
    dataFolderPath = path_join(path, dataFolder)
    self.prevStatus = 'start'
    self.status = 'none'
    self.errorReason = ''
    if not pathExists(dataFolderPath):
      info('%s not exists' % dataFolderPath)
      try:
        makedirs(dataFolderPath, exist_ok=True)
      except:
        self.status = 'fault'
    else:
      try:
        utime(dataFolderPath)
      except:
        self.status = 'fault'
    self.shutdown = False   # signal for utility threads to exit
    if self.status == 'fault':
      self.errorReason = "Can't access the local folder %s" % dataFolderPath
      critical(self.errorReason)
    else:
      super().__init__(self.user['auth'], path, dataFolderPath)
      self.executor = ThreadPoolExecutor()
      self.downloads = set()  # set of currently downloading files
      # event handler thread
      self.EH = Thread(target=self._eventHandler)
      self.EH.name = 'EventHandler'
      # i-notify watcher object
      self.watch = self._PathWatcher(self.path,
                                     [path_join(self.path, e)
                                       for e in self.user['exclude'] + [dataFolder]])
      self.EH.start()
      #self.listener = XMPPListener('\00'.join(user[login], user[auth]))
    # Status treatment staff
    self.error = False  # error flag. If it is True then fullSync is required
    self.progress = ''
    # dictionary with set of cloud status elements. Initial state
    self.cloudStatus = dict()
    self.changes = {'init'}  # set with changes flags
    # individual thread to control changes of status
    self.statusQueue = Queue()  # queue to pass status changes from other threads to StatusUpdater
    self.SU = Thread(target=self._statusUpdater)
    self.SU.name = 'StatusUpdater'
    self.SU.start()
    if self.status != 'fault':
      # connect to cloud if it is required by configuration
      if self.user.setdefault('start', True):
        self.connect()
      else:
        self.statusQueue.put((self.status, self.prevStatus))
    else:
      # set fault status
      self.statusQueue.put((self.status, self.prevStatus))

  def connected(self):
    return self.status in {'idle','busy','error'}

  def _setStatus(self, status):
    if status != self.status:
      self.prevStatus = self.status
      self.status = status
      self.statusQueue.put((status, self.prevStatus))

  def updateInfo(self):
    # get disk statistics if connected
    if self.connected():
      stat, res = self.task('info')
    else:
      stat = False
    if stat:
      total = res['total_space']
      used = res['used_space']
      trash = res['trash_size']
    else:
      total = '...'
      used = '...'
      trash = '...'
    if (self.cloudStatus.get('total') is None or
        self.cloudStatus['used'] != used or
        self.cloudStatus['trash'] != trash or
        self.cloudStatus['total'] != total):
      self.changes.add('prop')
      self.cloudStatus['total'] = total
      self.cloudStatus['used'] = used
      self.cloudStatus['trash'] = trash
    # get last synchronized list
    if self.connected():
      stat, res = self.task('last')
    else:
      stat = False
    last = res if stat else []
    if last != self.cloudStatus.get('last', []):
      self.changes.add('last')
    self.cloudStatus['last'] = last

  def _statusUpdater(self):     # Thread that reacts on status changes
    stime = time()
    while not self.shutdown:
      status, prevStatus = self.statusQueue.get()
      self.changes.add('stat')
      if status == 'busy':
        stime = time()
      if status == 'idle':
        self.h_data.save()
        if self.error:
          info('Some errors was detected during sync --> fillSync required')
          self.error = False
          self.fullSync()
        else:
          info('Finished in %s sec.' % (time() - stime))
      self.updateInfo()
      if self.changes:
        changes = self.changes
        self.changes = set()
        self.changed(changes)

  def getStatus(self):
    '''Return the current disk status
       The returned status dict contain the following items:
         { 'status': <current status (one of: 'fault', 'none', 'idle', 'busy', 'error', 'no_net')>,
           'progress': <current activity progress (it is actual only for 'busy' status)>,
           'login': <Cloud disk user login>
           'total': <total cloud disk size>,
           'used': <used cloud disk space>,
           'trash': <trash size>,
           'path': <synchronized local path>,
           'last': <up to 10 last synchronized items>
           'reson': <fault or error reason>
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
            'path': self.user['path'],
            'reason': self.errorReason
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
    # Output status changes to standard output
    print('status: %s  path: %s  event: %s' % (self.status, self.user['path'], str(change)))
    for e in change:
      if e == 'last':
        print(self.cloudStatus['last'])
      elif e == 'prop':
        print(' '.join(': '.join((t, str(self.cloudStatus[t]))) for t in ['total', 'used', 'trash']))

  def _submit(self, task, *args, **kwargs):

    def taskCB(ft):
      res = ft.result()
      unf = self.executor.unfinished()
      info('Done: %s, %d unfinished' % (str(res), unf))
      if isinstance(res, tuple):
        stat, rets = res      # it is cloud operation
        if not stat:
          self.error = True
        elif isinstance(rets, tuple) and rets[0] == 'down':
          # Remove downloaded file from downloads
          self.downloads -= {rets[1]}
      #elif isinstance(res, str) and res == 'fullSync':
      #  <do something after full sync>
      if unf == 0:  # all done
        self.downloads = set()  # clear downloads as no more downloads required
        self._setStatus('idle')

    if isinstance(task, str):
      ft = self.executor.submit(self.task, task, *args, **kwargs)
    else:
      ft = self.executor.submit(task, *args, **kwargs)
    ft.add_done_callback(taskCB)
    if self.status != 'busy':
      self._setStatus('busy')
    info('submit %s %s' % (str(task) , str(args)))

  def fullSync(self):
    '''Execute full synchronization within PoolExecutor
    '''

    def _fullSync(self):
      def ignore_path_down(path):
        nonlocal ignore
        ret = set()
        while path not in ignore and path != self.path:
          ret.add(path)
          if pathExists(path):
            self.h_data[path] = int(file_info(path).st_mtime)
          path = path_split(path)[0]
        ignore |= ret
        return ret
      ignore = set()  # set of files that shouldn't be synced or already in sync
      exclude = set(self.watch.exclude)
      # {colud} - {local} -> download from cloud or delete from cloud if it exist in the history
      # ({cloud} & {local}) and hashes are equal = ignore
      # ({cloud} & {local}) and hashes not equal -> decide conflict/upload/download depending on
      # the update time of files and time stored in the history
      for status, i in self.task('list', 40):
        if status:
          path = i['path']         # full file path !NOTE! getList doesn't return empty folders
          p = path_split(path)[0]  # containing folder
          if in_paths(p, exclude):
            continue
          if pathExists(path):
            if i['type'] == 'dir':  # it is existing directory
              # there is nothing to check for directories
              # here we may check UGM and if they are different we have to decide:
              # - store UGM to cloud or
              # - restore UGM from cloud
              # but for this decision we need last updated data for directories in history
              ####
              # !!! Actually Yd don't return empty folders in file list !!!
              # This section newer run
              ####
              #ignore_path_down(path); continue
              pass
            else:                     # existig file
              try:
                with open(path, 'rb') as f:
                  hh = sha256(f.read()).hexdigest()
              except:
                hh = ''
              c_t = i['modified']                       # cloud file modified date-time
              l_t = int(file_info(path).st_mtime)       # local file modified date-time
              h_t = self.h_data.get(path, l_t)    # history file modified date-time
              if hh == i['sha256']:
                # Cloud and local hashes are equal
                # here we may check UGM and if they are different we have to decide:
                # - store UGM to cloud or
                # - restore UGM from cloud
                # depending on modified time (compare c_t and l_t)
                ignore_path_down(path)  # add in ignore and history all folders by way to file
                continue
              else:
                # Cloud and local files are different. Need to decide what to do: upload,
                # download, or it is conflict.
                # Solutions:
                # - conflict if both cloud and local files are newer than stored in the history
                # - download if the cloud file newer than the local, or
                # - upload if the local file newer than the cloud file.
                if l_t > h_t and c_t > h_t:     # conflict
                  info('conflict')
                  continue ### it is not fully designed and not tested yet !!!
                  # Concept: rename older file to file.older and copy both files --> cloud and local
                  path2 = path + '.older'
                  ignore.add(path2)
                  ignore.add(path)
                  if l_t > c_t:  # older file is in cloud
                    self.downloads.add(path2)
                    self.task('move', path2, path)  # need to do before rest
                    self._submit('down', path2)
                    self._submit('up', path)
                  else:  # local file is older than file in cloud
                    self.downloads.add(path)
                    fileMove(path, path2)  # it will be captured as move from & move to !!!???
                    self._submit('down', path)
                    self._submit('up', path2)
                  continue
                elif l_t > c_t:  # local time greater than the cloud time
                  # upload (as file exists the dir exists too - no need to create dir in cloud)
                  self._submit('up', path)
                  ignore_path_down(path)  # add in ignore and history all folders by way to file
                  continue
                else:  # download
                  # upload (as file exists the dir exists too - no need to create local dir)
                  self.downloads.add(path)  # remember in downloads to avod events on this path
                  self._submit('down', path)
                  ignore_path_down(path)  # add in ignore and history all folders by way to file
                  continue
          # The file is not exists
          # it means that it has to be downloaded or.... deleted from the cloud when local file
          # was deleted and this deletion was not cached by active client (client was not
          # connected to cloud or was not running at the moment of deletion).
          if self.h_data.get(path, False):  # do we have history data for this path?
            # as we have history info for path but local path doesn't exists then we have to
            # delete it from cloud
            if not pathExists(p):   # containing directory is also removed?
              while True:           # go down to the shortest removed directory
                p_ = path_split(p)[0]
                if pathExists(p_):
                  break
                p = p_
                self.h_data.pop(p)  # remove history
                ### !!! all files in this folder mast be removed too, but we
                ### can't walk as files/folders was deleted from local FS!
                ### NEED history database to do delete where path.startwith(p) - it can't be done in dict
              self._submit('del', p)
              # add d to exceptions to avoid unnecessary checks for other files which are within p
              exclude.add(p)
            else:                   # only file was deleted
              self._submit('del', path)
              del self.h_data[path]  # remove history
          else:   # local file have to be downloaded from the cloud
            if i['type'] == 'file':
              if not pathExists(p):
                self.downloads |= ignore_path_down(p)   # store new dir in downloads to avoid upload
                makedirs(p, exist_ok=True)
              ignore.add(p)
              self.downloads.add(path)            # store downloaded file in downloads to avoid upload
              self._submit('down', path)
              ignore.add(path)
            #else:                                 # directory not exists  !!! newer run !!!
            #  self.downloads.add(ignore_path_down(path))  # store new dir in downloads to avoid upload
            #  makedirs(path, exist_ok=True)
      # ---- Done forward path (sync cloud to local) ------
      # (local - ignored) -> upload to cloud
      for root, dirs, files in walk(self.path):
        if in_paths(root, exclude):
          continue
        for d in dirs:
          d = path_join(root, d)
          if d not in ignore | exclude:
            # directory have to be created before start of uploading a file in it
            # do it in-line as it rather fast operation
            s, r = self.task('mkdir', d)
            info('done in-line %s %s'%(str(s), str(r)))
            ### !need to check success of folder creation! !need to decide what to do in case of error!
        for f in files:
          f = path_join(root, f)
          if f not in ignore:
            self._submit('up', f)
      return 'fullSync'

    if self.connected():
      self._submit(_fullSync, self)

  def _eventHandler(self):      # Thread that handles iNotify watcher events
    # Event handler local functions
    def _recCreate(path, exclude, submit):
      '''
        It recursively creates folders and files in cloud, starting from specified directory.
        It itself executed in threadExecutor and submits files uploads to threadExecutor but
        directories created by direct calls as it rather fast operation and directories need
        to be created in advance (before uploading file to them).
      '''
      s, r = self.task('mkdir', path)
      for root, dirs, files in walk(path):
        if in_paths(root, exclude):
          break
        for d in dirs:
          s, r = self.task('mkdir', path_join(root, d))
          info('done in-line %s %s'%(str(s), str(r)))
          ### !need to check success of folder creation! !need to decide what to do in case of error!
        for f in files:
          submit('up', path_join(root, f))
      return 'recCreate'

    def new(event):
      '''
        Handle new file/folder appearance
      '''
      if event.dir:
        if event.pathname in self.downloads:
          # this dir was created locally within fullSync it is already exists in the cloud
          self.downloads.remove(event.pathname)
        else:
          # create newly created local dir in the cloud
          if event.mask & IN_MOVED_TO:
            # If moved folder is not empty there is no events appear for all it's content.
            # So we need to walk inside and upload all directories, subdirectories and files
            # that are within the moved directory.
            # Do this task within threadExecutor as it can rather many files inside.
            self._submit(_recCreate, event.pathname, self.watch.exclude, self._submit)
          else:
            self.task('mkdir', event.pathname)
      else:   # it is file
        # do not start upload for downloading file
        if event.pathname not in self.downloads:
          self._submit('up', event.pathname)

    def moved(event):
      '''
        Handle standalone moved events
      '''
      if event.mask & IN_MOVED_TO:  # moved in = new
        new(event)
      else:  # moved out = deleted
        self._submit('del', event.pathname)
    '''
    Event handling thread
    '''
    while not self.shutdown:
      event = self.watch.get()
      if event is None:
        continue
      info(event)
      ''' event.pathname - full path
      '''
      while event.mask & (IN_MOVED_FROM | IN_MOVED_TO):
        try:
          event2 = self.watch.get(timeout=0.1)
          info(event2)
          try:
            cookie = event2.cookie
          except AttributeError:
            cookie = ''
          if event.cookie == cookie:
            # great! we've found the move operation (file moved within the synced path)
            self._submit('move', event.pathname, event2.pathname)
            break  # as ve alredy treated two MOVED events
          else:
            moved(event)  # treat first MOVED event as standalone
            event = event2  # treat second MOVED event
        except Empty:
          moved(event)  # treat first MOVED event as standalone
          break
      # treat not MOVED events
      if event.mask & IN_CREATE:
        new(event)
      elif event.mask & IN_DELETE:
        self._submit('del', event.pathname)
      elif event.mask & IN_MODIFY:
        # do not start upload for downloading file
        if event.pathname not in self.downloads:
          self._submit('up', event.pathname)
      elif event.mask & IN_ATTRIB:
        # do not update cloud properties for downloading file
        if event.pathname not in self.downloads:
          self._submit('setm', event.pathname)

  class _PathWatcher(Queue):    # iNotify watcher for directory
    '''
    iNotify watcher object for monitor of changes in directory.
    '''
    FLAGS = IN_MODIFY|IN_DELETE|IN_CREATE|IN_MOVED_FROM|IN_MOVED_TO|IN_ATTRIB

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
      self.started = False
      self._watch = []

    def start(self, exclude = None):
      if not self.started:
        # Add watch and start watching
        # Update exclude filter if it provided in call of start method
        self.exclude = exclude or self.exclude
        self._watch = self._wm.add_watch(self._path, self.FLAGS,
                                       exclude_filter=ExcludeFilter(self.exclude),
                                       auto_add=True, rec=True, do_glob=False)
        self.started = True

    def stop(self):
      if self.started:
        # Remove watch and stop watching
        self._wm.rm_watch(self._watch[self._path], rec=True)
        self.started = False

    def exit(self):
      self.stop()
      self._iNotifier.stop()

  def connect(self):
    '''Activate synchronizations with Yandex.disk
       Check connection and activate local watching object and cloud listener'''
    if self.status.startswith('no'): # self.status in ('none', 'no_net')
      if self.task('info')[0]:  # check connection
        self.watch.start()
        #self.listener.start()
        self._setStatus('busy')
        self.fullSync()
      else:
        self._setStatus('no_net')

  def disconnect(self):
    '''Deactivate synchronizations with Yandex.disk'''
    if self.connected():
      self.watch.stop()
      #self.listener.stop()
      self._setStatus('none')

  def trash(self):
    if self.connected():
      self._submit('trash')

  def exit(self):
    if self.connected():
      self.disconnect()
    self.shutdown = True
    if self.status != 'fault':
      self.watch.exit()
      self.watch.put(None)
      self.EH.join()
      self.executor.shutdown(wait=True)
    self._setStatus('exit')
    self.SU.join()
    return 0
