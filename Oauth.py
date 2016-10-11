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

def getToken(app_id, app_secret, gui=False):
  '''Receive access token via verification code that user can get on authorization page.

     Usage token = getAuth(app_id, app_secret, GUI)

     Interaction with user is performed via GUI (GUI=True) or via CLI (GUI=False or missed)
  '''
  host = uname().nodename
  token = ''
  msg1 = _("The authorization page will be opened in your browser automatically. If it"
           " doesn't happen then copy link below and paste into your web-browser.\n")
  msg2 = _("\nAfter authorization you'll receive the confirmation code. Put the code "
           "into the input box below and press Enter\n\n")
  msg3 = _("Enter the confirmation code here:")

  url = ('https://oauth.yandex.ru/authorize?'
           'response_type=code'                    # 'token' itself  or 'code' for token request
           '&client_id=%s' % app_id +              # application identificator
           '&display=popup'                        # popup - no additional decoration on the page
           '&device_name=%s' % (uname().nodename)  # device name (host name)
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
                       'code': code,
                       'client_id': app_id,
                       'client_secret': app_secret,
                       'device_name': host
                      })
    if r.status_code == 200:
      token = r.json()['access_token']
  return token

def getLogin(token):
  ''' Receive the user login - it is required for notification service
  '''
  r = requests.get('https://webdav.yandex.ru/?userinfo',
                   headers={'Accept': '*/*', 'Authorization': 'OAuth %s' % token})
  if r.status_code == 200:
    return re.findall(r'login:(.*)\n', r.text)[0]
  return None



if __name__ == '__main__':
  # application identity ???? I have no idea how to keep it from beeng compromised ????
  app_id = '389b4420fc6e4f509cda3b533ca0f3fd'
  app_secret = '5145f7a99e7943c28659d769752f6dae'

  TOKEN = getToken(app_id, app_secret)
  LOGIN = getLogin(TOKEN)

  print(TOKEN)
  print(LOGIN)

