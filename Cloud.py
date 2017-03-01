#!/usr/bin/env python3
#
#  Cloud - low level yanex.disk REST API wraper
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

import requests
from time import sleep
from json import dumps
from logging import error


class Cloud(object):
  def __init__(self, token):
    # make headers for requests that require authorization
    self._headers = {'Accept': 'application/json', 'Authorization': token}

  CMD = {'info':  ((requests.get,
                    'https://cloud-api.yandex.net/v1/disk'
                    '?fields=total_space%2Ctrash_size%2Cused_space%2Crevision'),
                   200),
         'last':  ((requests.get,
                    'https://cloud-api.yandex.net/v1/disk/resources/last-uploaded?limit=10'
                    '&fields=path'),
                   200),
         'res':   ((requests.get,
                    'https://cloud-api.yandex.net/v1/disk/resources?path={}'
                    '&fields=size%2Cmodified%2Csha256%2Cpath%2Ctype%2Ccustom_properties'),
                   200),
         'prop':  ((requests.patch,
                    'https://cloud-api.yandex.net/v1/disk/resources/?path={}'
                    '&fields=name%2Ccustom_properties'),
                   200),
         'list':  ((requests.get,
                    'https://cloud-api.yandex.net/v1/disk/resources/files?limit={}&offset={}'),
                   200),
         'mkdir': ((requests.put,
                    'https://cloud-api.yandex.net/v1/disk/resources?path={}'),
                   201),
         'del':   ((requests.delete,
                    'https://cloud-api.yandex.net/v1/disk/resources?path={}&permanently={}'),
                   204),
         'trash': ((requests.delete,
                    'https://cloud-api.yandex.net/v1/disk/trash/resources'),
                   204),
         'move':  ((requests.post,
                    'https://cloud-api.yandex.net/v1/disk/resources/move?from={}&path={}'),
                   201),
         'copy':  ((requests.post,
                    'https://cloud-api.yandex.net/v1/disk/resources/copy?from={}&path={}'),
                   201),
         'up':    ((requests.get,
                    'https://cloud-api.yandex.net/v1/disk/resources/upload?path={}&overwrite={}'),
                   200),
         'down':  ((requests.get,
                    'https://cloud-api.yandex.net/v1/disk/resources/download?path={}'),
                   200)}

  def _request(self, req, *args, **kwargs):
    ''' Perform the request with expanded URL via specified method using predefined headers
    '''
    method, url = req
    r = method(url.format(*args), **kwargs, headers=self._headers)
    return r.status_code, r.json() if r.text else ''

  def _cmd_request(self, cmd, *args, **kwargs):
    ''' Perform requers by command
        It also handles asynchronious operations
    '''
    req, code = self.CMD[cmd]
    status, result = self._request(req, *args, **kwargs)
    if status == 202:  # asyncronious operation
      url = result['href']
      while True:
        sleep(0.777)  # reasonable pause between continuous requests
        st, res = self._request((requests.get, url))
        if st == 200:
          if res.get("status") == "success":
            status = code
            break
        else:
          status = st
          result = res
          break
    if status != code:
      result['code'] = status
      return False, result
    else:
      return True, result

  def getDiskInfo(self):
    ''' Receives cloud disk status information'''
    cmd = 'info'
    status, result = self._cmd_request(cmd)
    if status:
      return True, result
    else:
      error('%s returned %s' % (cmd, str(result)))
      return False, (cmd, result)

  def getLast(self):
    ''' Receives 10 last synchronized items'''
    cmd = 'last'
    status, result = self._cmd_request(cmd)
    if status:
      return True, [item['path'].replace('disk:/', '') for item in result['items']]
    else:
      error('%s returned %s' % (cmd, str(result)))
      return False, (cmd, result)

  def getResource(self, path):
    ''' Returns folder/file properties'''
    cmd = 'res'
    status, result = self._cmd_request(cmd, path)
    if status:
      result['path'] = result['path'].replace('disk:/', '')
      return True, result
    else:
      error('%s %s returned %s' % (cmd, path, str(result)))
      return False, (cmd, path, result)

  def setProps(self, path, **props):
    ''' Sets customer propertie to file/folder
    '''
    cmd = 'prop'
    status, result = self._cmd_request(cmd, path, data=dumps({"custom_properties": props}))
    if status:
      return True, (cmd, path)
    else:
      error('%s %s returned %s' % (cmd, path, str(result)))
      return False, (cmd, path, result)

  def getList(self, chunk=20, offset=0):
    ''' Returns sorted list of cloud files by parts (chunk items starting from offset)
    '''
    cmd = 'list'
    status, result = self._cmd_request(cmd, str(chunk), str(offset))
    if status:
      ret = []
      for i in result['items']:
        ret.append({key: i[key] if key != 'path' else i[key].replace('disk:/', '')
                    for key in ['path', 'type', 'modified', 'sha256', 'size'] })
        ret[-1]['custom_properties'] = i.get('custom_properties')
      return True, ret
    else:
      error('%s returned %s' % (cmd, str(result)))
      return False, (cmd, result)

  def mkDir(self, path):
    ''' Makes new cloud folder
    '''
    cmd = 'mkdir'
    status, result = self._cmd_request(cmd, path)
    if status:
      return True, (cmd, path)
    else:
      if result['error'] == 'DiskPathPointsToExistentDirectoryError':
        return True, (cmd, path)
      else:
        error('%s %s returned %s' % (cmd, path, str(result)))
        return False, (cmd, path, result)

  def delete(self, path, perm=False):
    ''' Deletes file/folder from cloud disk'''
    cmd ='del'
    status, result = self._cmd_request(cmd, path, 'true' if perm else 'false')
    if status:
      return True, (cmd, path)
    else:
      error('%s %s returned %s' % (cmd, path, str(result)))
      return False, (cmd, path, result)

  def trash(self):
    ''' Makes trush empty
    '''
    cmd = 'trash'
    status, result = self._cmd_request(cmd)
    if status:
      return True, (cmd,)
    else:
      error('%s returned %s' % (cmd, str(result)))
      return False, (cmd, result)

  def move(self, pathfrom, pathto):
    ''' Moves file/folder from one path to another
    '''
    cmd = 'move'
    status, result = self._cmd_request(cmd, pathfrom, pathto)
    if status:
      return True, (cmd, pathfrom, pathto)
    else:
      error('%s %s %s returned %s' % (cmd, pathfrom, pathto, str(result)))
      return False, (cmd, pathfrom, pathto, result)

  def copy(self, pathfrom, pathto):
    ''' Makes copy of file/path
    '''
    cmd = 'copy'
    status, result = self._cmd_request(cmd, pathfrom, pathto)
    if status:
      return True, (cmd, pathfrom, pathto)
    else:
      error('%s %s %s returned %s' % (cmd, pathfrom, pathto, str(result)))
      return False, (cmd, pathfrom, pathto, result)

  def upload(self, lpath, path, ow=True):
    cmd = 'up'
    status, result = self._cmd_request(cmd, path, 'true' if ow else 'false')
    if status:
      try:
        with open(lpath, 'rb') as f:
          r = requests.put(result['href'], data = f)
        if r.status_code in (201, 200):
          return True, (cmd, path)
      except FileNotFoundError:
        return False, (cmd, path, {'error': 'FileNotFoundError', 'path': lpath})
      result = r.json() if r.text else dict()
      result['code'] = r.status_code
    error('%s %s returned %s' % (cmd, path, str(result)))
    return False, (cmd, path, result)

  def download(self, path, lpath):
    cmd = 'down'
    status, result = self._cmd_request(cmd, path)
    if status:
      r = requests.get(result['href'], stream=True)
      ### need try except for open and write
      with open(lpath, 'wb') as f:
        for chunk in r.iter_content(2048):
          f.write(chunk)
      if r.status_code == 200:
        return True, (cmd, path)
      result = r.json() if r.text else dict()
      result['code'] = r.status_code
    error('%s %s returned %s' % (cmd, path, str(result)))
    return False, (cmd, path, result)
