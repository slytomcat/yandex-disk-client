#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# source: https://habrahabr.ru/company/yandex/blog/227377/
# modified by Sly_tom_cat:
#  - switch from httplib to http.client (python3)
#  - switch from uritemplate.expand to simple inline function
#
# При использовании гиперссылок пропадает необходимость вручную собирать URL и беспокоиться
# о параметрах запроса и без того известных объекту, над которым выполняется операция.
#
#

#from httplib import HTTPSConnection
#from http.client import HTTPSConnection
#import json
import requests
#from uritemplate import expand

def expand(url, params):
  '''It replaces '{key}' inside url onto 'value' basing on params dictionary ({'key':'value'}).
  '''
  for key, value in params.items():
    url = url.replace('{%s}' % key, value)
  return url

TOKEN = 'AQAAAAAUgLEfAAOGGV4LyRANGEgGv-oUde5AubE'
headers = {'Accept': 'application/hal+json', 'Authorization':TOKEN}

def request(method, url, params=None):
    url = expand(url, params or {})
    r = {'GET': requests.get,
         'PUT': requests.put,
         'DELETE': requests.delete,
         'POST': requests.post
        }[method](url, headers=headers)
    obj = r.json() if r.text else None
    status = r.status_code
    if status == 201:
        # get the object by received reference
        status, obj = request(obj['method'], obj['href'])
    return status, obj

def do(resource, action, params=None):
    link = resource['_links'][action]
    _, obj = request(link['method'], link['href'], params)
    return obj


if __name__ == '__main__':
    # создаём папку
    _, folder = request('PUT',
                        expand('https://cloud-api.yandex.net/v1/disk/resources?path={path}',
                               {'path': '/foo'}))
    print('folder created')

    print(folder)


    # перемещаем папку и получаем перемещённую
    folder = do(folder, 'move', {'path': '/bar'})
    print('folder moved')

    print(folder)


    # копируем папку и получаем новую папку
    folder_copy = do(folder, 'copy', {'path': '/foobar'})
    print('folder copied')


    # удаляем папки
    do(folder, 'delete')
    do(folder_copy, 'delete')
    print('folders are deleted')
