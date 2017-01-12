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
selfresolve = {'scholar.google.com':
        [
            "218.189.25.129",
            "218.189.25.178",
            "93.123.23.1",
            "93.123.23.27",
            "197.199.253.45",
            "197.199.253.52",
            "218.253.0.156",
            "218.253.0.169",
            "111.92.162.23",
            "111.92.162.54",
            "218.176.242.4",
            "218.176.242.44",
            "218.176.242.39",
            "218.176.242.75",
            "218.176.242.247",
            "103.25.178.17",
            "103.25.178.29",
            "203.116.165.186",
            "203.116.165.204",
            "123.205.250.100",
            "123.205.250.136",
            "163.28.83.149",
            "163.28.83.187",
            "1.179.248.142",
            "1.179.248.161",
            "118.174.25.7",
            "118.174.25.75",
        ]
        }

filt_scholar_configs = {'scihub_host':scihub_self}
filt_scihub_configs = {'download_html':'download.html'}

util_log_level = logging.ERROR
logger_level = logging.DEBUG #proxy.py's log
gen_log_level = logging.ERROR
access_log_level = logging.ERROR
