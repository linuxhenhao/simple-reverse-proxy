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

server_static_root = './static/'
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
# selfresolve format
# {'host_name':ip_addrs_list}
# if there is more than one item in ip_addrs_list
# get one of the in random
selfresolve = {}  # replace scholar.google.com to google server's ip address in request uri directly
				  # and set host to "scholar.google.com " in request headers doesn't work
				  # So, google may has some request uri judge, We can only use self hosted dns server
				  # to return google's server address randomly , and maintain a list of google's server
				  # address in that dns server

filt_scholar_configs = {'scihub_host':scihub_self}
filt_scihub_configs = {'download_html':'download.html'}

util_log_level = logging.ERROR
logger_level = logging.DEBUG #proxy.py's log
gen_log_level = logging.ERROR
access_log_level = logging.ERROR
