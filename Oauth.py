# -*- coding: utf-8 -*-
#  OAuth - get the OAuth authorization token
#
#
from os import uname
from webbrowser import open_new as openNewBrowser
from gi import require_version
require_version('Gtk', '3.0')
from gi.repository import Gtk

def expand(url, params):
  '''It replaces '{key}' inside url onto 'value' basing on params dictionary ({'key':'value'}).
  '''
  for key, value in params.items():
    url = url.replace('{%s}' % key, value)
  return url

_=str

class OAuthDialog(Gtk.Dialog):
  def __init__(self):
    url = ('https://oauth.yandex.ru/authorize?'
           'response_type=code'                  # может быть сам token или code - для получения token через доп. запрос.
           '&client_id={client_id}'              # идентификатор приложения
    #       '&device_id={device_id}'              # идентификатор устройства
           '&device_name={device_name}'          # имя устройства - имя хоста
           '&display=popup'                      # popup - Признак облегченной верстки (без стандартной навигации Яндекса) для страницы разрешения доступа.
    #       '&login_hint={login_hint}'            # имя пользователя или электронный адрес
    #       '&force_confirm={force_confirm}'      # Признак того, что у пользователя обязательно нужно запросить разрешение на доступ к аккаунту (даже если пользователь уже разрешил доступ данному приложению).
    #       '&state={state}'                      # Строка состояния, которую Яндекс.OAuth возвращает без изменения. Максимальная допустимая длина строки — 1024 символа.
           '')

    params = {'client_id':'389b4420fc6e4f509cda3b533ca0f3fd'}
    params['device_name'] = uname().nodename
    URL = expand(redirect_url, params)
    #openNewBrowser(URL)
    Gtk.Dialog.__init__(self, _('Yandex.Disk-indicator authorization'), flags=1)
    #self.set_icon(logo)
    self.set_border_width(6)
    self.add_button(_('Confirm'), Gtk.ResponseType.CLOSE)

    # --- Indicator preferences tab ---
    dialogBox = Gtk.VBox(spacing=5)
    label = Gtk.Label(_("The authorization page will be opened in your browser automatically. "
                        "If it doesn't happen then copy link below and paste into your"
                        " web-browser.\n" ))
    label.set_line_wrap(True)
    dialogBox.add(label)
    label = Gtk.Label(URL)
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

    self.get_content_area().add(dialogBox)
    self.show_all()
    self.run()

    CODE = entry.get_text()

    self.destroy()
    return CODE


while TOKEN = '':
  CODE = OAuthDialog()
