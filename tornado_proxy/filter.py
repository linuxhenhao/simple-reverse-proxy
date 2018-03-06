#!/usr/bin/env python
#-*- coding: utf-8 -*-
# filters to modify the http headers and response body
import re
import importlib
import logging
from . import utils
from bs4 import BeautifulSoup
if sys.version_info[0] < 3:  # in python 2
    from urlparse import urlparse
else:
    from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class Filter:
    def __init__(self, filter_patterns, url_rules):
        '''
        @param list filter_patterns: contains regex_pattern, dotted path tuple
        @param list url_rules: contains 'http or https:url', 'http or https:host'
        '''
        self.filter_regexes = self._gen_filter_regexes(filter_patterns)
        self.reverse_dict = self._gen_reverse_url_map(url_rules)


    def _gen_filter_regexes(self, filter_patterns):
        '''
        compile regex_patterns and construct a new re.compile -> python-func
         dict.
        '''
        filter_regexes = dict()

        def import_function(function_path):
            '''
            @param str function_path; a dotted python path to import function
            return function
            '''
            module_name, func_name = function_path.rsplit('.', maxsplit=1)
            try:
                module = importlib.import_module(module_name)
                func = getattr(module, func_name)
                return func
            except ImportError as e:
                logger.info(e.msg)
            except AttributeError as e:
                logger.info(e.msg)
            return None

        for regex_pattern in filter_patterns:
            filt_func = import_function(function_path)
            if(filt_func is not None):
                filter_regexes[re.compile(regex_pattern)] =\
                    filt_func

        return filter_regexes

    def _gen_reverse_url_map(self, url_rules):
        '''
        generate a real host in "http://xxx or "https://xxx" form ->
                 proxy url in "http://proxy.com/xx/" or "https://proxy.com/xx/"
                 dict
        '''
        reverse_dict = dict()
        for proxy_str, real_host_str in url_rules:
            host_partial_url =  real_host_str.replace(":", "://")
            proxy_partial_url = proxy_str.replace(":", "://", 1)
            # the 1 in replace means only replace the first colon to ://
            reverse_dict[host_partial_url] = proxy_partial_url

        return reverse_dict

    def filt(self, response):
        '''
        @param tornado.httpclient.HTTPResponse response; http response waiting
        for processing
        '''
        for regex in self.filter_regexes:
            if(regex.match(response.effective_url) is not None):
                self.filter_regexes[regex](response, self.reverse_dict)

    @staticmethod
    def response_body_check(response):
        '''
        @param tornado.httpclient.HTTPResponse response;
        return True if response has a valid body, else False
        '''
        if(response.body is None or len(response.body) < 10):
            # a response.body less than 10 characters should not exist
            return False
        return True

    @staticmethod
    def host_replace(soup, real2proxy_map, protocol):
        '''
        @param bs4.BeautifulSoup soup: a beautifulSoup instance
        @param dict real2proxy_map: real host -> proxy_url map
        @param str protocol: https or http, the request's protocol to fetch
            the soup contents
        '''
        a_tags = soup.findAll('a')
        for tag in a_tags:
            src = tag.get('src')
            # in some pages, the src attr for a tag is set by js script
            # Thus a tag dose not have a src attr is possible
            if(src is not None):
                parse_result = urlparse(src)
                if(parse_result.netloc != ''):
                    if(parse_result.scheme == ''):
                        # some pages use src='//example.com' to fit both http
                        # and https requests
                        url = protocol + ":" + src
                    else:
                        url = parse_result.scheme + "://" parse_result.netloc
                    proxy_url = real2proxy_map.get(url)
                    if(proxy_url is not None):
                        tag['src'] = proxy_url +\
                            utils.urlparse2url_without_host(parse_result)


def filt_scholar(response, reverse_dict): #scholar's filter
    scihub_host=self.parser.get('scholar','scihub_host')
    soup=BeautifulSoup(response.body,"html.parser")
    answer_list=soup.findAll(attrs={"class":"gs_ri"})
    if(len(answer_list)==0): #no gs_ri,no available resources
        return
    for item in answer_list: #every item is a block contains [h3 header|brief content|some operations]
        if(item.h3==None): #not paper or patent block,ignore
            continue
        if(item.h3.a==None): #no resource url,continue
            continue

        res_url=item.h3.a.get("href") #the resource's url
        if(res_url==None):#no href attr,skip
            continue

        #has res_url,go to add a content <a ...
        more_a=item.find(name='a',attrs={"class":re.compile("gs_mor.*")})
        if(more_a==None):
            continue
#generate new tag to add after more
        down_a=soup.new_tag('a')
        down_a.string=u"下载"
        down_a['href']="http://"+scihub_host+'/'+res_url
        down_a['class']="gs_nph"
        down_a['target']='_blank' #open in new tab
        #insert the down_a after more_a
        more_a.insert_after(down_a)
    return str(soup) #response.body can't change,so return it

def filt_scihub(self,response):
    if('location' in response.request.headers):
        None
    if(response.body==None):
        return
    soup=BeautifulSoup(response.body,'html.parser')
    save=soup.findAll('div',attrs={'id':'save'})[0]
    if(len(save)==0): #not in download page
        return
#There is in download page
    new_download_html=open(self.parser.get('scholar','download_html')).read()
    new_download_soup=BeautifulSoup(new_download_html,'html.parser')

    new_download_soup.iframe['src']=soup.iframe['src']

    download_link_h3=new_download_soup.findAll(attrs={'id':'download_link'})[0]

    save.a.string=u'下载链接'
    download_link_h3.insert(1,save.a)
    return str(new_download_soup)
