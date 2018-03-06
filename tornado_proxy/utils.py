import re

pattern = re.compile(r'https?://[a-zA-Z-.]+/(.*)')

def path_parameters_from_url(url):
    match_result = pattern.match(url)
    if(match_result is None):
        return None
    else:
        # return the /xxx path and parameters portion of the url
        return match_result.groups()[0]


def urlparse2url_without_host(parse_result):
    '''
    @param urllib.urlparse.ParseResult parse_result;
    using a parsed result to construct a url without scheme and host
    eg:
        ParseResult(scheme='', netloc='example.com', path='/', params='',
                    query='foo=1&%2B%3F=6', fragment='nav')
    will return
        '/?foo=1&%2B%3F=6#nav'
    '''
    result = ''
    if(parse_result.path == ''):
        # in a http://example.com form
        return result
    else:
        # has path
        result += parse_result.path
        if(parse_result.query != ''):
            result += '?' + query
        if(parse_result.fragment != ''):
            result += '#' + parse_result.fragment
        return result
