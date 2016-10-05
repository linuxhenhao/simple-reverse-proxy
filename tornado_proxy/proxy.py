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
import ssl
from urlparse import urlparse
import filter,re
import util,config

try:
    import Cookie  # py2
except ImportError:
    import http.cookies as Cookie  # py3


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


def fetch_request(url, callback, **kwargs):
    proxy = get_proxy(url)
    if proxy:
        logger.debug('Forward request via upstream proxy %s', proxy)
        tornado.httpclient.AsyncHTTPClient.configure(
            'tornado.curl_httpclient.CurlAsyncHTTPClient')
        host, port = parse_proxy(proxy)
        kwargs['proxy_host'] = host
        kwargs['proxy_port'] = port

    tornado.httpclient.AsyncHTTPClient.configure(
        'tornado.curl_httpclient.CurlAsyncHTTPClient')
    req = tornado.httpclient.HTTPRequest(url, **kwargs)
    client = tornado.httpclient.AsyncHTTPClient()
    client.fetch(req, callback, raise_error=True) #raise HTTPError for further treatment



class HttpHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ['GET']

    def initialize(self,rules):
        self._replace_to_originalhost_rules = rules

    def compute_etag(self):
        return None # disable tornado Etag

    def is_in_hostlist(self): #check host before any further action
        logger.debug('HttpHandler is_in_hostlist host:%s'%self.request.host)
        return self._replace_to_originalhost_rules.has_key(self.request.host)

    @tornado.web.asynchronous
    def get(self):
        logger.debug('Handle http request: %s'%self.request)
        if(self.is_in_hostlist() == False):
            self.finish()
            return
# complete all the uri from "GET /xxx" to "GET https?://host/xxx"
        host_pattern=re.compile("(https?://)([^/]+)")
        match_result=host_pattern.match(self.request.uri)
        if(match_result==None): #no host info in uri,add it
            self.request.uri=self.request.protocol+"://"+self.request.host+self.request.uri

        logger.debug('redirect http request %s to https'% self.request.uri)
        self._headers = tornado.httputil.HTTPHeaders()
        self.set_status(301)
        self.set_header('Location' , self.request.uri.replace('http','https',1))
        self.finish()



class ProxyHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ['GET', 'POST', 'CONNECT']

    #@tornado.web.RequestHandler.initialize
#add custom config to this class
#add config=file_path to handler
    def initialize(self, **kwargs):
    #rules, selfresolve, Myfilter, https_enabled
        ProxyHandler._filter=kwargs['Myfilter']
        ProxyHandler._replace_to_originalhost_rules = kwargs['rules']
        ProxyHandler._selfresolve = kwargs['selfresolve']
        ProxyHandler._https_enabled = kwargs['https_enabled']

    def compute_etag(self):
        return None # disable tornado Etag

    def is_in_hostlist(self): #check host before any further action
        logger.debug("ProxyHandler is_in_hostlist host:%s"%self.request.host)
        return self._replace_to_originalhost_rules.has_key(self.request.host)


    @tornado.web.asynchronous
    def get(self):

        if(self.is_in_hostlist() == False):
            self.finish()
            return
