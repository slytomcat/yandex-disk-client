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
    self._headers = {'Accept': 'application/hal+json', 'Authorization': token}

  def _expand(self, url, params):
    '''It replaces '{key}' inside url onto 'value' basing on params dictionary ({'key':'value'}).
    '''
    for key, value in params.items():
      url = url.replace('{%s}' % key, value)
    return url

  def _request(self, method, url, params=None):
    '''Perform the request with expanded URL via specified method using predefined headers
    '''
    r = {'GET': requests.get,
         'PUT': requests.put,
         'DELETE': requests.delete,
         'POST': requests.post
        }[method](self._expand(url, params or {}), headers=self._headers)
    return r.status_code , r.json() if r.text else ''

  def _wait(self, res):
    '''waits for asynchronous operation completion'''
    while True:
      sleep(0.5)  # reasonable pause between continuous requests
      status, r = self._request(res['method'], res['href'])
      if status == 200:
        if r["status"] == "success":
          return True
        else:
          continue
      else:
        return False

  def getDiskInfo(self):
    '''Receives cloud disk status information'''
    status, res = self._request('GET', 'https://cloud-api.yandex.net:443/v1/disk')
    if status == 200:
      # Remove unnecessary info
      del res['system_folders']
      del res['is_paid']
      return res
    else:
      return False

  def getLast(self):
    '''Receives 10 last uploaded items'''
    status, res = self._request('GET',
                                'https://cloud-api.yandex.net/v1/disk/resources/last-uploaded?'
                                          'limit=10')
    if status == 200:
      items = []
      for item in res['items']:
        items.append(item['name'])
      return items
    else:
      return False


  def getResource(self, path):
    status, res = self._request('GET',
                                'https://cloud-api.yandex.net/v1/disk/resources?path={path}',
                                {'path': path})
    if status == 200:
      # Remove unnecessary info
      del res['_links']
      res.setdefault('preview', '')
      del res['preview']
      return res
    else:
      return False

  def getFullList(self):
    status, res = self._request('GET', 'https://cloud-api.yandex.net/v1/disk/resources/files?'
                                          'limit=2147483647')
    if status == 200:
      for item in res['items']:
        # Remove unnecessary info
        del item['_links']
        item.setdefault('preview', '')
        del item['preview']
      return res['items']
    else:
      return False

  def mkDir(self, path):
    status, res = self._request('PUT',
                                'https://cloud-api.yandex.net/v1/disk/resources?path={path}',
                                {'path': path})
    if status == 201:
      return True
    else:
      return False

  def delete(self, path, perm=False):
    perm = 'true' if perm else 'false'
    status, res = self._request('DELETE',
                                'https://cloud-api.yandex.net/v1/disk/resources?path={path}'
                                                                       '&permanently={perm}',
                                {'path': path, 'perm': perm})
    if status == 204:
      return True
    elif status == 202:
      return self._wait(res)
    else:
      return False

  def trash(self):
    status, res = self._request('DELETE',
                                'https://cloud-api.yandex.net:443/v1/disk/trash/resources')
    if status == 204:
      return True
    elif status == 202:
      return self._wait(res)
    else:
      return False


  def move(self, pathfrom, pathto):
    status, res = self._request('POST',
                                'https://cloud-api.yandex.net:443/v1/disk/resources/move?'
                                       'from={from}&path={to}',
                                {'from': pathfrom, 'to': pathto})
    if status == 201:
      return True
    elif status == 202:
      return self._wait(res)
    else:
      return False

  def copy(self, pathfrom, pathto):
    status, res = self._request('POST',
                                'https://cloud-api.yandex.net:443/v1/disk/resources/copy?'
                                        'from={from}&path={to}',
                              {'from': pathfrom, 'to': pathto})
    if status == 201:
      return True
    elif status == 202:
      return self._wait(res)
    else:
      return False

  def upload(self, lpath, path, ow=True):
    ow = 'true' if ow else 'false'
    status, res = self._request('GET',
                                'https://cloud-api.yandex.net/v1/disk/resources/upload?'
                                          'path={path}&overwrite={ow}',
                                {'path': path,'ow': ow})
    if status == 200:
      with open(lpath, 'rb') as f:
        r = requests.put(res['href'], data = f)
      if r.status_code == 201:
        return True
    return False

  def download(self, path, lpath):
    status, res = self._request('GET',
                                'https://cloud-api.yandex.net/v1/disk/resources/download?'
                                          'path={path}',
                                {'path': path})
    if status == 200:
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



