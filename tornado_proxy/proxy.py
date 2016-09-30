#!/usr/bin/env python
#
# Simple asynchronous HTTP proxy with tunnelling (CONNECT).
#
# GET/POST proxying based on
# http://groups.google.com/group/python-tornado/msg/7bea08e7a049cf26
#
# Copyright (C) 2012 Senko Rasic <senko.rasic@dobarkod.hr>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import logging
import os
import sys
import socket
from urlparse import urlparse
import filter,re
from MyConfigParser import RawConfigParser

import tornado.httpserver
import tornado.ioloop
import tornado.iostream
import tornado.web
import tornado.httpclient
import tornado.httputil

logger = logging.getLogger('tornado_proxy')

__all__ = ['ProxyHandler', 'run_proxy']


def get_proxy(url):
    url_parsed = urlparse(url, scheme='http')
    proxy_key = '%s_proxy' % url_parsed.scheme
    return os.environ.get(proxy_key)


def parse_proxy(proxy):
    proxy_parsed = urlparse(proxy, scheme='http')
    return proxy_parsed.hostname, proxy_parsed.port

def config2dict(parser,section): #parser is a configParser object
    dic=dict()
    for filt_name,regex in parser.items(section):
        dic[regex]=filt_name
    return dic

def fetch_request(url, callback, **kwargs):
    proxy = get_proxy(url)
    if proxy:
        logger.debug('Forward request via upstream proxy %s', proxy)
        tornado.httpclient.AsyncHTTPClient.configure(
            'tornado.curl_httpclient.CurlAsyncHTTPClient')
        host, port = parse_proxy(proxy)
        kwargs['proxy_host'] = host
        kwargs['proxy_port'] = port

    req = tornado.httpclient.HTTPRequest(url, **kwargs)
    client = tornado.httpclient.AsyncHTTPClient()
    try:
        client.fetch(req, callback, raise_error=True) #raise HTTPError for further treatment
    except e:
        print e

def get_host(url):
    #url is something like http://www.baidu.com/word?
    items=url.split('/')  #[http,'',host,uri] 2 is host
    if(items[0].find('http')!=-1): #found 'http'
        try:
            return items[2]
        except:
            logger.debug('url format error when get_host')
            return None


def get_target_url_by_pattern_result(pattern_result,target_val):
    # pattern results is re.match's result
    # target val is a target url that using $number as signature for replace by pattern result
    signature_position_list=list()
    target_val_length_minus1=len(target_val)-1
    position=target_val.find('$')

    while(position!=-1):
        signature_position_list.append(position)
        if(position==target_val_length_minus1):
            break
        position=target_val.find('$',position+1)

    signature_position_list_length=len(signature_position_list)
    if(signature_position_list_length%2!=0):
        logger.debug('counts of $ in url_redirect rule don\'t match')
        return None

    number=int(target_val[ signature_position_list[0]+1 : signature_position_list[1] ])
    target_url=target_val[ :signature_position_list[0] ]+pattern_result.groups()[number]
    for i in xrange(2,signature_position_list_length,2):
        number=int(target_val[ signature_position_list[i]+1 : signature_position_list[i+1]])
        target_url+=target_val[ signature_position_list[i-1]+1: signature_position_list[i]]+pattern_result.groups()[number]

    if(signature_position_list[-1]!=target_val_length_minus1):
        target_url+=target_val[signature_position_list[-1]+1:]

    return target_url

def add_server_name_compiled_list_to_parser(parser):
    server_name_list=parser.items('server_name')
    parser.server_name_compiled_list=list()
    for k,v in server_name_list:
        parser.server_name_compiled_list.append(re.compile(v))

def is_server_name_right(compiled_server_name_list,request_host):
    for re_server_pattern in compiled_server_name_list:
        if(re_server_pattern.match(request_host)):
            return True
        else:
            return False

class ProxyHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ['GET', 'POST', 'CONNECT']

    #@tornado.web.RequestHandler.initialize
#add custom config to this class
#add config=file_path to handler
    def initialize(self,parser,Myfilter):
        ProxyHandler.filter=Myfilter
        ProxyHandler.parser=parser
        ProxyHandler.pattern_target_list=list()
        key_val_list=self.parser.items('url_redirect')
        for key,val in key_val_list:
            ProxyHandler.pattern_target_list.append((re.compile(key),val))

    def compute_etag(self):
        return None # disable tornado Etag

    @tornado.web.asynchronous
    def get(self):
#first of all,judge whether the request's host is what we server for
        if(is_server_name_right(self.parser.server_name_compiled_list,\
                    self.request.host)==False):
            logger.debug('request uri %s\'s server name not in list',\
                    self.request.uri)
            self.finish()
            return

        logger.debug('Handle %s request to %s', self.request.method,
                     self.request.uri)


        def handle_response(response):
            if (response.error and not \
                    isinstance(response.error, tornado.httpclient.HTTPError)):
                self.set_status(500)
                self.write('Internal server error:\n' + str(response.error))
            else:
                self.set_status(response.code, response.reason)
                self._headers = tornado.httputil.HTTPHeaders() # clear tornado default header
                response_body=self.filter.filt_content(self.url_before_selfresolve,response)
                for header, v in response.headers.get_all():
                    if header not in ('Content-Length', 'Transfer-Encoding', 'Content-Encoding', 'Connection'):
                        self.add_header(header, v) # some header appear multiple times, eg 'Set-Cookie'

                if response_body:
                    self.set_header('Content-Length', len(response_body))
                    self.write(response_body)
            self.finish()

        def redirect_before_fetch(url):
            for re_pattern,target in self.pattern_target_list:
                match_result=re_pattern.match(url)
                if(match_result!=None): # matched
                    target_url=get_target_url_by_pattern_result(match_result,target)
                    if(target_url!=None):
                        self.request.uri=target_url
                        self.url_before_selfresolve=target_url

                        target_host=get_host(target_url)
                        if(target_host!=None):
                            self.request.host=self.request.headers['Host']=target_host
                             #request.headers['Host'] is different form request.host

                            splited_host=target_host.split(":")
                            host_without_port=splited_host[0]
                            if(self.parser.has_option('selfresolve',host_without_port)):
                            #dispite the effects of port in host section
                                real_host=self.parser.get('selfresolve',host_without_port)
                                self.request.uri=target_url.replace(host_without_port,real_host)
                                self.request.host=target_host.replace(host_without_port,real_host)

                            if('Referer' in self.request.headers): #delete Referer in headers
                                del self.request.headers['Referer']
                            return True #if program runs to selfresolve step, always return True,url redirect finishied

            return False



            #    print ">>redirect from "+host+" to "+to_host




        body = self.request.body
        if not body:
            body = None
        try:
            if 'Proxy-Connection' in self.request.headers:
                del self.request.headers['Proxy-Connection']

