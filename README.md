# MindSphere Device Connector (Python)
device-mindsphere-python is a library which provides the way to connect to MindSphere and exchange data.
 - HTTP protocol.
 - MQTT messaging protocol .


## Prerequisites ##
- Docker
  - Version : 18.09.5 or above
  - [Where to download](https://www.docker.com/)
  - [How to install](https://www.docker.com/)
- Docker Compose
  - Version : 1.24.0 or above
  - [Where to download](https://docs.docker.com/compose/)
  - [How to install](https://docs.docker.com/compose/install/)

## How to create docker image ##
```
docker build -t mindsphere-connector-service . 
```

## How to tag ##
```
docker tag mindsphere-connector-service edgexfoundry/mindsphere-connector-service:1.0
``` 
## How to run ##
Download docker-compose.yml from Docker folder and run below command
```
1.docker-compose pull
2.docker-compose up -d
```

## Configuring to export data using HTTP protocol ##
URL : http://edgex-mindsphere-connector:8107/config/rest, Method : PUT
```
BODY: {“RestConfigValues”: [{
  "name": "MindSphereREST",
  "addressable": {
    "name": "MindSphereREST",
    "protocol": "https",
    "method": "POST",
    "address": "gateway.eu1.MindSphere.io",
    "port": null,
    "path": "/api/iottimeseries/v3/timeseries/0ce91e5d0d3543919b45c03d85e7dff4/MotorAspect",
    "publisher": null,
    "user": "ServiceCredentialsUser",
    "password": "ServiceCredentialsTokenPassword",
    "topic": null,
    "refreshUrl" : "https://tenantname.piam.eu1.MindSphere.io/oauth/token"
  },
  "format": "JSON",
  "filter": {
    "deviceIdentifiers": ["motordevice"]
  },
  "encryption": {},
  "enable": true,
  "destination": "REST_ENDPOINT"
}]}
```

## Configuring to export data using MQTT protocol  ##
URL : http://edgex-mindsphere-connector:8107/config/mqtt, Method : PUT
```
BODY: {“RestConfigValues”: [{
    "name":"MindSphereMQTT ",
    "addressable":{
        "name":"MindSphereMQTT ",
        "protocol":"tcp",
        "method": null,
        "address":"tenantname.mciotextension.eu-central.MindSphere.io",
        "port":1883,
        "publisher":"edgexmqtt",
        "topic":"s/us",
        "user": "tenantName/userId",
        "password": "password"
    },
    "format":"JSON",
    "filter":{
        "deviceIdentifiers":["motordevice"]
    },
    "enable":true,
    "destination":"MQTT_TOPIC"
} ]}
```
