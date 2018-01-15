#!/usr/bin/env python
#-*- coding:utf-8 -*-
import os,logging

#####################################
#
# host default means host(with port)
#
#####################################
https_enabled = True

server_root = os.path.dirname(__file__)
pwd = '/etc/tornadoproxy/'
if(os.path.exists('/etc/INDOCKER')): #in an docker container
    pwd = '/media/live/ipv4.thinkeryu.com/'
    fullchain_cert_path = pwd+'fullchain.pem'
    private_key_path = pwd+'privkey.pem'
else:
    fullchain_cert_path = pwd+'fullchain.pem'
    private_key_path = pwd+'privkey.pem'

server_name = '.*thinkeryu.com' #using in add_handler's host pattern for virtual host

# only handle get '/' for this host, any other host will not be accessed without
# any argments or additional path
main_host = 'scholar.thinkeryu.com'

server_static_root = server_root +'/static/'
#url replace rules
scihub_self = 'scihub.thinkeryu.com'

#rules_source original host with port and proto, selfhost only host with port
# port is optional
rules_source = [
('https://xue.glgoo.net', 'scholar.thinkeryu.com'),
('https://ipv4.google.com','ipv4.thinkeryu.com'),
('https://ipv6.google.com','ipv6.thinkeryu.com'),
('https://sci-hub.tw', scihub_self),
('https://scholar.googleusercontent.com','content.thinkeryu.com')
]

regexs4select_filter_source = {
        'https?://xue\.glgoo\..*': 'filt_scholar',
        'https?://ipv(4|6)\.google\..*': 'filt_ipv46',
        'https?://.*sci-hub\.tw': 'filt_scihub'
                }
data_sitekey ='6LfWzToUAAAAAAkKGSrsoG9DcFn_Z_f1cN5d9_Zk'
# allow_ipv6 option determines whethe to use ipv6 to
# resolve url in client.fetch
allow_ipv6 = True
# selfresolve format
# {'host_name':ip_addrs_list}
# if there is more than one item in ip_addrs_list
# get one of the in random
selfresolve = {'xue.glgoo.net': ["172.104.74.82"]}
# replace scholar.google.com to google server's
# ip address in request uri directly
# and set host to "scholar.google.com " in request headers doesn't work
# So, google may has some request uri judge, We
# can only use self hosted dns server
# to return google's server address randomly ,
# and maintain a list of google's server
# address in that dns server

filt_scholar_configs = {'scihub_host': scihub_self}
filt_scihub_configs = {'download_html': 'download.html'}

util_log_level = logging.ERROR
logger_level = logging.INFO  #proxy.py's log
gen_log_level = logging.ERROR
access_log_level = logging.ERROR

#### cloudflare ip list Detecter configs
cf_urls = ['https://www.cloudflare.com/ips-v4',
           'https://www.cloudflare.com/ips-v6']

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
