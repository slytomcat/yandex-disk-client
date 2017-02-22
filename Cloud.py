#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

class Cloud(object):
  def __init__(self, token):
    # make headers for requests that require authorization
    self._headers = {'Accept': 'application/json', 'Authorization': token}

  def _request(self, req, *args, dt=None):
    '''Perform the request with expanded URL via specified method using predefined headers
    '''
    method, url = req
    r = method(url.format(*args), data=dt, headers=self._headers)
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

  def _wait(self, url, path):
    '''waits for asynchronous operation completion '''
    while True:
      sleep(0.5)  # reasonable pause between continuous requests
      status, r = self._request((requests.get, url))
      if status == 200:
        if r["status"] == "success":
          return True, path
        else:
          continue
      else:
        print('Async op [on "%s"] returned %d' % (path, status))
        return False, path

  def getDiskInfo(self):
    '''Receives cloud disk status information'''
    req, code = self.CMD['info']
    status, res = self._request(req)
    if status == code:
      return True, res
    else:
      print('Info returned %d' % status)
      return False, status

  def getLast(self):
    '''Receives 10 last synchronized items'''
    req, code = self.CMD['last']
    status, res = self._request(req)
    if status == code:
      return True, [item['path'].replace('disk:/', '') for item in res['items']]
    else:
      print('Last10 returned %d' % status)
      return False, ''

  def getResource(self, path):
    req, code = self.CMD['res']
    status, res = self._request(req, path)
    if status == code:
      res['path'] = res['path'].replace('disk:/', '')
      if res.get('items', False):   # remove items form directory resource info
        del res['items']
      return True, res
    else:
      print('Resource %s returned %d' % (path, status))
      return False, path

  def setProps(self, path, **props):
    req, code = self.CMD['prop']
    status, res = self._request(req, path, dt=dumps({"custom_properties": props}))
    if status == code:
      return True, res
    else:
      print('setProp returned %d' % status)
      return False, ''

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
      print('List returned %d' % status)
      return False, ''

  def mkDir(self, path):
    req, code = self.CMD['mkdir']
    status, res = self._request(req, path)
    if status == code:
      return True, path
    else:
      print('MkDir %s returned %d' % (path, status))
      return False, path

  def delete(self, path, perm=False):
    req, code = self.CMD['del']
    status, res = self._request(req, path, 'true' if perm else 'false')
    if status == code:
      return True, path
    elif status == 202:
      return self._wait(res['href'], path)
    else:
      print('Delete %s returned %d' % (path, status))
      return False, path

  def trash(self):
    req, code = self.CMD['trash']
    status, res = self._request(req)
    if status == code:
      return True, ''
    elif status == 202:
      return self._wait(res['href'], '')
    else:
      print('Trash clean returned %d' % status)
      return False, ''

  def move(self, pathfrom, pathto):
    req, code = self.CMD['move']
    status, res = self._request(req, pathfrom, pathto)
    if status == code:
      return True, pathto
    elif status == 202:
      return self._wait(res['href'], pathto)
    else:
      print('Move %s to %s returned %d' % (pathfrom, pathto, status))
      return False, pathto

  def copy(self, pathfrom, pathto):
    req, code = self.CMD['copy']
    status, res = self._request(req, pathfrom, pathto)
    if status == code:
      return True, pathto
    elif status == 202:
      return self._wait(res['href'], pathto)
    else:
      print('Copy %s to %s returned %d' % (pathfrom, pathto, status))
      return False, pathto

  def upload(self, lpath, path, ow=True):
    req, code = self.CMD['up']
    status, res = self._request(req, path, 'true' if ow else 'false')
    if status == code:
      try:
        with open(lpath, 'rb') as f:
          r = requests.put(res['href'], data = f)
        if r.status_code in (201, 200):
          return True, path
      except FileNotFoundError:
        status = 'FileNotFoundError'
    print('Upload of %s returned %s' % (path, str(status)))
    return False, path

  def download(self, path, lpath):
    req, code = self.CMD['down']
    status, res = self._request(req, path)
    if status == code:
      r = requests.get(res['href'], stream=True)
      with open(lpath, 'wb') as f:
        for chunk in r.iter_content(2048):
          f.write(chunk)
      if r.status_code == 200:
        return True, path
      else:
        status = r.status_code
    print('Download of %s returned %d' % (path, status))
    return False, path

if __name__ == '__main__':
  from os import remove

  def getToken():
    from re import findall
    '''Local test token have to be store_requestd in file 'OAuth.info' with following format:
           devtoken:  <OAuth token>
    '''
    try:
      with open('OAuth.info', 'rt') as f:
        token = findall(r'devtoken: (.*)', f.read())[0].strip()
        #print ('Token: %s'%(token))
    except:
      ''' CircleCi token is in the environment variable API_TOKEN
      '''
      from os import getenv
      token = getenv('API_TOKEN')

    return token

  c = Cloud(getToken())
  res = []
  res.append(c.getDiskInfo())
  print('\nDisk Info:', res[-1], '\n')
  res.append(c.mkDir('testdir'))
  print('\nNew dir:', res[-1], '\n')
  res.append(c.move('testdir', 'newtestdir'))
  print('\nMove dir:', res[-1], '\n')
  res.append(c.getResource('newtestdir'))
  print('\nDir info:', res[-1], '\n')
  res.append(c.getResource('Bears.jpg'))
  print('\nFile info:', res[-1], '\n')
  res.append(c.setProps('Sea.jpg', uid=1000, gid=1000, mod=33204))
  print('\nSetProps:', res[-1], '\n')
  res.append(c.getResource('Sea.jpg'))
  print('\nFile info:', res[-1], '\n')
  res.append(c.delete('newtestdir'))
  print('\nDelete Dir:', res[-1], '\n')
  res.append(c.copy('Music', 'MusicTest'))
  print('\nCopy big Dir:', res[-1], '\n')
  res.append(c.move('MusicTest', 'MusicTest2'))
  print('\nMove big Dir:', res[-1], '\n')
  res.append(c.delete('MusicTest2'))
  print('\nDelete big Dir:', res[-1], '\n')
  res.append(c.getDiskInfo())
  print('\nDisk Info:', res[-1], '\n')
  res.append(c.trash())
  print('\nEmpty trash:', res[-1], '\n')
  res.append(c.getDiskInfo())
  print('\nDisk Info:', res[-1], '\n')
  res.append(c.getLast())
  print('\nLast:', res[-1], '\n')
  res.append(c.getList(chunk=5))
  print('\nGet list:', res[-1], '\n')
  res.append(c.upload('README.md', 'README_.md'))
  print('\nUpload:', res[-1], '\n')
  res.append(c.download('README_.md', 'README_.md'))
  print('\nDownload:', res[-1], '\n')
  res.append(c.delete('README_.md'))
  print('\nDelete file:', res[-1], '\n')
  remove('README_.md')
  for stat, _ in res:
    if not stat:
      raise NameError('Something wrong with it.')
  '''
  '''
