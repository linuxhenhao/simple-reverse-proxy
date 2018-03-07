## a simple reverse proxy based on tornado
a simple python implemented reverse proxy, based on tornado.
tornado.gen is used to make write asynchronous program in a
synchronized way.


## Feathures

### flexible url mapping

the url_rules list in settings.py defines the url mapping,
Both domain to domain or url to domain form are supported,
though, the url has a restricted format.

for example:
```python
	url_rules = [
		# domain to domain
		('http:proxy.com', 'https:www.google.com'),
		# url to domain
		('http:proxy.com/just4show/', 'https:www.bing.com')
        ]
```

the rule is constructed by proxy-target tuples, an element in tuple
is a `domain_str`. As showed by above example, every domain_str is
constituted by a HTTP scheme portion and a url without 'http(s)://'
portion which are delimited by a colon.


### properly handed cookie domain
for security reason, if a 'Set-Cookie' section is in a HTTP response's
header and the cookie string has some 'domain=xxx' contents, the browser
will make sure that the currently opened tab's domain is the same or a subdomain
of the xxx before take the `set cookie` action.

So, cookie domain convert should be carefully handed in a reverse proxy.


### filt ability
When doing reverse proxy, some find-and-replace actions should always be taken,
Such as some url replace actions to make sure the user can fetch the contents of
mirrored sites through proxy server.

Any other modifications can be put into the filt functions. Thus, the contents fetched
through this proxy are under control.

the filt function configurations are stored in settings.py, a filter_patterns list.

```python
	filter_patterns = [
			(r'.*\.google\.\w', 'tornaod_proxy.filter.google'),
			...
			...
            ]
```
the first part is a regular expression about target real server's url
to determin which filter will be used.
the seconde part in the tuple is a dotted python path.
the config in the above example set a google filter function in filter.py
 under the following directory structure:

	top_dir
	-- tornado_proxy
	-- -- filter.py
	-- run.py

The filter function takes one and only one parameter, a
tornado.httpclient.HTTPResponse instance for a corresponding request.
Filter author can edit the response's headers, the contens of the returned
page or img using response.body, etc

## Licence: MIT
Thanks to Senko Rasic (senko.rasic@dobarkod.hr) for his/her tornado_proxy project,
that project inspired me to write this simple reverse proxy
