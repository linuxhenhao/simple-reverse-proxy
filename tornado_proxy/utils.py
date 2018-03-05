import re

pattern = re.compile(r'https?://[a-zA-Z-.]+/(.*)')

def path_parameters_from_url(url):
    match_result = pattern.match(url)
    if(match_result is None):
        return None
    else:
        # return the /xxx path and parameters portion of the url
        return match_result.groups()[0]
