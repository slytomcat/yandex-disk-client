# -*- coding: utf-8 -*-
# Yandex.disk client engine
from os import remove, makedirs, getpid, geteuid, getenv

class User(object):
  def __init__(conf):
    self.LocalDir = conf.LocalDir
    self.Token = conf.Token
    self.startOnStart = conf.startOnStart
    self.active = False

class Disk(object):
  '''High-level Yandex.disk client interface'''
  def __init__(user):
    self.user = user
    self.status = initialStatus
    if user.startOnStart:
      self.connect(user)
    self.activated({'init'})

  def connect(user):
    '''Activate synchronizations with Yandex.disk'''
    if not user.active:
      startWatch(user.LocalDir)
      openListenSocket(user.Token)
    self.activated({'stat'})

  def disconnect(user):
    '''Deactivate synchronizations with Yandex.disk'''
    if user.active:
      stopWatch(user.LocalDir)
      closeListenSocket(user.Token)
    self.activated({'stat'})

  def status():
    '''Return the current synchronization status'''

    return self.currentStatus

  def changed(change={}):
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
    print(self.currentStatus)

  def _folderWatchHandler():
    if folderChanged():
      _syncLocal2Cloud()

  def _socketHandler():
    if changeReceived():
      _syncCloud2Local()

  def _syncLocal2Cloud():
    '''Start synchronization from local folder to Yandex.disk'''
    holdSocketListening()
    doUploads()
    unholdSocketListening()

  def _syncCloud2Local():
    '''Start synchronization from Yandex.disk to local folder'''
    stopWatch(userLocalDir)
    doDownloads()
    startWatch(userLocalDir)

def appExit(msg=None):
  from sys import exit as sysExit

  for disk in disks:
    disk.exit()
  sysExit(msg)

if __name__ == '__main__':
  from jconfig import Config
  from gettext import translation

  appName = 'yd-client'
  osUserHome = getenv("HOME")
  confHome = osUserHome + '/.config/' + appName
  config = Config(confHome + 'client.conf')
  if not config.loaded:
    makedirs(confHome)
    config.changed = True
  config.setdefault('type', 'std')
  config.setdefault('disks', {})
  if config.changed:
    config.save()
  # Setup localization
  translation(appName, '/usr/share/locale', fallback=True).install()

  disks = []
  for user in config['disks'].items():
    disks.append(Disk(user))
  if not disks:
    appExit(_('No accounts configred'))
