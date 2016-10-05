#!/usr/bin/env python
#-*- coding:utf-8 -*-
import os,logging

https_enabled = True

pwd = os.path.dirname(os.path.realpath(__file__))+'/'

if(os.path.exists('/etc/INDOCKER')): #in an docker container
    pwd = '/media/'
    fullchain_cert_path = pwd+'fullchain1.pem'
    private_key_path = pwd+'privkey1.pem'
else:
    fullchain_cert_path = pwd+'fullchain1.pem'
    private_key_path = pwd+'privkey1.pem'

server_name = '.*thinkeryu.com' #using in add_handler's host pattern for virtual host

#url replace rules
scihub_self = 'scihub.thinkeryu.com'

rules_source = [
('https://scholar.google.com', 'scholar.thinkeryu.com'),
('https://ipv4.google.com','ipv4.thinkeryu.com'),
('http://sci-hub.bz', scihub_self)
]

regexs4select_filter_source = {'https?://scholar\.google\..*':'filt_scholar',
                'https?://ipv4\.google\..*':'filt_ipv4',
                'https?://.*sci-hub\.bz':'filt_scihub'}
selfresolve = {'g.scihub.tk':'199.195.251.240'}

filt_scholar_configs = {'scihub_host':scihub_self}
filt_scihub_configs = {'download_html':'download.html'}

util_loglevel = logging.DEBUG
