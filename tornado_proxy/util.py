#!/usr/bin/env python
#-*- coding: utf-8 -*-

#general useful functions for this project
import MyCookie as Cookie

from configini import rules_source,util_log_level
import logging
logger = logging.getLogger('util_log')
logger.setLevel(util_log_level)

def gen_origin_selfhost_list(tuple_list):
    '''the tuple_list is in [('https://www.xx.xx', 'www.xx.xxx'),] format'''
    origin_selfhost_list = list()
    for origin_url,selfhost in tuple_list:
        origin,trash = get_host_from_url(origin_url)
        origin_without_port = origin.split(":")[0]
        selfhost_without_port = selfhost.split(":")[0]
        origin_selfhost_list.append((origin_without_port,selfhost_without_port))
    return origin_selfhost_list



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
    host,just_after_host_position=get_host_from_url(origin_url)
    if ( host != None):
        return to_selfhost_rules[host]+ \
            origin_url[just_after_host_position:]
    else: # cannot get host from origin url
        return None

def replace_to_originalhost(selfhost_url,to_original_rules):
    '''replace the selfhost url to original real url
    such as https://scholar.thinkeryu.com to https://scholar.google.com
    rules like dict{'selfhost':original_url,}
    selfhost also include port if it exist
    '''
    host,just_after_host_position=get_host_from_url(selfhost_url)
    if(host != None):
        return to_original_rules[host]+\
                selfhost_url[just_after_host_position:]
    else: # cannot get host from selfhost_url
        return None

def get_host_from_url(url):
    '''
    return host with port, or none if not found
    url may like //host[:port]/xxxx
    or https?://host[:port]/xxxx
    or /arg?id=3xxxxxx (in this format, host can only get from request info
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
    return None

def load_cookie(headers):
    c = Cookie.SimpleCookie()
    set_cookie = headers.pop('Set-Cookie',False)
    if(set_cookie): # has set-cookie section
        logger.debug('cookie_content>>>\n%s'%set_cookie)
        c.load(set_cookie)
        return c
    else:
        set_cookie = headers.pop('Cookie',False)
        if(set_cookie):
            logger.debug('cookie_content>>>\n%s'%set_cookie)
            c.load(set_cookie)
            return c
        else:
            return None
def get_same_level_domain_from_host(host,domain):
    dot_counts = domain.count('.')
    def get_domain(counts,host):
        last_pos = None
        while(counts != 0):
            last_pos = host.rfind('.',0,last_pos)
            if(last_pos == -1):
                return host
            counts = counts - 1
        return host[last_pos+1:]

    if(domain[0]=='.'): #format .google.com
        counts = dot_counts
        return '.'+get_domain(counts,host)
    else:
        counts =dot_counts+1
        return get_domain(counts,host)

def cookie_domain_replace(direction,**kwargs):
    '''direction can be 'to_seflhost' and 'to_origin'
    if to_selfhost kwargs should be url and response
    else kwargs should be httpHandler
    '''
    if(direction == 'to_selfhost'):
        to_selfhost = True
    else:
        to_selfhost = False
    if(to_selfhost):
        url = kwargs['url']
        headers =kwargs['response'].headers
    else:
        httpHandler = kwargs['httpHandler']
        url = httpHandler.request.uri
        headers = httpHandler.request.headers

    c = load_cookie(headers)
    if(c == None):
        return False #do nothing
    else:
        for key in c.keys():
            domain = c[key].pop('domain',False)
            if(domain):
                host,trash = get_host_from_url(url)
                host_without_port = host.split(":")[0]
                for original_host_without_port,selfhost_without_port in origin_selfhost_list:
                    if(to_selfhost):
                        if(original_host_without_port == host_without_port):
                            # one of the original_host_without_port must equal to origin_host_without_port
                            # for the program runs into filt_content
                            selfdomain = get_same_level_domain_from_host(selfhost_without_port,domain)

                            c[key]['domain'] = selfdomain
                    else: #'to original host'
                        if(selfhost_without_port == host_without_port):
                            origindomain = get_same_level_domain_from_host(original_host_without_port,domain)
                            c[key]['domain'] = origindomain
    logger.debug("cookie output from simpleCookie>>>\n%s"%c.output())
    cookie_contents = c.output().split("Set-Cookie: ") #["",value,value,value]
    for value in cookie_contents[1:]:
        if(to_selfhost): #for set cookie on client side
            headers.add('Set-Cookie',value.strip())

        else: #for send to real server
            headers.add("Cookie",value.strip())

origin_selfhost_list = gen_origin_selfhost_list(rules_source)
