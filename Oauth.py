#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  OAuth - get the OAuth authorization token
#
#
from os import uname
from subprocess import call, DEVNULL
import requests
import re

from gi import require_version
require_version('Gtk', '3.0')
from gi.repository import Gtk

_ = str   # temporary replacement for localization functionality

def getToken(GUI=False):
  '''Receives access token via verification code that user can see on authorization page.
     Additionally it receives the user login name

     Usage token, login = getAuth(UI)

     Interaction with user is performed via GUI (UI=True) or via CLI (UI=False or missed)'''

  HOST = uname().nodename
  TOKEN = ''
  msg1 = _("The authorization page will be opened in your browser automatically. If it"
           " doesn't happen then copy link below and paste into your web-browser.\n")
  msg2 = _("\nAfter authorization you'll receive the confirmation code. Put the code "
           "into the input box below and press Enter\n\n")
  msg3 = _("Put the confirmation code here:")

  url = ('https://oauth.yandex.ru/authorize?'
           'response_type=code'                  # 'token' itself  or 'code' for token request
           '&client_id=389b4420fc6e4f509cda3b533ca0f3fd'              # App ID
    #       '&device_id={device_id}'              # Device ID
           '&display=popup'                      # popup - no additional decoration on the page
           '&device_name=%s'%HOST                # Device name (Host name)
    #       '&login_hint={login_hint}'            # user name or e-mail
    #       '&force_confirm={force_confirm}'      # Force the access confirmation (if already have)
    #       '&state={state}'                      # 1024 symbols returnable value (CSRF protection)
        )
  while TOKEN == '':
    call(['xdg-open', url], stdout=DEVNULL, stderr= DEVNULL)

    if GUI:
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
      CODE = entry.get_text();     dlg.destroy()
    else:
      print(msg1)
      print(url)
      print(msg2)
      CODE = input(msg3)
    r = requests.post('https://oauth.yandex.ru/token',
                      {'grant_type': 'authorization_code',
                       'code': CODE,
                       'client_id': '389b4420fc6e4f509cda3b533ca0f3fd',
                       'client_secret': '5145f7a99e7943c28659d769752f6dae',
                       'device_name': HOST
                      })
    if r.status_code == 200:
      TOKEN = r.json()['access_token']

  return TOKEN

def getLogin(token):
  # Receive the user login - it is required for notification service
  r = requests.get('https://webdav.yandex.ru/?userinfo',
                   headers={'Accept': '*/*', 'Authorization': 'OAuth %s' % TOKEN})
  login = re.findall(r'login:(.*)\n', r.text)[0]
  return login



if __name__ == '__main__':
  #TOKEN = getToken()

  TOKEN = 'AQAAAAAUgLEfAAOGGV4LyRANGEgGv-oUde5AubE'

  LOGIN = getLogin(TOKEN)

  print(TOKEN)
  print(LOGIN)

