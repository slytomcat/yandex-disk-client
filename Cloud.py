#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Cloud - cloud manipulation class
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

class Cloud(object):
  def __init__(self, token):
    # make headers for requests that require authorization
    self._headers = {'Accept': 'application/json', 'Authorization': token}

  def _expand(self, url, params):
    '''It replaces '{key}' inside url onto 'value' basing on params dictionary ({'key':'value'}).
    '''
    for key, value in params.items():
      url = url.replace('{%s}' % key, value)
    return url

  def _request(self, req, params=None):
    '''Perform the request with expanded URL via specified method using predefined headers
    '''
    method, url = req
    r = {'GET': requests.get,
         'PUT': requests.put,
         'DELETE': requests.delete,
         'POST': requests.post
        }[method](self._expand(url, params or {}), headers=self._headers)
    return r.status_code , r.json() if r.text else ''

  def _wait(self, res):
    '''waits for asynchronous operation completion '''
    while True:
      sleep(0.5)  # reasonable pause between continuous requests
      status, r = self._request((res['method'], res['href']))
      if status == 200:
        if r["status"] == "success":
          return True
        else:
          continue
      else:
        return False

  CMD = {'info':  (('GET',
                    'https://cloud-api.yandex.net:443/v1/disk'
                    '?fields=total_space%2Ctrash_size%2Cused_space%2Crevision'),
                   200),
         'last':  (('GET',
                    'https://cloud-api.yandex.net/v1/disk/resources/last-uploaded?limit=10'
                    '&fields=path'),
                   200),
         'res':   (('GET',
                    'https://cloud-api.yandex.net/v1/disk/resources?path={1}'
                    '&fields=size%2Cmodified%2Ccreated%2Csha256%2Cpath%2Ctype%2Crevision'),
                   200),
         'list':  (('GET',
                    'https://cloud-api.yandex.net/v1/disk/resources/files?limit=2147483647'),
                   200),
         'mkdir': (('PUT',
                    'https://cloud-api.yandex.net/v1/disk/resources?path={1}'),
                   201),
         'del':   (('DELETE',
                    'https://cloud-api.yandex.net/v1/disk/resources?path={1}&permanently={2}'),
                   204),
         'trash': (('DELETE',
                    'https://cloud-api.yandex.net:443/v1/disk/trash/resources'),
                   204),
         'move':  (('POST',
                    'https://cloud-api.yandex.net:443/v1/disk/resources/move?from={1}&path={2}'),
                   201),
         'copy':  (('POST',
                    'https://cloud-api.yandex.net:443/v1/disk/resources/copy?from={1}&path={2}'),
                   201),
         'up':    (('GET',
                    'https://cloud-api.yandex.net/v1/disk/resources/upload?path={1}&overwrite={2}'),
                   200),
         'down':  (('GET',
                    'https://cloud-api.yandex.net/v1/disk/resources/download?path={1}'),
                   200)}

  def getDiskInfo(self):
    '''Receives cloud disk status information'''
    req, code = self.CMD['info']
    status, res = self._request(req)
    if status == code:
      return res
    else:
      return False

  def getLast(self):
    '''Receives 10 last synchronized items'''
    req, code = self.CMD['last']
    status, res = self._request(req)
    if status == code:
      return [item['path'].replace('disk:/', '') for item in res['items']]
    else:
      return False

  def getResource(self, path):
    req, code = self.CMD['res']
    status, res = self._request(req, {'1': path})
    if status == code:
      res['path'] = res['path'].replace('disk:/', '')
      return res
    else:
      return False

  def getFullList(self):
    req, code = self.CMD['list']
    status, res = self._request(req)
    if status == code:
      # filter fields
      return [{key: i[key] if key != 'path' else i[key].replace('disk:/', '')
                   for key in ['size', 'modified', 'created', 'sha256', 'path', 'type']
              } for i in res['items']]
    else:
      return False

  def mkDir(self, path):
    req, code = self.CMD['mkdir']
    status, res = self._request(req, {'1': path})
    if status == code:
      return True
    else:
      return False

  def delete(self, path, perm=False):
    perm = 'true' if perm else 'false'
    req, code = self.CMD['del']
    status, res = self._request(req, {'1': path, '2': perm})
    if status == code:
      return True
    elif status == 202:
      return self._wait(res)
    else:
      return False

  def trash(self):
    req, code = self.CMD['trash']
    status, res = self._request(req)
    if status == code:
      return True
    elif status == 202:
      return self._wait(res)
    else:
      return False


  def move(self, pathfrom, pathto):
    req, code = self.CMD['move']
    status, res = self._request(req, {'1': pathfrom, '2': pathto})
    if status == code:
      return True
    elif status == 202:
      return self._wait(res)
    else:
      return False

  def copy(self, pathfrom, pathto):
    req, code = self.CMD['copy']
    status, res = self._request(req, {'1': pathfrom, '2': pathto})
    if status == code:
      return True
    elif status == 202:
      return self._wait(res)
    else:
      return False

  def upload(self, lpath, path, ow=True):
    ow = 'true' if ow else 'false'
    req, code = self.CMD['up']
    status, res = self._request(req, {'1': path,'2': ow})
    if status == code:
      with open(lpath, 'rb') as f:
        r = requests.put(res['href'], data = f)
      if r.status_code == 201:
        return True
    return False

  def download(self, path, lpath):
    req, code = self.CMD['mkdir']
    status, res = self._request(req, {'1': path})
    if status == code:
      r = requests.get(res['href'], stream=True)
      with open(lpath, 'wb') as f:
        for chunk in r.iter_content(1024):
          f.write(chunk)
      if r.status_code == 200:
        return True
    return False

if __name__ == '__main__':
  from re import findall
  with open('OAuth.info', 'rt') as f:
    token = findall(r'devtoken: (.*)', f.read())[0].strip()
  c = Cloud(token)
  print('\nDisk Info:', c.getDiskInfo(), '\n')
  print('\nNew dir:', c.mkDir('testdir'), '\n')
  print('\nMove dir:', c.move('testdir', 'newtestdir'), '\n')
  print('\nDir info:', c.getResource('newtestdir'), '\n')
  print('\nFile info:', c.getResource('Bears.jpg'), '\n')
  print('\nDelete Dir:', c.delete('newtestdir'), '\n')
  print('\nCopy big Dir:', c.copy('Music', 'MusicTest'), '\n')
  print('\nMove big Dir:', c.move('MusicTest', 'MusicTest2'), '\n')
  print('\nDelete big Dir:', c.delete('MusicTest2'), '\n')
  print('\nDisk Info:', c.getDiskInfo(), '\n')
  print('\nEmpty trash:', c.trash(), '\n')
  print('\nDisk Info:', c.getDiskInfo(), '\n')
  print('\nLast:', c.getLast(), '\n')
  print('\nFull list:', c.getFullList(), '\n')
  print('\nUpload:', c.upload('README.md', 'README_.md'), '\n')
  print('\nDownload:', c.download('README_.md', 'README_.md'), '\n')
  print('\nDelete file:', c.delete('README_.md'), '\n')



