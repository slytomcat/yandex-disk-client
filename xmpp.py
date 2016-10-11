#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  xmpp.py
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

import base64

# Token for notification service base64(login+\00+token)
#t = base64.urlsafe_b64encode(bytes(''.join([LOGIN, '\00', TOKEN]).encode('UTF8')))

import sleekxmpp

class xmppBot(sleekxmpp.ClientXMPP):
    def __init__(self, jid, password):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)

        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.message)

        self.register_plugin('xep_0030') # Service Discovery
        self.register_plugin('xep_0199') # ping


    def session_start(self, event):
        self.send_presence()
        self.get_roster()

    def message(self, msg):
        """respond to incoming messages"""
        pass


