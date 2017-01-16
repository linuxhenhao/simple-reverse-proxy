#!/bin/sh
rm /etc/resolv.conf
echo "nameserver 127.0.0.1" > /etc/resolv.conf
python /root/tornado_proxy/findmegoogleip.py &
python /root/tornado_proxy/proxy.py
