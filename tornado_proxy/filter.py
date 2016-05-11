#!/usr/bin/env python
#-*- coding: utf-8 -*-
# filters to modify the http headers and response body
import re
from bs4 import BeautifulSoup
filter_regexs={'https?://g\.ald-lab\.tk.*/scholar':'filt_scholar',
        'https?://sci\.ald-lab\.tk':'filt_scihub'}

class Myfilter:
    def __init__(self,filter_regexs,parser):
        self.parser=parser #site.conf file parser
        self.filter_regexs=filter_regexs
        self.rules=[re.compile(i) for i in filter_regexs.keys()]

    def filt_content(self,url,response,**kwargs):
        for rule in self.rules:
            if(rule.match(url)!=None): #in filter rules
                filt_name=self.filter_regexs[rule.pattern]
                return getattr(self,filt_name)(response,**kwargs)


    def filt_scholar(self,response): #scholar's filter
            scihub_host=self.parser.get('scholar','scihub_host')
            soup=BeautifulSoup(response.body,"html.parser")
            answer_list=soup.findAll(attrs={"class":"gs_ri"})
            if(len(answer_list)==0): #no gs_ri,no available resources
                return
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
            return str(soup) #response.body can't change,so return it

    def filt_scihub(self,response,**kwargs):
        None

