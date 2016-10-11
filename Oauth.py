# -*- coding: utf-8 -*-
#  OAuth - get the OAuth authorization token
#
#
from os import uname
from webbrowser import open_new as openNewBrowser
import requests

from gi import require_version
require_version('Gtk', '3.0')
from gi.repository import Gtk

_=str
HOST = uname().nodename
TOKEN = ''

def OAuthDialog():
    url = ('https://oauth.yandex.ru/authorize?'
           'response_type=code'                  # может быть сам token или code - для получения token через доп. запрос.
           '&client_id=389b4420fc6e4f509cda3b533ca0f3fd'              # идентификатор приложения
    #       '&device_id={device_id}'              # идентификатор устройства
           '&device_name=%s'%HOST +              # имя устройства - имя хоста
           '&display=popup'                      # popup - Признак облегченной верстки (без стандартной навигации Яндекса) для страницы разрешения доступа.
    #       '&login_hint={login_hint}'            # имя пользователя или электронный адрес
    #       '&force_confirm={force_confirm}'      # Признак того, что у пользователя обязательно нужно запросить разрешение на доступ к аккаунту (даже если пользователь уже разрешил доступ данному приложению).
    #       '&state={state}'                      # Строка состояния, которую Яндекс.OAuth возвращает без изменения. Максимальная допустимая длина строки — 1024 символа.
           )
    openNewBrowser(url)

    dlg=Gtk.Dialog(_('Yandex.Disk-indicator authorization'), flags=1)
    #self.set_icon(logo)
    dlg.set_border_width(6)
    dlg.add_button(_('Confirm'), Gtk.ResponseType.CLOSE)
    dialogBox = Gtk.VBox(spacing=5)
    label = Gtk.Label(_("The authorization page will be opened in your browser automatically. "
                        "If it doesn't happen then copy link below and paste into your"
                        " web-browser.\n" ))
    label.set_line_wrap(True)
    dialogBox.add(label)
    label = Gtk.Label(url)
    label.set_line_wrap(True)
    label.set_selectable(True)
    dialogBox.add(label)
    label = Gtk.Label(_("\nAfter authorization you'll receive the confirmation code."
                        " Put the code into the input box below and press Confirm\n\n"
                        "Put the confirmation code here:"))
    label.set_line_wrap(True)
    dialogBox.add(label)
    entry = Gtk.Entry()
    dialogBox.add(entry)

    dlg.get_content_area().add(dialogBox)
    dlg.show_all()
    dlg.run()

    CODE = entry.get_text()

    dlg.destroy()
    return CODE

while TOKEN == '':
  CODE = OAuthDialog()

  data = {'grant_type': 'authorization_code',
          'code': CODE,
          'client_id': '389b4420fc6e4f509cda3b533ca0f3fd',
          'client_secret': '5145f7a99e7943c28659d769752f6dae',
          'device_name': HOST
         }
  r = requests.post('https://oauth.yandex.ru/token', data)
  if r.status_code == 200:
    TOKEN = r.json()['access_token']

print(TOKEN)


