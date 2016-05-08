#!/usr/bin/env python
#-*- coding: utf-8 -*-
# filters to modify the http headers and response body
import re
from bs4 import BeautifulSoup

def filt_content(url,responsebody,url_prefix,scihub_host):
    if(url.find(url_prefix)!=-1): # scholar's prefix found
        soup=BeautifulSoup(responsebody,"html.parser")
        answer_list=soup.findAll(attrs={"class":"gs_ri"})
        if(len(answer_list)==0): #no gs_ri,no available resources
            return responsebody
        for item in answer_list: #every item is a block contains [h3 header|brief content|some operations]
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
            #insert the down_a after more_a
            more_a.insert_after(down_a)
        return str(soup)
#Not scholar url,no need to filt
    return responsebody



