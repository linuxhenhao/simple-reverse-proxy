#!/usr/bin/env python
# https option
https_enabled = False
# if https enabled,
'''
url_rules are constructed by
(front end host description, target host description)
tuples, the description string is constituted by colon delimited
scheme and host string, eg "https:www.baidu.com".
'''
url_rules = [
        # ('https:test.com', 'https:scholar.google.com'),
        ]

'''
the key in self_resolve is host string, and the value is a
list contains ip string whether ipv4 or ipv6 address is ok.
when redirect request, if the target host in request after
redirect is in this dict, one of the ip address in the list
will be randomly choosed to fetch data from.
'''
self_resolve = {
        # 'abc.com': ['1.1.1.1', '2.2.2.2'],
        }

# allow tornado.httpclient using ipv6 to fetch if ipv6 is
# available both in proxy host and target host
allow_ipv6 = True

'''
filter_patterns: a django url_patterns like list, regular expression will be used
to match which filter will be applied to that response
'''
filter_patterns = [
            # (r'^scholar\.google\.\w+', 'tornado_proxy.filter.google'),
            ]
