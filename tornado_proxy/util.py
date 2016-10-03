#!/usr/bin/env python
#-*- coding: utf-8 -*-

#general useful functions for this project

class HostNotFoundError(Exception):
    def __init__(self,url):
        self.url=url
    def __str__(self):
        return repr('cannot found host in '+self.url)

def replace_to_selfhost(origin_url,to_selfhost_rules):
    '''replace the original url to our server's url
    such as https://scholar.google.com
    rules like dict{'original_host':selfhost_url,}
    original_host include port if it has
    '''
    try:
        host,just_after_host_position=get_host_from_url(origin_url)
        return to_selfhost_rules[host]+ \
            origin_url[just_after_host_position:]
    except:
        return None

def replace_to_originalhost(selfhost_url,to_original_rules):
    '''replace the selfhost url to original real url
    such as https://scholar.thinkeryu.com to https://scholar.google.com
    rules like dict{'selfhost':original_url,}
    selfhost also include port if it exist
    '''
    try:
        host,just_after_host_position=get_host_from_url(selfhost_url)
        return to_original_rules[host]+\
                selfhost_url[just_after_host_position:]
    except:
        return None

def get_host_from_url(url):
    '''url may like //host[:port]/xxxx
    or https?://host[:port]/xxxx
    '''
    just_before_host_position = url.find('//')
    if(just_before_host_position != -1): #found
        just_after_host_position = url.find('/',\
                just_before_host_position+2)
        if(just_after_host_position == -1):#no /xxxx part in url
            just_after_host_position=len(url)
        host=url[just_before_host_position+2:\
                just_after_host_position]
        #host judge
        host_without_port = host.split(':')[0]
        dot_position = host_without_port.rfind('.')
        if(dot_position < len(host_without_port)-1):
            return host,just_after_host_position
    raise HostNotFoundError(url)
