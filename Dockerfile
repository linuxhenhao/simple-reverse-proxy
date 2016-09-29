FROM alpine

MAINTAINER Yu Huang

WORKDIR /root/
RUN apk update
RUN apk add python
RUN apk add py-pip
RUN apk add git
RUN git clone -b urlredirect https://github.com/linuxhenhao/tornado_proxy.git
RUN pip install -r tornado_proxy/requirements.txt

CMD python /root/tornado_proxy/tornado_proxy/proxy.py

EXPOSE 8888 
