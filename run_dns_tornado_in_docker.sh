#!/bin/sh
rm /etc/resolv.conf
echo "nameserver 127.0.0.1" > /etc/resolv.conf
python /root/tornado-proxy/FindMeGoogleIP/findmegoogleip.py &
python /root/tornado-proxy/tornado-proxy/proxy.py