# complete all the uri from "GET /xxx" to "GET https?://host/xxx"
        host_pattern=re.compile("(https?://)([^/]+)")
        match_result=host_pattern.match(self.request.uri)
        if(match_result==None): #no host info in uri,add it
            self.request.uri=self.request.protocol+"://"+self.request.host+self.request.uri


        logger.debug('Handle %s request to %s', self.request.method,
                     self.request.uri)


        def handle_response(response):
            logger.info('>>>in handle response')
            if (response.error and not \
                    isinstance(response.error, tornado.httpclient.HTTPError)):
                self.set_status(500)
                self.write('Internal server error:\n' + str(response.error))
            else:
                logger.info('>>>in else')
                self.set_status(response.code, response.reason)
                self._headers = tornado.httputil.HTTPHeaders() # clear tornado default header
                logger.info('>>>before filt_content')
                response_body=self._filter.filt_content(self.url_before_selfresolve,response)

                logger.debug("response's headers")
                set_cookie_content = response.headers.pop('Set-Cookie',False)

                for header, v in response.headers.get_all():
                    logger.debug('%s:%s'%(header,v))
                    if header not in ('Content-Length', 'Transfer-Encoding', 'Content-Encoding', 'Connection'):
                        self.add_header(header, v) # some header appear multiple times, eg 'Set-Cookie'

                if(set_cookie_content): #add set-cookie to the end of headers
                    self.add_header('Set-Cookie',set_cookie_content)

                if response_body:
                    logger.info('>>>before write response body')
                    self.set_header('Content-Length', len(response_body))
                    self.write(response_body)
            self.finish()

        def redirect_before_fetch(host):
            #util.replace_to_originalhost will replace the selfhost to original host if in rules
            target_url = util.replace_to_originalhost(self.request.uri, self._replace_to_originalhost_rules)
            if(target_url !=None): #has corresponding target host in rules, successfully replaced
                self.request.uri = target_url

                #replace self.request.headers['Host']
                target_host,trash = util.get_host_from_url(self._replace_to_originalhost_rules[self.request.host])
                self.request.headers['Host'] = target_host
                self.request.host = target_host

                #replace cookies's domain option if has
                util.cookie_domain_replace(direction='to_origin',httpHandler=self)

                #replace host in referer
                if('Referer' in self.request.headers): #delete Referer in headers
                    target_referer = util.replace_to_originalhost(self.request.headers['Referer'], \
                    self._replace_to_originalhost_rules)
                    if(target_referer != None): #replace ok
                        self.request.headers['Referer'] = target_referer

                #selfresolve
                self.url_before_selfresolve = self.request.uri
                host_without_port = host.split(":")[0]
                if(self._selfresolve.has_key(host_without_port)): # request host in selfresolve dict
                    ip_addr = self._selfresolve[host_without_port]
                    self.request.uri = self.request.uri.replace(host_without_port, ip_addr)
                logger.debug("request after redirect>>>\n %s" % self.request)

                return True #if program runs to selfresolve step, always return True,url redirect finishied

            return False



            #    print ">>redirect from "+host+" to "+to_host




        body = self.request.body
        if not body:
            body = None
        try:
            if 'Proxy-Connection' in self.request.headers:
                del self.request.headers['Proxy-Connection']


#do redirect before fetch request
#to detect whether the request host is in redirect config rules
            statu=redirect_before_fetch(self.request.host)
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
        logger.debug('request to %s of request.uri %s'% (self.request.host, self.request.uri))
        if(self.is_in_hostlist() == False):
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


def run_proxy(port, address, workdir, configurations, start_ioloop=True):
    """
    Run proxy on the specified port. If start_ioloop is True (default),
    the tornado IOLoop will be started immediately.
    """


    myfilter=filter.Myfilter(configurations,workdir)
    handler_initialize_dict = dict(rules=configurations.replace_to_originalhost_rules,\
                         selfresolve=configurations.selfresolve, Myfilter=myfilter,\
                         https_enabled=configurations.https_enabled
                         )
    app = tornado.web.Application()
    app.add_handlers(configurations.server_name, [
    (r'.*', ProxyHandler,handler_initialize_dict),
    ])

    if(configurations.https_enabled): #https_enabled
        app4redirect2https = tornado.web.Application()
        app4redirect2https.add_handlers(configurations.server_name, [
        (r'.*', HttpHandler,dict(rules=configurations.replace_to_originalhost_rules)
        )
        ])

        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(configurations.fullchain_cert_path,\
                                configurations.private_key_path)
        if(address==None):
            app.listen(port, ssl_options = ssl_ctx)
            app4redirect2https.listen(80)
        else:
            app.listen(port,address, ssl_options = ssl_ctx)
            app4redirect2https.listen(80, address)
    else:
        if(address == None):
            app.listen(port)
        else:
            app.listen(port,address)
    ioloop = tornado.ioloop.IOLoop.instance()
    if start_ioloop:
        ioloop.start()

if __name__ == '__main__':
    loglevel = logging.DEBUG
    logger.setLevel(loglevel)
    tornado.web.gen_log.setLevel(loglevel)
    tornado.web.access_log.setLevel(loglevel)
    pwd = os.path.dirname(os.path.realpath(__file__))+'/'
    configurations = config.all_configuration #get all configrations in config.py
    if(os.getenv('OPENSHIFT_PYTHON_IP')==None):
        ip='0.0.0.0'
        if(configurations.https_enabled):
            port = 443
        else:
            port = 80
        if len(sys.argv) > 1:
            port = int(sys.argv[1])
    else:
        port = int(os.getenv('OPENSHIFT_PYTHON_PORT'))
        ip = os.getenv('OPENSHIFT_PYTHON_IP')
    print ("Starting HTTP proxy on %s port %d" % (ip,port))
    run_proxy(port,ip,pwd,configurations)
