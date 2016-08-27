#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# Copyright (C) 2012 Free Software Fundation

# auteur : pzia

import requests
import re
import sys
import time
import imaplib, email, email.utils
import json, pprint
import base64

class RC2Imap(object):
    portalUrlLogin = "https://foo"
    rcUrlLogin = "https://foo/bar"
    portalUrlLoginGet = {
        'op' : 'c',
        #This url is the roundcube url base-64 encoded
        'url' : 'aHR0cHM6Ly9mb28vYmFy'
        }
    portalUrlLoginPost = {
        'valide':'on',
        #This url is the roundcube url base-64 encoded
        'url':'aHR0cHM6Ly9mb28vYmFy',
        'identifiant':'prenom.nom',
        'secret':'motdepasse',
        'apply':'Connexion'
        }
    rcUrlLoginGet = {
        '_task':'login',
        '_action':'login',
        '_timezone':'1',
        '_dstactive':'1',
        '_user':'prenom.nom',
        '_pass':'motdepasse'
        }
    rcUrlMailGet = { #These are the basics parameters for rc mail interactions
        '_task':'mail',
        '_action':'list',
        '_mbox':'INBOX',
        '_refresh':'1',
        '_remote':'1',
        '_unlock':"loading%d000" % 1345387133,
        '_':"%d050" % 1345387133,
        }

    def __init__(self, login, pwd, portal, roundcube):
        super(RC2Imap, self).__init__()
        #initialise les variables
        self.portalAuthLogin = login
        self.portalAuthPass = pwd
        self.portalUrlLogin = portal
        self.rcUrlLogin = roundcube

        self.portalUrlLoginPost['identifiant'] = login
        self.portalUrlLoginPost['secret'] = pwd
        self.portalUrlLoginPost['url'] = base64.encode(roundcube)

        self.rcUrlLoginGet['_user'] = login
        self.rcUrlLoginGet['_pass'] = pwd
        self.rcUrlLoginGet['url'] = base64.encode(roundcube)
        self.session = requests.session()
        
    def loginPortail(self):
        """Login to PIGP"""
        r = self.session.post(self.portalUrlLogin, data = self.portalUrlLoginPost, params = self.portalUrlLoginGet)

    def loginRc(self):
        """Login to RC, and initialise rcHeaders"""
        #Récupère le token de login
        r2 = self.session.get(self.rcUrlLogin)
        m = re.search(r'_token"\s+value="([a-z0-9]+)"', r2.content)
        token = m.group(1)
        self.rcUrlLoginGet['_token'] =token
        #Se loggue
        r2 = self.session.post(self.rcUrlLogin, data = self.rcUrlLoginGet)

        #Récupère le token de session
        r2 = self.session.post(self.rcUrlLogin, params = {'_task':'mail'})
        m = re.search(r'"request_token":"([a-z0-9]+)"}', r2.content)
        token = m.group(1)
        self.rcHeaders = {'X-Roundcube-Request': token}
        
    def rcAction(self, action, more = {}):
        """Retourne un objet url"""
        param = self.rcUrlMailGet.copy()
        now = int(time.time())+1
        param['_action'] = action
        param['_unlock'] = "loading%d000" % now
        param['_'] = "%d050" % now
        param.update(more)
        r = self.session.get(self.rcUrlLogin, params = param, headers = self.rcHeaders)
        return r
 
    def rcListMessages(self, page = 1):
        l = self.rcAction('list', {"_page" : page})
        print(l.url)
#        print(l.content)
        commit_data = json.loads(l.content)
        pagecount = commit_data['env']['pagecount']
        print(pagecount)
        m = re.findall(r'add_message_row\((\d+)', l.content)
        return m

    def rcGetMessage(self, uid):
        """Get a mail message from roundcube by uid"""
        l = self.rcAction("viewsource", {'_uid' : uid})
#        print(l.text)
        try :
            msg = email.message_from_string(l.text.encode('utf-8'))
        except Exception as e:
            print(e)
            print(l.text)     
            sys.exit()
        return msg

    
if __name__ == '__main__':
    portal = RC2Imap('premnom.nom', 'password')
    portal.loginPortail()
    portal.loginRc()
    loop = True
    page = 1
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login('gmail.prefixe', 'password')
    mail.select("inbox") # connect to inbox.

    while 1 :
        m = portal.rcListMessages(page)
        if len(m) == 0:
            break
#    pprint.pprint(m)
        for uid in m:
            msg = portal.rcGetMessage(uid)
            ed = msg.get('Date')
            msg['Object'] = "FOOTEST%s" % msg.get('Object')
            print uid, ed
#    pprint.pprint(ed)
            tuppledate = email.utils.parsedate_tz(ed)
#    pprint.pprint(tuppledate)
    #FIXME: le traitement de la date n'est pas complet (?)
#            mail.append('INBOX', '', imaplib.Time2Internaldate(tuppledate[:9]), msg.as_string(True))
        page += 1


    mail.close()
    mail.logout()
