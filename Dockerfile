FROM alpine

MAINTAINER Yu Huang

WORKDIR /etc/
RUN touch INDOCKER

WORKDIR /root/
RUN apk update
RUN apk add python
RUN apk add py-pip
RUN apk add git
RUN apk add py-curl
RUN git clone -b urlredirect https://github.com/linuxhenhao/tornado_proxy.git
RUN pip install -r tornado_proxy/requirements.txt

CMD sh /root/tornado_proxy/run_dns_tornado_in_docker.sh

EXPOSE 443
EXPOSE 80
