FROM alpine:3.5
RUN apk add --update \
    python3
RUN pip3 install bottle
RUN pip3 install requests_oauthlib
RUN pip3 install paho-mqtt
RUN pip3 install pymongo
EXPOSE 8105
COPY mindsphere_device_connector.py /mindsphere_device_connector_1_0.py
CMD python3 /mindsphere_device_connector_1_0.py
