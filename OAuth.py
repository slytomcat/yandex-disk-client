#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  OAuth - get the OAuth authorization token
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
#

from os import uname
from subprocess import call, DEVNULL
import requests
from re import findall

from gi import require_version
require_version('Gtk', '3.0')
from gi.repository import Gtk

_ = str   # temporary replacement for localization functionality

def getToken(app_id, app_secret, gui=False):
  '''Receive access token via verification code that user can get on authorization page.

     Usage token = getAuth(app_id, app_secret, GUI)

     Interaction with user is performed via GUI (GUI=True) or via CLI (GUI=False or missed)
  '''
  host = uname().nodename
  token = ''
  msg1 = _("The authorization page will be opened in your browser automatically. If it"
           " doesn't happen then copy link below and paste into your web-browser.\n")
  msg2 = _("\nAfter authorization you'll receive the confirmation code. Copy/paste the code "
           "below and press Enter\n\n")
  msg3 = _("Enter the confirmation code here: ")

  url = ('https://oauth.yandex.ru/authorize?' + '&'.join((
           'response_type=code',                  # 'token' itself  or 'code' for token request
           'client_id=%s' % app_id,               # application identificator
           #'device_name=%s' % uname().nodename)), # device name (host name)
           'display=popup' ))                     # popup - no additional decoration on the page
        )
  while token == '':
    call(['xdg-open', url], stdout=DEVNULL, stderr= DEVNULL)
    if gui:
      dlg=Gtk.Dialog(_('Yandex.Disk-indicator authorization'), flags=1)
      #self.set_icon(logo)
      dlg.set_border_width(6)
      dlg.add_button(_('Enter'), Gtk.ResponseType.CLOSE);   dialogBox = Gtk.VBox(spacing=5)
      label = Gtk.Label(msg1);   label.set_line_wrap(True);   dialogBox.add(label)
      label = Gtk.Label(url);    label.set_line_wrap(True);   label.set_selectable(True)
      dialogBox.add(label)
      label = Gtk.Label(msg2 + msg3);  label.set_line_wrap(True);   dialogBox.add(label)
      entry = Gtk.Entry();         dialogBox.add(entry);      dlg.get_content_area().add(dialogBox)
      dlg.show_all();              dlg.run()
      code = entry.get_text();     dlg.destroy()
    else:
      print(msg1, '\n', url, '\n', msg2)
      code = input(msg3)
    r = requests.post('https://oauth.yandex.ru/token',
                      {'grant_type': 'authorization_code',
                       #'device_name': uname().nodename,
                       'code': code,
                       'client_id': app_id,
                       'client_secret': app_secret
                      })
    if r.status_code == 200:
      token = r.json()['access_token']
  return token

def getLogin(token):
  ''' Receive the user login by token.
  '''
  r = requests.get('https://webdav.yandex.ru/?userinfo',
                   headers={'Accept': '*/*', 'Authorization': 'OAuth %s' % token})
  if r.status_code == 200:
    return findall(r'login:(.*)\n', r.text)[0]
  return None

if __name__ == '__main__':
  '''Test ID and secret have to be stored in file 'OAuth.info' in following format:
         AppID: <Application ID>
         AppSecret: <Application password>
  '''
  with open('OAuth.info', 'rt') as f:
    buf = f.read()
  ID = findall(r'AppID: (.*)', buf)[0].strip()
  secret = findall(r'AppSecret: (.*)', buf)[0].strip()

  token = getToken(ID, secret)
  login = getLogin(token)
  print(login, token)

  '''Test token have to be stored in file 'OAuth.info' in following format:
         API_TOKEN: <OAuth token>
  '''
  re.sub(r'API_TOKEN: \S*', 'devtoken: %s' % token, buf)
  with open('OAuth.info', 'wt') as f:
    f.write(buf)
