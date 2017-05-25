#!/usr/bin/env python
#-*- coding: utf-8 -*-
# filters to modify the http headers and response body
import re
import util
from proxy import logger
from bs4 import BeautifulSoup

class Myfilter:
    def __init__(self,configurations,workdir):
        self._workdir = workdir
        self._configurations = configurations
        self._regexs4select_filter = configurations.regexs4select_filter
        self._replace_to_selfhost_rules = configurations.replace_to_selfhost_rules
        self._host_proto = configurations.host_proto

        self._set_configs_for_all_filters() #set self._filt_name_configs if exists

    def _set_configs_for_all_filters(self):
        self._filters_configs = dict()
        for filter_name in self._regexs4select_filter.values():
            config = self._configurations.get_configs_for_filter(filter_name)
            if(config != None): #has configs for the filter_name
                self._filters_configs[filter_name] = config

    def filt_content(self,url,response,**kwargs):
        logger.debug("In filt_content>>>>>>>>>>>>>>")
        response_body=response.body
        self._location_header_replace(response) #replace host in headers's location if exists
        util.cookie_domain_replace(direction='to_selfhost',url=url,response=response)
        content_type = self._get_content_type_from_response(response)
        if(content_type is None or content_type.lower().find('text/html') == -1):
            logger.debug("content_type is _%s_, do nothing"% content_type)
            return response_body
        if(response.body==None or len(response.body)<=10 ):
            logger.debug("response.body is empty or none, do nothing in filter")
            return  response_body                #no page,do nothing,the same as follow situation
                                    #  too short not a html page,do nothing

############## check done, now going to replace original hosts in all <a> links to selfhost
        soup=BeautifulSoup(response.body,"html.parser")
        if(self._replace_host(soup)): # replace occured
            response_body = str(soup)
        for url_pattern in self._regexs4select_filter.keys():
            if(url_pattern.match(url)!=None): #in filter rules
                filt_name = self._regexs4select_filter[url_pattern]
                if(self._filters_configs.has_key(filt_name)):
                    return_body = getattr(self,filt_name)(response,soup,\
                        self._filters_configs[filt_name], **kwargs)
                else:
                    return_body = getattr(self,filt_name)(response,soup,**kwargs)
                if(return_body!=None):
                    response_body=return_body

        return response_body
    def _get_content_type_from_response(self,response):
        try:
            logger.debug("response.headers {}".format(response.headers))
            content_type = response.headers['Content-Type']
            return content_type
        except KeyError:
            return None

    def _location_header_replace(self,response):
#In some situation,google will use 302 to location to ipv4.google.com
#to do a humanbeing check, we should do some hooks in the response headers
            origin_location_url=response.headers.pop('Location',False)
            if(origin_location_url): #has  Location section
                replaced_url =  util.replace_to_selfhost(origin_location_url,self._replace_to_selfhost_rules)
                if (replaced_url != None): #replaced successfully,has corresponding host in rules
                    new_location='Location:'+ replaced_url
                else:
                    new_location ='Location:' + origin_location_url
                response.headers.parse_line(new_location)

    def _replace_host(self,soup):
            a_list=soup.findAll('a')
            replaced = False
            for a in a_list:
                href=a.get('href')
                if(href!=None):
                    replaced_url = util.replace_to_selfhost(href,self._replace_to_selfhost_rules)
                    if(replaced_url != None ):
                        logger.debug("original url: %s replaced to %s"%(href,replaced_url))
                        a['href'] = replaced_url
                        replaced = True
                        logger.debug(">>>soup:\n %s"%(str(soup)))
            return replaced


    def filt_ipv4(self,response,soup,filt_configs=None,**kwards): #url replace for ipv4.google.com
            if(response.body==None or len(response.body)<10):
                return

            return str(soup)
    def filt_scholar(self,response,soup,filt_configs=None,**kwards): #scholar's filter

            logger.debug('In filt_scholar>>>>>>>>>>>')
            logger.debug(">>>soup:\n %s"%(str(soup)))
            scihub_host=filt_configs['scihub_host']
            citation_links = soup.findAll('a',attrs={'class':'gs_citi'})
            if(len(citation_links) != 0): # citation links found
                for link in citation_links:
                    link['target'] = "_blank" # open citation page in new tab


            answer_list=soup.findAll(attrs={"class":"gs_r"})
            if(len(answer_list) != 0): # gs_ri, available resources found
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
                    more_a=item.find(name='a',attrs={"class":"gs_nph"})
                    if(more_a==None):
                        continue
#generate new tag to add after more
                    down_a=soup.new_tag('a')
                    down_a.string=u"下载"
                    down_a['href']=self._host_proto + '://' + scihub_host+'/'+res_url
                    down_a['target']='_blank' #open in new tab
                    #insert the down_a after more_a
                    more_a.insert_before(down_a)

            return str(soup) #response.body can't change,so return it

    def filt_scihub(self,response,soup,filt_configs=None,**kwargs):
        #if('location' in response.request.headers):
        #    None
        try:
            save=soup.findAll('div',attrs={'id':'save'})[0]
        except: #cannot find save div,means no the webpage we predicted,so do noting
            return

        if(len(save)==0): #not in download page
            return
#There is in download page
        new_download_html=open(self._workdir+filt_configs['download_html']).read()
        new_download_soup=BeautifulSoup(new_download_html,'html.parser')

        new_download_soup.iframe['src']=soup.iframe['src']

        download_link_h3=new_download_soup.findAll(attrs={'id':'download_link'})[0]

        save.a.string=u'下载链接'
        download_link_h3.insert(1,save.a)
        return str(new_download_soup)

    def _replace_googlecontent_to_selfhost(self,soup):
        try:
            save = soup.findAll('a',attrs={'class':'gs_citi'})
        except: # findAll caught in exception, nothing in save ,just return
            return
        if (len(save) == 0):  #cannot find any links in class gs_citi return
            return
        #links in class gs_citi found, deal with them
        for link in save:
            url = link.get('href')
            if(url != None): # link has href attribute
                selfhost_url = util.replace_to_selfhost(url)
                if(selfhost_url != None): # replace succed
                    link['href'] = selfhost_url
                #else, nothing need to be done, because url don't contain host,
                #things can work as we want
