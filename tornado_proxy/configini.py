#!/usr/bin/env python
#-*- coding:utf-8 -*-
import os,logging

https_enabled = True

server_root = os.path.dirname(os.path.realpath(__file__))+'/'
pwd = server_root
if(os.path.exists('/etc/INDOCKER')): #in an docker container
    pwd = '/media/'
    fullchain_cert_path = pwd+'fullchain.pem'
    private_key_path = pwd+'privkey.pem'
else:
    fullchain_cert_path = pwd+'fullchain.pem'
    private_key_path = pwd+'privkey.pem'

server_name = '.*thinkeryu.com' #using in add_handler's host pattern for virtual host

server_static_root = server_root +'/static/'
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
logger_level = logging.INFO #proxy.py's log
gen_log_level = logging.ERROR
access_log_level = logging.ERROR


#--------------------------------------------------------------------------
class DNSServerSettings:
    def __init__(self):
# debug flag for running dns name server
# set to True to show more debug messages
        self.debug = False
# the number of threads(dns query or ssl service check) running concurrently
        self.threads = 100

# the maximum number of dns servers to query in a certain country
        self.servers = 800

# Set the proxies to access public dns website if this variable is not None
        self.proxies = None
#proxies = {
#    'http': 'http://127.0.0.1:8087',
#    'https': 'http://127.0.0.1:8087',
#}
# upper dns name server
        self.upper_dns_server = "208.67.222.123" #openDNS's server
# dns server bind address
        self.bind_tuple = ("172.17.0.1",53) #for docker container
dns_settings = DNSServerSettings()
