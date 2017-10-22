#!/usr/bin/env python3

import threading
from hashlib import md5
import sys
import logging
import ctypes
import time

if sys.version_info[0] < 3:
    # python 3
    from urllib2 import urlopen
else:
    from urllib.request import urlopen
# logging.basicConfig(level=logging.DEBUG)

class DetectThread(threading.Thread):
    def __init__(self, urls):
        super(DetectThread, self).__init__()
        self.md5 = md5()
        # md5.update("string")
        # md5.digest() return bytes caculated from string
        self.result = {}  # key->url, content, md5
        for url in urls:
            self.result[url] = None
        self.iplistM = IPListMaintainer()
        self.updateList()

    def updateList(self):
        for url in self.result.keys():
            #try:
                fd = urlopen(url)
                contentStr = fd.read()
                self.md5.update(contentStr)
                md5 = self.md5.digest()
                print(contentStr)
                if(self.result[url] is not None):  # already has contents
                    if(self.result[url][1] != md5):
                        # the same contents, do nothing, only update when differ
                        self.result[url] = (contentStr, md5)
                        self.iplistM.updateIPList(contentStr)
                else:
                    self.result[url] = (contentStr, md5)
                    self.iplistM.updateIPList(contentStr)
                print(url+'finished')
            #except:
                # urlopen failed, skip
            #    print("urlopen failed")
            #    pass

    def run(self):
        time.sleep(3600)
        self.updateList()

    def isInIPList(self, ipaddr):
        return self.iplistM.isInIPList(ipaddr)

