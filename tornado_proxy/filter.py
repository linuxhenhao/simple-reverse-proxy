#!/usr/bin/env python
#-*- coding: utf-8 -*-
# filters to modify the http headers and response body
import re
from bs4 import BeautifulSoup

class Myfilter:
    def __init__(self,filter_regexs,parser,workdir):
        self.parser=parser #site.conf file parser
        self.workdir=workdir
        print filter_regexs
        self.filter_regexs=filter_regexs
        self.rules=[re.compile(i) for i in filter_regexs.keys()]

    def filt_content(self,url,response,**kwargs):
        response_body=response.body
        for rule in self.rules:
            if(rule.match(url)!=None): #in filter rules
                filt_name=self.filter_regexs[rule.pattern]
                return_body=getattr(self,filt_name)(response,**kwargs)
                if(return_body!=None):
                    response_body=return_body
        return response_body



    def filt_scholar(self,response): #scholar's filter
            scihub_host=self.parser.get('scholar','scihub_host')
            soup=BeautifulSoup(response.body,"html.parser")

#replace all real_shcolar_host to self_scholar_host
            a_list=soup.findAll('a')
            for a in a_list:
                href=a.get('href')
                if(href!=None):
                    a['href']=href.replace(self.parser.get('scholar',\
                        'real_scholar_host'),self.parser.get('scholar',\
                            'self_scholar_host'))

            answer_list=soup.findAll(attrs={"class":"gs_r"})
            if(len(answer_list)==0): #no gs_ri,no available resources
                return
            for item in answer_list: #every item is a block contains [h3 header|brief content|some operations]
                item=item.find(attrs={"class":"gs_ri"})
                if(item==None): #no gs_ri found,continue
                    continue
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
        #if('location' in response.request.headers):
        #    None
        if(response.body==None):
            return                  #no page,do nothing,the same as follow situation
        if(len(response.body)<=10): #too short not a html page,do nothing
            return
        soup=BeautifulSoup(response.body,'html.parser')
        save=soup.findAll('div',attrs={'id':'save'})[0]
        if(len(save)==0): #not in download page
            return
#There is in download page
        new_download_html=open(self.workdir+self.parser.get('scholar','download_html')).read()
        new_download_soup=BeautifulSoup(new_download_html,'html.parser')

        new_download_soup.iframe['src']=soup.iframe['src']

        download_link_h3=new_download_soup.findAll(attrs={'id':'download_link'})[0]

        save.a.string=u'下载链接'
        download_link_h3.insert(1,save.a)
        return str(new_download_soup)


