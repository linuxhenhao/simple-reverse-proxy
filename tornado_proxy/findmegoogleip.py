#! /usr/bin/python2

import random
import threading
import sys
import time
import socket
import ssl
import re
import dns.resolver
import dns.exception
import os
import urllib2
from configini import dns_settings
import logging
import json
import multiprocessing


class FindMeGoogleIP:
    BASE_DIR = os.path.dirname(os.path.realpath(__file__))
    DNS_SERVERS_DIR = os.path.join(BASE_DIR, 'dns_servers')

    def __init__(self, locations):
        self.locations = locations
        self.dns_servers = []
        self.resolved_ips = {}
        self.reachable = []
        self.concatenated_result = None
        self.json_result = None
        self.progress_percentage = 0

    @staticmethod
    def read_domains():
        return [f.replace('.txt', '') for f in os.listdir(FindMeGoogleIP.DNS_SERVERS_DIR)]

    def run_threads(self, threads, limit=None):
        """A general way to run multiple threads"""
        if not limit:
            limit = dns_settings.threads
        lock = threading.Lock()
        total = len(threads)
        for index, thread in enumerate(threads):
            thread.lock = lock
            if threading.active_count() > limit:
                time.sleep(1)

            logging.info("Starting thread (%s/%s)" % (index, total))
            self.progress_percentage = (index+1) * 100 / total
            thread.start()

        for thread in threads:
            thread.join()

    def get_dns_servers(self):
        if self.locations == ['all']:
            self.locations = self.read_domains()

        try:
            for location in self.locations:
                domain_file = os.path.join(self.DNS_SERVERS_DIR, location+'.txt')
                logging.info('reading servers from file %s' % domain_file)
                with open(domain_file) as f:
                    data = f.read().strip()
                    if data:
                        servers = re.split('\s+', data)
                        random.shuffle(servers)
                        for server in servers[:dns_settings.servers]:
                            self.dns_servers.append((server, location))
        except IOError:
            logging.error("Cannot read dns servers")

    def lookup_ips(self):
        threads = [NsLookup('google.com', server, self.resolved_ips) for server in self.dns_servers]
        self.run_threads(threads)

    def check_service(self):
        threads = [ServiceCheck(ip, self.resolved_ips[ip][0], self.reachable) for ip in self.resolved_ips.keys()]
        self.run_threads(threads)

    def cleanup_low_quality_ips(self):
        """
        For ips in the same range, if success_rate does not satisfy a pre-defined threshold,
        they'll be all treated as low quality and removed.
        """
        reachable = {ip for ip, rtt in self.reachable}
        success_count = {}
        fail_count = {}
        success_rate = {}
        threshold = 80  # 80%

        for ip in self.resolved_ips.keys():
            prefix = self.get_ip_prefix(ip)
            if ip in reachable:
                success_count[prefix] = success_count.get(prefix, 0) + 1
            else:
                fail_count[prefix] = fail_count.get(prefix, 0) + 1

        for prefix in success_count.keys():
            success_rate[prefix] = 100 * success_count[prefix] // (success_count[prefix] + fail_count.get(prefix, 0))

        self.reachable = [(ip, rtt) for ip, rtt in self.reachable
                          if success_rate.get(self.get_ip_prefix(ip), 0) >= threshold]

    @staticmethod
    def get_ip_prefix(ip):
        return re.sub('\.[0-9]+$', '', ip)

    def get_results(self):
        if self.reachable:
            reachable_sorted = sorted(self.reachable, key=lambda x: x[1])
            self.concatenated_result = '|'.join(ip for ip, rtt in reachable_sorted)
            self.json_result = [ip for ip, rtt in reachable_sorted]
            return self.json_result
        else:
            logging.info("No available servers found")
            return None


    def run(self):
        self.get_dns_servers()
        self.lookup_ips()
        self.check_service()
        # self.cleanup_low_quality_ips()
        return self.get_results()

    def update_dns_files(self):
        threads = [DNSServerFileDownload(location) for location in FindMeGoogleIP.read_domains()]
        self.run_threads(threads, 50)
        logging.info('finished')


class DNSServerFileDownload(threading.Thread):
    def __init__(self, location):
        threading.Thread.__init__(self)
        self.domain = location
        self.url = "http://public-dns.info/nameserver/%s.txt" % location
        self.file = os.path.join(FindMeGoogleIP.DNS_SERVERS_DIR, '%s.txt' % location)
        self.lock = None

    def run(self):
        try:
            logging.info('downloading file %s' % self.url)
            proxy_handler = urllib2.ProxyHandler(proxies=dns_settings.proxies)
            opener = urllib2.build_opener(proxy_handler)
            data = opener.open(self.url, timeout=5).read().decode()
            with open(self.file, mode='w') as f:
                f.write(data)
        except IOError as err:
            logging.error('cannot(%s) update file %s' % (str(err), self.file))


