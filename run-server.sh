#!/bin/sh
docker rm -f scihub_container
docker rmi -f scihub

cd /root/tornado_proxy && git pull
pip install -r /root/tornado_proxy/requirements.txt
# python /root/tornado_proxy/tornado_proxy/findmegoogleip.py &

cp /root/tornado_proxy/Dockerfile /root/docker/

cd /root
docker build --no-cache -t scihub ./docker

# docker --dns=172.17.0.1 run --name scihub_container -v /etc/letsencrypt/:/media/ -p 80:80 -p 443:443 scihub
 docker  run --name scihub_container -v /etc/letsencrypt/:/media/ -p 80:80 -p 443:443 scihub
