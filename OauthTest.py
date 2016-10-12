#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  OauthTest.py
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

import Oauth
from re import findall
if __name__ == '__main__':
  with open('OAuth.info', 'rt') as f:
    buf = f.read()
  ID = findall(r'AppID: (.*)', buf)[0].strip()
  secret = findall(r'AppSecret: (.*)', buf)[0].strip()

  token = Oauth.getToken(ID, secret)
  login = Oauth.getLogin(token)

  print(login, token)