class ServiceCheck(threading.Thread):
    def __init__(self, ip, host, servicing):
        threading.Thread.__init__(self)
        self.ip = ip
        self.host = host
        self.port = 443
        self.lock = None
        self.servicing = servicing

    def run(self):
        try:
            logging.info('checking ssl service %s:%s' % (self.ip, self.port))
            socket.setdefaulttimeout(5)
            conn = ssl.create_default_context().wrap_socket(socket.socket(), server_hostname=self.host)
            conn.connect((self.ip, self.port))

            start = time.time()
            socket.create_connection((self.ip, self.port))
            end = time.time()
            rtt = int((end-start)*1000)  # milliseconds

            with self.lock:
                self.servicing.append((self.ip, rtt))

        except (ssl.CertificateError, ssl.SSLError, socket.timeout, OSError) as err:
            logging.error("error(%s) on connecting %s:%s" % (str(err), self.ip, self.port))


class NsLookup(threading.Thread):
    def __init__(self, name, server, store):
        threading.Thread.__init__(self)
        self.name = name
        self.server = server
        self.lock = None
        self.store = store
        self.resolver = dns.resolver.Resolver()
        self.resolver.nameservers = [self.server[0]]
        self.resolver.lifetime = 5

    def run(self):
        try:
            logging.info('looking up %s from %s' % (self.name, self.server))
            answer = self.resolver.query(self.name)
            with self.lock:
                for response in answer:
                    ip = str(response)
                    if not self.is_spf(ip):
                        self.store[ip] = (self.name, self.server[1])
        except (dns.exception.DNSException, ValueError):
            pass

    @staticmethod
    def is_spf(ip):
        ips = {'64.18.', '64.233.', '66.102.', '66.249.', '72.14.', '74.125.', '173.194.', '207.126.', '209.85.',
               '216.58.', '216.239.'}
        if re.sub('\.[0-9]+\.[0-9]+$', '.', ip) in ips:
            return True
        else:
            return False
# DNSQuery class from http://code.activestate.com/recipes/491264-mini-fake-dns-server/
class DNSQuery:
    def __init__(self, data):
        self.data=data
        self.domain=''

        tipo = (ord(data[2]) >> 3) & 15   # Opcode bits
        if tipo == 0:                     # Standard query
            ini=12
            lon=ord(data[ini])
            while lon != 0:
                self.domain+=data[ini+1:ini+lon+1]+'.'
                ini+=lon+1
                lon=ord(data[ini])

    def respuesta(self, ip):
        logging.debug("In DNSQuery's respuesta,gen return packte \
                for %s"%ip)
        packet=''
        if self.domain:
            packet+=self.data[:2] + "\x81\x80"
            packet+=self.data[4:6] + self.data[4:6] + '\x00\x00\x00\x00'   # Questions and Answers Counts
            packet+=self.data[12:]                                         # Original Domain Name Question
            packet+='\xc0\x0c'                                             # Pointer to domain name
            packet+='\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'             # Response type, ttl and resource data length -> 4 bytes
            packet+=str.join('',map(lambda x: chr(int(x)), ip.split('.'))) # 4bytes of IP
        return packet