class IPListMaintainer:
    def __init__(self):
        self.v4List = list()
        self.v6List = list()

    def updateIPList(self, string):
        if(isinstance(string, bytes)):
            string = string.decode('utf-8')
        if('.' in string):  # ipv4
            v = '4'
        else:
            v = '6'
        return getattr(self, '_updateV'+v+'List')(string)

    def isInIPList(self, ipstr):
        if('.' in ipstr):  # ipv4
            v = '4'
        else:
            v = '6'
        return getattr(self, '_isInV'+v+'List')(ipstr)

    def isMatchSections(self, sections, CFsections):
        '''
        @param [int] sections; a list contains ip address converted int
        @param [Section] CFsections; a list contains section  produced by cloudflare's ips
        '''

        for index in range(len(CFsections)):
            logging.debug("In section {}".format(index))
            logging.debug("cf section {}".format(CFsections[index]))
            if(CFsections[index].isEqual(sections[index]) is False):
                return False
        return True

    def genMask(self, counts, V4=True):
        '''
        @param ctypes.c_int8(or 16) value;
        '''
        if(V4 is True):
            init = ctypes.c_int8(128)  # 1000 0000
        else:
            init = ctypes.c_int16(65536)  # 1000 0000 0000 0000

        for i in range(counts):
            init.value |= init.value >> i
        return init.value

    def _updateV4List(self, string):
        '''
        @param str string; cloudflare's ipvs-v4 return content, in ipaddr/masklen
        format, seperated by '\n'
        '''
        del self.v4List[:]
        for ipstr in string.strip().split('\n'):
            if(ipstr != ''):  # the last ip/mask followed by a \n, produce a empty str
                ip, mask = ipstr.strip().split('/')
                mask = int(mask)
                self.v4List.append(self._convertV4ToInts(ip, mask))

    def _updateV6List(self, string):
        '''
        @param str string; cloudflare's ipvs-v6 return content, in ipaddr/masklen
        format, seperated by '\n'
        '''
        del self.v6List[:]
        for ipstr in string.strip().split('\n'):
            if(ipstr != ''):  # the last ip/mask followed by a \n, produce a empty str
                ip, mask = ipstr.strip().split('/')
                mask = int(mask)
                self.v6List.append(self._convertV6ToInts(ip, mask))

    def _isInV4List(self, ipstr):
        '''
        @param str ipstr; eg: 192.168.3.1
        test whethe this ipstr in cloudflare's v4 tree
        '''
        sections = ipstr.strip().split('.')
        intSections = [int(i) for i in sections]
        for CFsection in self.v4List:
            logging.debug('cfsection {}'.format(CFsection))
            if(self.isMatchSections(intSections, CFsection) is True):
                return True
        return False

    def _isInV6List(self, ipstr):
        '''
        @param str ipstr; eg: 2400:cb00::
        test whethe this ipstr in cloudflare's v4 tree
        '''
        sections = ipstr.strip().split(':')
        zeroSections = 8 - len(sections) + 1
        metZero = False  # only expand :: to multiple zeros onece
        intSections = list()
        for section in sections:
            if(section == ''):
                value = 0
                if(metZero is False):
                    for i in range(zeroSections):
                        intSections.append(value)
                    metZero = True
                else:
                    intSections.append(value)
            else:
                value = int(section, base=16)
                intSections.append(value)
        logging.debug("intSections gen from ip {}".format(intSections))

        for CFsection in self.v6List:
            if(self.isMatchSections(intSections, CFsection) is True):
                return True
        return False


    def _convertV4ToInts(self, ipstr, maxLength):
        numToConvert = 3 - int((32-maxLength)/8)  # start from 0, so 3-xx
        logging.debug("{} sections need to generate".format(numToConvert))
        ipsections = ipstr.strip().split('.')
        values = []
        for index in range(numToConvert+1):
            value = int(ipsections[index], base=10)
            if(index == numToConvert and maxLength < (index+1)*8):
                # the last section not all masked, a range section
                value &= self.genMask(8 - (index+1)*8 + maxLength, V4=True)
                maxValue = value + 2**((index+1)*8-maxLength) - 1
                values.append(Section(value, maxValue))
                logging.debug("last range section in [{}, {}]".format(value, maxValue))
            else:
                values.append(Section(value))
                logging.debug("section at {} {}".format(index, value))
        return values

    def _convertV6ToInts(self, ipstr, maxLength):
        numToConvert = 7 - int((128-maxLength)/16)  #start from 0
        logging.debug("{} sections need to generate".format(numToConvert))
        logging.debug("ipaddr is {}".format(ipstr))
        ipsections = ipstr.strip().split(':')
        zeroSections = 8 - len(ipsections) + 1  # ipv6 addr use :: to short the conituned zerosections
        metZero = False  # :: can only met once, for addrs like 2400:cb00::, only the first '' should
                         # be expand to zeroSections, the next one is just set value to 0
        values = []
        vindex = index = 0
        while True:
            logging.debug("index is at {}".format(index))
            if(metZero):
                vindex = index - zeroSections
            else:
                vindex = index

            if(index > numToConvert):
                break
            if(ipsections[vindex] == ''):
                value = 0
                if(metZero is False):
                    for i in range(zeroSections):
                        if(index+i == numToConvert and maxLength < (index+i+1)*16):
                            value &= self.genMask(16 - (index+i+1)*16 + maxLength, V4=False)
                            maxValue = value + 2**((index+i+1)*16-maxLength)-1
                            values.append(Section(value, maxValue))
                            logging.debug("last range section in [{}, {}]".format(value, maxValue))

                        else:
                            values.append(Section(value))
                            logging.debug("section at {} {}".format(index, value))
                    index += zeroSections
                    metZero = True
                else:
                    if(index == numToConvert and maxLength < (index+1)*16):
                        value &= self.genMask(16 - (index+1)*16 + maxLength, V4=False)
                        maxValue = value + 2**((index+1)*16-maxLength)-1
                        values.append(Section(value, maxValue))
                        logging.debug("last range section in [{}, {}]".format(value, maxValue))
                    else:
                        values.append(Section(value))
                        logging.debug("section at {} {}".format(index, value))
                    index += 1
                continue
            else:
                value = int(ipsections[vindex], base=16)
                if(index == numToConvert and maxLength < (index+1)*16):
                    value &= self.genMask(16 - (index+1)*16 + maxLength, V4=False)
                    maxValue = value + 2**((index+1)*16-maxLength)-1
                    values.append(Section(value, maxValue))
                    logging.debug("last range section in [{}, {}]".format(value, maxValue))
                else:
                    values.append(Section(value))
                    logging.debug("section at {} {}".format(index, value))
                index += 1
        return values

class Section:
    def __init__(self, value, maxValue=None):
        if(maxValue is None):
            self.tRange = False
            self.value = value
        else:
            self.tRange = True
            self.minValue = value
            self.maxValue = maxValue

    def isEqual(self, value):
        if(self.tRange):
            return value >= self.minValue and value <= self.maxValue
        else:  # signle value
            return value == self.value

    def __str__(self):
        if(self.tRange):
            return '({}, {})'.format(self.minValue, self.maxValue)
        else:
            return str(self.value)
