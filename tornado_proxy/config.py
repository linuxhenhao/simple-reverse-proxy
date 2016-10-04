#!/usr/bin/env python
#-*- coding:utf-8 -*-

#
# configuration file
#
import re,util
import os

https_enabled = True

pwd = os.path.dirname(os.path.realpath(__file__))+'/'

if(os.path.exists('/etc/INDOCKER')): #in an docker container
    pwd = '/etc/media/'
    fullchain_cert_path = pwd+'fullchain1.pem'
    private_key_path = pwd+'privkey1.pem'
else
    fullchain_cert_path = pwd+'fullchain1.pem'
    private_key_path = pwd+'privkey1.pem'

server_name = '.*thinkeryu.com' #using in add_handler's host pattern for virtual host

#url replace rules
scihub_self = 'scihub.thinkeryu.com'

rules_source = [
('https://scholar.google.com', 'scholar.thinkeryu.com'),
('https://ipv4.google.com',' ipv4.thinkeryu.com'),
('http://sci-hub.bz', scihub_self)
]

regexs4select_filter_source = {'https?://scholar\.google\..*':'filt_scholar',
                'https?://ipv4\.google\..*':'filt_ipv4',
                'https?://.*sci-hub\.bz':'filt_scihub'}
selfresolve = {'g.scihub.tk':'199.195.251.240'}

filt_scholar_configs = {'scihub_host':scihub_self}
filt_scihub_configs = {'download_html':'download.html'}

class getHostError(Exception):
    def __init__(self,error_message):
        self.error_message = error_message

    def __str__(self):
        return repr(sefl.error_message)

class configurations:
    def __init__(self,https_enabled, fullchain_cert_path, private_key_path, server_name,rules_source,regexs,selfresolve,**kwargs):
        self._https_enabled = https_enabled
        if(https_enabled):
            self._selfhost_proto = 'https'
        else:
            self._selfhost_proto = 'http'
        self._fullchain_cert_path = fullchain_cert_path
        self._private_key_path = private_key_path
        self._server_name = server_name
        self._rules_source = rules_source
        self._regexs4select_filter_source = regexs
        self._selfresolve = selfresolve
        self._gen_regexs4select_filter()
        self._gen_replace_rules() #generate two dict from rules_source
                                  #add to self.replace_to_xxx
        self._gen_configs_for_filters(**kwargs)
    @property
    def https_enabled(self):
        copy = self._https_enabled
        return copy

    @property
    def fullchain_cert_path(self):
        copy = self._fullchain_cert_path
        return copy

    @property
    def private_key_path(self):
        copy = self._private_key_path
        return copy

    @property
    def host_proto(self):
        copy = self._selfhost_proto
        return copy

    @property
    def selfresolve(self):
        return self._selfresolve.copy()

    @property
    def server_name(self):
        copy = self._server_name
        return server_name

    @property
    def regexs4select_filter(self):
        return self._regexs4select_filter.copy()

    @property
    def replace_to_selfhost_rules(self):
        return self._replace_to_seflhost_rules.copy()

    @property
    def replace_to_originalhost_rules(self):
        return self._replace_to_originalhost_rules.copy()

    def get_configs_for_filter(self,filter_name):
        try:
            return getattr(self,'_'+filter_name).copy()
        except:
            return None

    def _gen_regexs4select_filter(self):
        self._regexs4select_filter = dict()
        for regex_pattern,filt_name in self._regexs4select_filter_source.items():
            self._regexs4select_filter[re.compile(regex_pattern)] = filt_name

    def _gen_replace_rules(self):
        self._replace_to_seflhost_rules = dict()
        self._replace_to_originalhost_rules = dict()

        for origin,selfhost in self._rules_source:
            origin_host,trash = util.get_host_from_url(origin) #return host,just_after_host_position tuple
            #selfhost is already in xxx.xxx.com[:port] format
            if(origin_host and selfhost): # both of them are not None
                self._replace_to_seflhost_rules[origin_host] = self._selfhost_proto+"://"+selfhost
                self._replace_to_originalhost_rules[selfhost] = origin
            else:
                raise getHostError('Unabled to get host from '+origin+' or '+selfhost)

    def _gen_configs_for_filters(self,**kwargs):
        '''get configs for every filter in regexs4select_filter dict'''
        for filter_name in self._regexs4select_filter.values():
            if(kwargs.has_key(filter_name+'_configs')):
                setattr(self, "_"+filter_name, kwargs[filter_name+'_configs'])

all_configuration = configurations(https_enabled,fullchain_cert_path,private_key_path,server_name,rules_source,regexs4select_filter_source,selfresolve, \
                filt_scholar_configs=filt_scholar_configs,filt_scihub_configs=filt_scihub_configs)
