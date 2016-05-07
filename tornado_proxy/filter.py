#!/usr/bin/env python
#-*- coding: utf-8 -*-
# filters to modify the http headers and response body
import ConfigParser
from BeautifualSoup import BeautifualSoup

filter_options=ConfigParser.RawConfigParser()
filter_options.read("./site.conf")

url_prefix=filter_options.get('scholar','scholar_site_url_prefix')
content_host=filter_options.get('scholar','scholar_content_host')  #the host to get pdfs
                                                                #only host name like sci.com
def filt_content(url,resbonsebody):
    if(url.find(url_prefix)!=-1): # scholar's prefix found
        soup=BeautifualSoup(resbonsebody)
        answer_list=soup.findAll(attrs={"class":"gs_ri"})
        if(len(answer_list)==0): #no gs_ri,no available resources
            return responsebody
        for item in answer_list: #every item is a block contains [h3 header|brief content|some operations]
            res_url=item.a.get("href") #the resource's url
            if(res_url==None):#no href attr,skip
                continue
            #has res_url,go to add a content <a ...
            more_a=item.find(name='a',attrs={"class":"gs_mor gs_oph"})
            if(more_a==None):
                continue


