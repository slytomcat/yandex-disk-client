#!/usr/bin/env python3
#
#  Cloud - low level yanex.disk REST API wraper
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

import requests
from time import sleep
from json import dumps
from logging import error

class Cloud(object):
  def __init__(self, token):
    # make headers for requests that require authorization
    self._headers = {'Accept': 'application/json', 'Authorization': token}

  BASEURL = 'https://cloud-api.yandex.net/v1/disk'
  # cmd : (method, url, success ret_code)
  CMD = {'info':  (requests.get, BASEURL + '?fields=total_space%2Ctrash_size%2Cused_space', 200),
         'last':  (requests.get, BASEURL + '/resources/last-uploaded?limit=10&fields=path', 200),
         'res':   (requests.get, BASEURL + '/resources?path={}'
                   '&fields=size%2Cmodified%2Csha256%2Cpath%2Ctype%2Ccustom_properties', 200),
         'list':  (requests.get, BASEURL + '/resources/files?limit={}&offset={}', 200),
         'prop':  (requests.patch, BASEURL + '/resources/?path={}'
                   '&fields=path%2Ccustom_properties', 200),
         'mkdir': (requests.put, BASEURL + '/resources?path={}', 201, ),
         'del':   (requests.delete, BASEURL + '/resources?path={}', 204),
         'trash': (requests.delete, BASEURL + '/trash/resources', 204),
         'move':  (requests.post, BASEURL + '/resources/move?path={}&from={}', 201),
         'copy':  (requests.post, BASEURL + '/resources/copy?path={}&from={}', 201),
         'up':    (requests.get, BASEURL + '/resources/upload?path={}&overwrite=true', 200),
         'down':  (requests.get, BASEURL + '/resources/download?path={}', 200)}

  def _request(self, cmd, *args, **kwargs):
    ''' format URL, perform request and handle asynchronous operations'''
    method, url, code = self.CMD[cmd]
    r = method(url.format(*args), **kwargs, headers=self._headers)
    status_code = r.status_code
    result = r.json() if r.text else ''
    if status_code == 202:  # it is asynchronous operation
      url = result['href']
      while True:
        sleep(0.777)  # reasonable pause between continuous requests
        r = requests.get(url, headers=self._headers)
        st = r.status_code
        res = r.json() if r.text else ''
        if st == 200:
          if res.get("status") == "success":
            status_code = code
            break
          if res.get("status") == "failed":
            status_code = 404
            result = {'error': 'FailedAsyncOperationError'}
            break
        else:
          status_code = st
          result = res
          break
    ok = status_code == code
    if not ok:
      result['code'] = status_code  # add status code into error description
    return ok, result

  def task(self, cmd, *args, **kwargs):
    '''
      Universal disk operation. It can be called with following parameters:
      - 'info'                    : to retrieve the common disk information,
      - 'last'                    : to retrieve 10 last updeted files,
      - 'res', path               : to retrieve file|folder properties,
      - 'list', <chunk>, <offset> : returns <chunk> files starting from <ofset> from full file list,
      - 'prop', path, pr=val,...  : to set custom properties for file/folder,
      - 'mkdir', path             : to create a new folder,
      - 'del', path               : to delete file/folder,
      - 'trash'                   : to clean the trash,
      - 'move', pathto, pathfrom  : to move file/foldet from pathfrom to pathto,
      - 'copy', pathto, pathfrom  : to move file/foldet from pathfrom to pathto,
      - 'up', path, localpath     : to upload file from localpath of local disk to path on cloud
      - 'down', path, localpath   : to download file from path on cloud to localpath on local disk

      It always return the tuple (status, result).
      When status True then result is the result of request. It varies for different operations:
      - dict with keys: total_space, trash_size, used_space                    : for 'info',
      - list of 10 paths                                                       : for 'last',
      - dict with keys: path, type, size, sha256, modified, custom_properties  : for 'res',
      - list of dicts like dict forres                                         : for 'list',
      - tuple (cmd, *args)                                                     : for all rest.

      If status False then it returns tuple(cmd, *args, error_dict), where error_dict contain
      at least 'code': <request status code>, 'error': <Error_identity_string>
    '''

    # handle input parameters
    if cmd in ('up', 'down'):
      # remove local path from args for upload and download operations
      lpath = args[1]
      args = (args[0],)
    elif cmd == 'prop':
      kwargs = {'data': dumps({"custom_properties": kwargs})}

    # perform request
    status, result = self._request(cmd, *args, **kwargs)

    # handle (pass) some errors
    if not status and cmd == 'mkdir' and result['error'] == 'DiskPathPointsToExistentDirectoryError':
      status = True

    # handle successful results and return results for successfully handled
    if status:

      # 'prop', 'mkdir', 'del', 'trash', 'move' and 'copy'
      if cmd in {'prop', 'mkdir', 'del', 'trash', 'move', 'copy'}:
        return status, (cmd, *args)

      # Upload
      elif cmd == 'up':
        try:  # try to open and upload file
          with open(lpath, 'rb') as f:
            # make secondary request to transfer data
            r = requests.put(result['href'], data = f)

        except OSError as e:
          # prepare error description for failed file/socket operation
          result = {'error': 'OSError', 'path': lpath, 'errno': e.errno, 'description': e.strerror}
        if r.status_code in (201, 200):
          return True, (cmd, *args)
        # prepare error description for secondary request
        result = r.json() if r.text else dict()
        result['code'] = r.status_code
        # do not return here, handle error in section below

      # Download
      elif cmd == 'down':
        # make secondary request to transfer data
        r = requests.get(result['href'], stream=True)
        # try open and write to local file
        try:
          with open(lpath, 'wb') as f:
            for chunk in r.iter_content(2048):
              f.write(chunk)
        except OSError as e:
          # prepare error description for failed file/socket operation
          result = {'code': -1, 'error': 'OSError', 'path': lpath,
                    'errno': e.errno, 'description': e.strerror}
        if r.status_code == 200:
          return True, (cmd, *args)
        # prepare error description for secondary request
        status = r.status_code
        result = r.json() if r.text else dict()
        # do not return here, handle error in section below

      # List
      elif cmd == 'list':
        items = result['items']
        result = []
        for i in items:
          item = {key: i[key] for key in ['path', 'type', 'modified', 'sha256', 'size']}
          item['path'] = item['path'][6:]  #.replace('disk:/', '')
          item['custom_properties'] = item.get('custom_properties')
          result.append(item)
        return True, result

      # Info
      elif cmd in 'info':
        return True, result

      # Last 10
      elif cmd == 'last':
        return True, [item['path'][6:] for item in result['items']]  #.replace('disk:/', '')

      # get file/path properties
      elif cmd == 'res':
        result['path'] = result['path'][6:]  #.replace('disk:/', '')
        result['custom_properties'] = result.get('custom_properties')
        return True, result

    # Handle errors
    error('%s(%s) returned %s' % (cmd, ', '.join(str(i) for i in args), str(result)))
    return False, (cmd, *args, result)
