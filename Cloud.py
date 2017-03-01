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

  def _request(self, req, *args, **kwargs):
    '''Perform the request with expanded URL via specified method using predefined headers
    '''
    method, url = req
    r = method(url.format(*args), data=kwargs.get('dt'), headers=self._headers)
    return r.status_code, r.json() if r.text else ''

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
                    '&fields=size%2Cmodified%2Ccreated%2Csha256%2Cpath%2Ctype%2Ccustom_properties'),
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

  def _wait(self, url, rets):
    '''waits for asynchronous operation completion '''
    while True:
      sleep(0.777)  # reasonable pause between continuous requests
      status, r = self._request((requests.get, url))
      if status == 200:
        if r["status"] == "success":
          return True, rets
      else:
        error('Async op ["%s"] returned %d' % (rets, status))
        return False, rets

  def getDiskInfo(self):
    '''Receives cloud disk status information'''
    req, code = self.CMD['info']
    status, res = self._request(req)
    if status == code:
      return True, res
    else:
      error('Info returned %d' % status)
      return False, 'info'

  def getLast(self):
    '''Receives 10 last synchronized items'''
    req, code = self.CMD['last']
    status, res = self._request(req)
    if status == code:
      return True, [item['path'].replace('disk:/', '') for item in res['items']]
    else:
      error('Last returned %d' % status)
      return False, 'last'

  def getResource(self, path):
    req, code = self.CMD['res']
    status, res = self._request(req, path)
    if status == code:
      res['path'] = res['path'].replace('disk:/', '')
      return True, res
    else:
      error('Resource %s returned %d' % (path, status))
      return False, 'res ' + path

  def setProps(self, path, **props):
    req, code = self.CMD['prop']
    rets = 'prop ' + path
    status, res = self._request(req, path, dt=dumps({"custom_properties": props}))
    if status == code:
      return True, rets
    else:
      error('%s returned %d' % (rets, status))
      return False, rets + ' code: ' + str(status)

  def getList(self, chunk=20, offset=0):
    req, code = self.CMD['list']
    status, res = self._request(req, str(chunk), str(offset))
    if status == code:
      ret = []
      for i in res['items']:
        ret.append({key: i[key] if key != 'path' else i[key].replace('disk:/', '')
                     for key in ['path', 'type', 'modified', 'sha256']
                    })
        ret[-1]['custom_properties'] = i.get('custom_properties')
      return True, ret
    else:
      error('list returned %d' % status)
      return False, 'list'

  def mkDir(self, path):
    req, code = self.CMD['mkdir']
    rets = 'mkdir ' + path
    status, res = self._request(req, path)
    if status == code or status == 409:  # 409 - already exists - it is not fail in this case
      return True, rets
    else:
      error('%s returned %d' % (rets, status))
      return False, rets

  def delete(self, path, perm=False):
    req, code = self.CMD['del']
    rets = 'del ' + path
    status, res = self._request(req, path, 'true' if perm else 'false')
    if status == code:
      return True, rets
    elif status == 202 or status == 404:  # 404 - not exists - it is not fail in this case
      return self._wait(res['href'], rets)
    else:
      error('%s returned %d' % (rets, status))
      return False, rets

  def trash(self):
    req, code = self.CMD['trash']
    rets = 'trash'
    status, res = self._request(req)
    if status == code:
      return True, rets
    elif status == 202:
      return self._wait(res['href'], rets)
    else:
      error('%s returned %d' % (rets, status))
      return False, rets

  def move(self, pathfrom, pathto):
    req, code = self.CMD['move']
    rets = 'move %s %s' % (pathfrom, pathto)
    status, res = self._request(req, pathfrom, pathto)
    if status == code:
      return True, rets
    elif status == 202:
      return self._wait(res['href'], rets)
    else:
      error('%s returned %d' % (rets, status))
      return False, rets

  def copy(self, pathfrom, pathto):
    req, code = self.CMD['copy']
    rets = 'copy %s %s' % (pathfrom, pathto)
    status, res = self._request(req, pathfrom, pathto)
    if status == code:
      return True, rets
    elif status == 202:
      return self._wait(res['href'], rets)
    else:
      error('%s returned %d' % (rets, status))
      return False, rets

  def upload(self, lpath, path, ow=True):
    req, code = self.CMD['up']
    rets = 'up ' + path
    status, res = self._request(req, path, 'true' if ow else 'false')
    if status == code:
      try:
        with open(lpath, 'rb') as f:
          r = requests.put(res['href'], data = f)
        if r.status_code in (201, 200):
          return True, rets
      except FileNotFoundError:
        status = 'FileNotFoundError'
    error('%s returned %s' % (rets, str(status)))
    return False, rets

  def download(self, path, lpath):
    req, code = self.CMD['down']
    rets = 'down ' + path
    status, res = self._request(req, path)
    if status == code:
      r = requests.get(res['href'], stream=True)
      with open(lpath, 'wb') as f:
        for chunk in r.iter_content(2048):
          f.write(chunk)
      if r.status_code == 200:
        return True, rets
      else:
        status = r.status_code
    error('%s returned %d' % (rets, status))
    return False, rets