class DNSServer:
    '''
    use host_ip_map dict to do local resolve,
    and query results from upper server when domain not in this map.
    map dict format {'domain',[ip,ip,ip]}
    randomly return one of the ips in ip list
    '''
    def __init__(self,host_ip_map,upper_server,bind_address_tuple):
        self._host_ip_map = host_ip_map
        self._upper_name_server = upper_server
        self._resolver = dns.resolver.Resolver()
        self._resolver.nameservers = [self._upper_name_server]
        self._resolver.lifetime = 5
        self._bind_address_tuple = bind_address_tuple
    def run(self):
        logging.debug(">>>>>>starting udp dns name server")
        try:
            udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_server.bind(self._bind_address_tuple) #only answer local queries,set to 127.0.0.1
        except Exception, e:
            print("Failed to create socket on UDP port 53:",e)
            sys.exit(1)
        def get_ip_address_by_domain(domain,host_ip_map,resolver):
            ip_address = '127.0.0.1'
            domain = domain.rstrip('.')
            if(host_ip_map.has_key(domain)):
                ip_address = host_ip_map[domain][random.randint(0,\
                        len(host_ip_map[domain])-1)] #random choose one of the ips in list
                logging.debug(">>>>>>find %s in %s"%(domain,ip_address))
            else:
                logging.debug(">>>>>>resolve %s from upper name server"%domain)
                answer = resolver.query(domain) #may occur timeout or other dns erro
                                                #auto break is enough, no more action
                for response in answer:
                    ip_address = str(response)
                    #only return the last ip in query answer
            logging.debug(">>>>>>domain %s's ip is %s"%(domain,ip_address))
            return  ip_address


        def query_and_send_back_ip(data, addr, udp_server, host_ip_map, resolver):
            try:
                p=DNSQuery(data)
                logging.info('Request domain: %s' % p.domain)
                ip = get_ip_address_by_domain(p.domain,host_ip_map,resolver)
                udp_server.sendto(p.respuesta(ip), addr)
            except Exception, e:
                print 'query for:%s error:%s' % (p.domain, e)
        while True:
            data, addr = udp_server.recvfrom(1024)
            logging.debug(">>>>>>recived new dns query, starting new thread")
            thread = threading.Thread(target=query_and_send_back_ip,args=(data,addr,udp_server,self._host_ip_map,self._resolver))
            thread.start()
        udp_server.close()


def update_host_ip_map_daemon(shared_host_ip_dict):
    while True:
        time.sleep(24*3600)  #wait 24hrs before next update
        update_google_ips(shared_host_ip_dict)

def update_google_ips(shared_host_ip_dict):
    domains = ['jp']
    #domains = ['jp','tw','hk','us','kr','fr']
    ip_list = FindMeGoogleIP(domains).run()
    if(ip_list == None):
        print('No available ip found')
    else:
        print(ip_list)
        IPs = int(len(ip_list)/3)
        if(IPs < 50):
            num_of_IPs = len(ip_list)
        elif(IPs > 100):
            num_of_IPs = 100
        else:
            num_of_IPs = IPs
        logging.debug("num_of_ips is %d "%num_of_IPs)
        #update shared_host_ip_dict
        shared_host_ip_dict['scholar.google.com'] = ip_list[:num_of_IPs]

def run_dns_server(host_ip_map,upper_dns_server,bind_address_tuple):
    dns_server = DNSServer(host_ip_map,upper_dns_server,bind_address_tuple)
    dns_server.run()

if __name__ == "__main__":
    DEBUG = dns_settings.debug
    if(DEBUG):
        logging.basicConfig(format='%(message)s', level=logging.DEBUG)
        class FindMeGoogleIP:
            def __init__(self,domain):
                pass
            def run(self):
                logging.debug("for debug, only return a empty list")
                return ['1.2.3.4','2.2.3.4','3.4.5.6','7.8.9.10',
                '8.9.10.11','9.10.11.12']
    else:
        logging.basicConfig(format='%(message)s', level=logging.CRITICAL)
    if len(sys.argv) >= 2:
        if sys.argv[1] == 'update':
            FindMeGoogleIP([]).update_dns_files()
#        else:
#            FindMeGoogleIP(sys.argv[1:]).run()
#    else:
#        domain = [random.choice(FindMeGoogleIP.read_domains())]
#        logging.info("Usage:")
#        logging.info("Find ips in specified domains: findmegoogleip.py kr us")
#        logging.info("=" * 50)
#        logging.info("Now running default: find ip from a randomly chosen domain: %s" % domain[0])
    upper_server = dns_settings.upper_dns_server #opendns's dns server
    bind_address_tuple =  dns_settings.bind_tuple #only accept local dns queries

    manager = multiprocessing.Manager() #using manager to generate dict to share between processes
    host_ip_map = manager.dict()

    logging.debug(">>>>>>updating google ip map the first time")
    update_google_ips(host_ip_map) 		#generate host_ip_map first of all
    logging.debug(">>>>>>starting host_ip_map update daemon process")
    host_ip_map_update_process = multiprocessing.Process(target=\
            update_host_ip_map_daemon,args=(host_ip_map,))

    logging.debug(">>>>>>starting dns server daemon process")
    dns_server_process = multiprocessing.Process(target=run_dns_server,\
            args=(host_ip_map,upper_server,bind_address_tuple))
    host_ip_map_update_process.start()
    dns_server_process.start()
    dns_server_process.join()