# complete all the uri from "GET /xxx" to "GET https?://host/xxx"
            host_pattern=re.compile("(https?://)([^/]+)")
            match_result=host_pattern.match(self.request.uri)
            if(match_result==None): #no host info in uri,add it
                self.request.uri=self.request.protocol+"://"+self.request.host+self.request.uri

#do redirect before fetch request
#to detect whether the request host is in redirect config rules
            statu=redirect_before_fetch(self.request.uri)
            if(statu==False): #not in rules,finish
                self.set_status(500)
                self.write('Internal server error:\n')
                self.finish()
            else:
                logger.info("request after urlredirect %s"% self.request)
                fetch_request(
                self.request.uri, handle_response,
                method=self.request.method, body=body,
                headers=self.request.headers, follow_redirects=False,
                allow_nonstandard_methods=True)
        except tornado.httpclient.HTTPError as e:
            if hasattr(e, 'response') and e.response:
                handle_response(e.response)
            else:
                self.set_status(500)
                self.write('Internal server error:\n' + str(e))
                self.finish()

    @tornado.web.asynchronous
    def post(self):
        return self.get()

    @tornado.web.asynchronous
    def connect(self):
        if(is_server_name_right(self.parser.server_name_compiled_list,\
                    self.request.host)==False):
            logger.debug('request uri %s\'s server name not in list',\
                    self.request.uri)
            self.finish()
            return
        logger.debug('Start CONNECT to %s', self.request.uri)
        host, port = self.request.uri.split(':')
        client = self.request.connection.stream

        def read_from_client(data):
            upstream.write(data)

        def read_from_upstream(data):
            client.write(data)

        def client_close(data=None):
            if upstream.closed():
                return
            if data:
                upstream.write(data)
            upstream.close()

        def upstream_close(data=None):
            if client.closed():
                return
            if data:
                client.write(data)
            client.close()

        def start_tunnel():
            logger.debug('CONNECT tunnel established to %s', self.request.uri)
            client.read_until_close(client_close, read_from_client)
            upstream.read_until_close(upstream_close, read_from_upstream)
            client.write(b'HTTP/1.0 200 Connection established\r\n\r\n')

        def on_proxy_response(data=None):
            if data:
                first_line = data.splitlines()[0]
                http_v, status, text = first_line.split(None, 2)
                if int(status) == 200:
                    logger.debug('Connected to upstream proxy %s', proxy)
                    start_tunnel()
                    return

            self.set_status(500)
            self.finish()

        def start_proxy_tunnel():
            upstream.write('CONNECT %s HTTP/1.1\r\n' % self.request.uri)
            upstream.write('Host: %s\r\n' % self.request.uri)
            upstream.write('Proxy-Connection: Keep-Alive\r\n\r\n')
            upstream.read_until('\r\n\r\n', on_proxy_response)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        upstream = tornado.iostream.IOStream(s)

        proxy = get_proxy(self.request.uri)
        if proxy:
            proxy_host, proxy_port = parse_proxy(proxy)
            upstream.connect((proxy_host, proxy_port), start_proxy_tunnel)
        else:
            upstream.connect((host, int(port)), start_tunnel)


def run_proxy(port, address, workdir ,config_file_path, regexs_section,start_ioloop=True):
    """
    Run proxy on the specified port. If start_ioloop is True (default),
    the tornado IOLoop will be started immediately.
    """
    parser=RawConfigParser()
    parser.read(workdir+config_file_path)
    filter_regexs=config2dict(parser,regexs_section)

    add_server_name_compiled_list_to_parser(parser)
    #now parser.server_name_compiled_list exists

    myfilter=filter.Myfilter(filter_regexs,parser,workdir)
    app = tornado.web.Application([
        (r'.*', ProxyHandler,dict(parser=parser,Myfilter=myfilter)),
    ])
    if(address==None):
        app.listen(port)
    else:
        app.listen(port,address)
    ioloop = tornado.ioloop.IOLoop.instance()
    if start_ioloop:
        ioloop.start()

if __name__ == '__main__':
    if(os.getenv('OPENSHIFT_PYTHON_IP')==None):
        ip='0.0.0.0'
        port = 8888
        if len(sys.argv) > 1:
            port = int(sys.argv[1])
    else:
        port = int(os.getenv('OPENSHIFT_PYTHON_PORT'))
        ip = os.getenv('OPENSHIFT_PYTHON_IP')
    logger.setLevel(logging.INFO)
    pwd = os.path.dirname(os.path.realpath(__file__))+'/'

    print ("Starting HTTP proxy on %s port %d" % (ip,port))
    run_proxy(port,ip,pwd,"site.conf",'regexs')
