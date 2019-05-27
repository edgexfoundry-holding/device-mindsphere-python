# Copyright (C) 2018-2019 Dell Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License.  You
# may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.  See the License for the specific language governing
# permissions and limitations under the License.

"""MindsphereDeviceConnector.

This module will send data to Mindsphere.

Example:
    Please run the module using below command::

        $ python mindsphere_device_connector.py


Attributes:
    MQTT_JSON_ARRAY (json array): this variable will be used for storing Mqtt
        Config data in Json format.
    REST_JSON_ARRAY (json array): this variable will be used for storing Rest
        Config data in Json format.
    MQTT_JSON_IS_VALID (boolean): this variable will be used for checking
        whether Mqtt Json is in correct format.
    REST_JSON_IS_VALID (boolean): this variable will be used for checking
        whether Rest Json is in correct format.

"""

from datetime import datetime
import json
import time
import pymongo
import paho.mqtt.client as paho
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
from bottle import route, run, request, response


MQTT_JSON_ARRAY = []
REST_JSON_ARRAY = []
MQTT_JSON_IS_VALID = False
REST_JSON_IS_VALID = False
MQTT_JSON_ERROR_MSG = ''
REST_JSON_ERROR_MSG = ''
CLIENT = None
OAUTHCLIENT = None
ACCESS_TOKEN = None

def log_exception(log_level, msg):
    """Logs the ERROR, INFO message in log collecton
    Args:
      log_level: Either ERROR or INFO
      msg: Message required to log.
    Raises:
      IOError: If unable to store value.
      ConnectionError: Unable to connect database.
    """
    try:
        myclient = pymongo.MongoClient(MONGODB_URL)
        mydb = myclient["logging"]
        mycol = mydb["logEntry"]
        time_stamp = int(round(time.time() * 1000))
        log_message = {"logLevel" : log_level, "labels" :[], "originService"\
        : "mindsphere-connector-service", "message" : msg, "created" : \
        'NumberLong('+str(time_stamp)+')'}
        mycol.insert_one(log_message)
        myclient.close()
    except (KeyError, AttributeError, ValueError, TypeError, \
            pymongo.errors.PyMongoError) as ex:
        print("ERROR Logged in log_exception: {0}".format(ex))

def check_mqtt_config_values():
    """Read mqtt config values form database
       and validate the values.

    Raises:
      Exception: If any exception occur.
    """
    try:
        global MQTT_JSON_ARRAY
        global MQTT_JSON_IS_VALID
        global MQTT_JSON_ERROR_MSG
        MQTT_JSON_IS_VALID = False
        MQTT_JSON_ERROR_MSG = ''
        myclient = pymongo.MongoClient(MONGODB_URL)
        mydb = myclient["mindspheredeviceconnectorservice"]
        mycol = mydb["config"]
        for mqtt_array in mycol.find({"MqttConfigValues.destination":\
        "MQTT_TOPIC"}, {"_id": 0}):
            MQTT_JSON_ARRAY = mqtt_array['MqttConfigValues']
            for mqtt_json in MQTT_JSON_ARRAY:
                if mqtt_json['addressable']['port'] is None:
                    MQTT_JSON_ERROR_MSG = 'Port'
                elif mqtt_json['addressable']['address'] is None:
                    MQTT_JSON_ERROR_MSG = 'Address'
                elif mqtt_json['addressable']['publisher'] is None:
                    MQTT_JSON_ERROR_MSG = 'Publisher'
                elif mqtt_json['addressable']['user'] is None:
                    MQTT_JSON_ERROR_MSG = 'User'
                elif mqtt_json['addressable']['password'] is None:
                    MQTT_JSON_ERROR_MSG = 'Password'
                elif mqtt_json['addressable']['topic'] is None:
                    MQTT_JSON_ERROR_MSG = 'Topic'
                else:
                    MQTT_JSON_IS_VALID = True
        MQTT_JSON_ERROR_MSG += ' is missing in MQTT config'
        myclient.close()
    except (KeyError, AttributeError, ValueError, TypeError, \
            pymongo.errors.PyMongoError) as ex:
        log_exception("ERROR", "Logged in reading mqtt_json: {0}".format(ex))
        MQTT_JSON_ERROR_MSG = "ERROR in reading MQTT config:{0}".format(ex)


def check_rest_config_values():
    """Read rest config values form database
       and validate the values.

    Raises:
      Exception: If any exception occur.
    """
    try:
        global REST_JSON_ARRAY
        global REST_JSON_IS_VALID
        global REST_JSON_ERROR_MSG
        REST_JSON_IS_VALID = False
        REST_JSON_ERROR_MSG = ''
        myclient = pymongo.MongoClient(MONGODB_URL)
        mydb = myclient["mindspheredeviceconnectorservice"]
        mycol = mydb["config"]
        for rest_array in mycol.find({"RestConfigValues.destination":\
        "REST_ENDPOINT"}, {"_id": 0}):
            REST_JSON_ARRAY = rest_array['RestConfigValues']
            for rest_json in REST_JSON_ARRAY:
                if rest_json['addressable']['protocol'] is None:
                    REST_JSON_ERROR_MSG = 'Protocol'
                elif rest_json['addressable']['address'] is None:
                    REST_JSON_ERROR_MSG = 'Address'
                elif rest_json['addressable']['path'] is None:
                    REST_JSON_ERROR_MSG = 'Path'
                elif rest_json['addressable']['user'] is None:
                    REST_JSON_ERROR_MSG = 'User'
                elif rest_json['addressable']['password'] is None:
                    REST_JSON_ERROR_MSG = 'Password'
                elif rest_json['addressable']['refreshUrl'] is None:
                    REST_JSON_ERROR_MSG = 'RefreshUrl'
                else:
                    REST_JSON_IS_VALID = True
        REST_JSON_ERROR_MSG += ' is missing in REST config'
        myclient.close()
    except (KeyError, AttributeError, ValueError, TypeError, \
            pymongo.errors.PyMongoError) as ex:
        log_exception("ERROR", "Logged in reading rest_json: {0}".format(ex))
        REST_JSON_ERROR_MSG = "ERROR in reading REST config: {0}".format(ex)


@route('/time')
def get_time():
    """
    To get the system time
    """
    current_time = datetime.now().isoformat(' ')
    return {"system": 1, "datetime": current_time}


@route('/senddata/mqtt', method='POST')
def send_mqtt_data():
    """Receive sensor data and send those to Mindsphere through MQTT

    Args:
      json_data: Sensor data in JSON format
    Raises:
      IOError: Unable to call connector service API.
      ConnectionError: If unable to connect to Connector Service
    """
    try:
        global MQTT_JSON_ARRAY
        global MQTT_JSON_IS_VALID
        global MQTT_JSON_ERROR_MSG
        device_found = False
        if MQTT_JSON_IS_VALID is False:
            check_mqtt_config_values()
        mqtt_status = {}
        if MQTT_JSON_IS_VALID:
            body = request.body.read().decode("utf-8")
            body = body.replace("null", "\"None\"")
            json_data = json.loads(body)
            for row in MQTT_JSON_ARRAY:
                if row['filter']['deviceIdentifiers'][0] == json_data['device']:
                    mqtt_json = row
                    device_found = True
                    break
            if not device_found:
                return {"status": "device name not found in Mqtt Json Config"}
            mqtt_msg = ""
            for row in json_data['readings']:
                mqtt_msg += "200,"+row['name']+","+row['name']+","+\
                row['value']+","+row['name']+"\n"
            mqtt_client = paho.Client(\
                client_id=mqtt_json['addressable']['publisher'], \
                clean_session=True, userdata=None, protocol=paho.MQTTv311)
            mqtt_client.username_pw_set(mqtt_json['addressable']['user'], \
            mqtt_json['addressable']['password'])
            mqtt_client.connect(mqtt_json['addressable']['address'], \
            mqtt_json['addressable']['port'])
            mqtt_client.publish(mqtt_json['addressable']['topic'], mqtt_msg)
            mqtt_status = {"status": "inserted"}
        else:
            mqtt_status = MQTT_JSON_ERROR_MSG
        return mqtt_status
    except Exception as ex:
        log_exception("Error", "Logged in sendmqttdata: {0}".format(ex))


@route('/senddata/rest', method='POST')
def send_rest_data():
    """Receive sensor data and send those to Mindsphere through REST

    Args:
      json_data: Sensor data in JSON format
    Raises:
      IOError: Unable to call connector service API.
      ConnectionError: If unable to connect to Connector Service
    """
    try:
        global REST_JSON_ARRAY
        global REST_JSON_IS_VALID
        global REST_JSON_ERROR_MSG
        global CLIENT
        rest_json = []
        device_found = False
        if REST_JSON_IS_VALID is False:
            check_rest_config_values()
        if REST_JSON_IS_VALID:
            body = request.body.read().decode("utf-8")
            body = body.replace("None", "\"None\"")
            body = body.replace("null", "\"None\"")
            json_data = json.loads(body)
            for row in REST_JSON_ARRAY:
                if row['filter']['deviceIdentifiers'][0] == json_data['device']:
                    rest_json = row
                    device_found = True
                    break
            if not device_found:
                return {"status": "device name not found in Rest Json Config"}
            current_time_gmt = datetime.utcnow()
            timestamp = current_time_gmt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            msg = '[{"_time" : "' + timestamp + '"'
            for row in json_data['readings']:
                msg += ',"' + row['name'] + '" : "' + row['value'] + '"'
            msg += '}]'
            rest_msg = json.loads(msg)
            url = "{0}://{1}{2}".format(rest_json['addressable']['protocol'], \
            rest_json['addressable']['address'], \
            rest_json['addressable']['path'])
            CLIENT.put(url, json=rest_msg, headers={'Content-Type':\
            'application/json'})
            return {"status": "inserted"}
        else:
            return REST_JSON_ERROR_MSG
    except Exception as ex:
        log_exception("Error", "Logged in sendrestdata: {0}".format(ex))
        try:
            global OAUTHCLIENT
            global ACCESS_TOKEN
            OAUTHCLIENT = BackendApplicationClient(client_id=rest_json\
            ['addressable']['user'])
            oauthsession = OAuth2Session(client=OAUTHCLIENT)
            ACCESS_TOKEN = oauthsession.fetch_token(token_url=rest_json\
            ['addressable']['refreshUrl'], client_id=rest_json['addressable']\
            ['user'], client_secret=rest_json['addressable']['password'])
            CLIENT = OAuth2Session(client_id=rest_json['addressable']['user']\
            , token=ACCESS_TOKEN)
            url = "{0}://{1}{2}".format(rest_json['addressable']['protocol'], \
            rest_json['addressable']['address'], rest_json['addressable']\
            ['path'])
            CLIENT.put(url, json=rest_msg, headers={'Content-Type':\
            'application/json'})
            return {"status": "inserted"}
        except Exception as ex1:
            log_exception("Error", "Logged in sendrestdata inner catch block:"\
            "{0}".format(ex1))
            return {"status": "not inserted"}


@route('/getdata/<path:path>', method='GET')
def getdata(path):
    """Receive url and call this url to get threshold values

    Args:
      URL: this url will be used to get threshold values and return as response
    Raises:
      IOError: Unable to call connector service API.
      ConnectionError: If unable to connect to Connector Service
    """
    try:
        global REST_JSON_ARRAY
        global REST_JSON_IS_VALID
        global REST_JSON_ERROR_MSG
        global CLIENT
        device_found = False
        str_len = path.find('/')
        device_name = path[:str_len]
        app_url = path[(str_len+1):]
        get_data_response = {"status": "error"}
        if REST_JSON_IS_VALID is False:
            check_rest_config_values()
        if REST_JSON_IS_VALID:
            for row in REST_JSON_ARRAY:
                if row['filter']['deviceIdentifiers'][0] == device_name:
                    rest_json = row
                    device_found = True
                    break
            if not device_found:
                return {"status": "device name not found in Rest Json Config"}
            url = "{0}://{1}/{2}".format(rest_json['addressable']['protocol'], \
            rest_json['addressable']['address'], app_url)
            resp = CLIENT.get(url)
            get_data_response = resp.json()
        else:
            return REST_JSON_ERROR_MSG
    except Exception as ex:
        log_exception("ERROR", "Logged in GetData: {0}".format(ex))
        try:
            global OAUTHCLIENT
            global ACCESS_TOKEN
            OAUTHCLIENT = BackendApplicationClient(client_id=rest_json\
            ['addressable']['user'])
            oauthsession = OAuth2Session(client=OAUTHCLIENT)
            ACCESS_TOKEN = oauthsession.fetch_token(token_url=\
            rest_json['addressable']['refreshUrl'], client_id=rest_json\
            ['addressable']['user'], client_secret=\
            rest_json['addressable']['password'])
            CLIENT = OAuth2Session(client_id=\
            rest_json['addressable']['user'], token=ACCESS_TOKEN)
            url = "{0}://{1}/{2}".format(rest_json['addressable']['protocol'], \
            rest_json['addressable']['address'], app_url)
            resp = CLIENT.get(url)
            get_data_response = resp.json()
        except Exception as ex1:
            log_exception("ERROR", "Logged in GetData inner catch block: "\
            "{0}".format(ex1))
    return get_data_response


@route('/log', method='GET')
def get_log():
    """Read log data from database

    Raises:
      IOError: Unable to read from database.
      ConnectionError: If unable to connect to database
    """
    try:
        myclient = pymongo.MongoClient(MONGODB_URL)
        mydb = myclient["logging"]
        mycol = mydb["logEntry"]

        log_data = "["
        for row in mycol.find(\
            {"originService": "mindsphere-connector-service"}, {"_id": 0}):
            if log_data == "[":
                log_data += json.dumps(row)
            else:
                log_data += "," + json.dumps(row)
        log_data += "]"
        response.content_type = 'application/json'
        myclient.close()
        return log_data
    except pymongo.errors.PyMongoError as ex:
        log_exception("ERROR", "Logged in get_log : {0}".format(ex))


@route('/log', method='DELETE')
def delete_log():
    """Delete log data from database

    Raises:
      IOError: Unable to delete from database.
      ConnectionError: If unable to connect to database
    Return:
      Status : Return number or records deleted
    """
    try:
        myclient = pymongo.MongoClient(MONGODB_URL)
        mydb = myclient["logging"]
        mycol = mydb["logEntry"]
        status = mycol.delete_many(
            {"originService": "mindsphere-connector-service"})
        myclient.close()
        return {"No of deleted records": status.deleted_count}
    except pymongo.errors.PyMongoError as ex:
        log_exception("ERROR", "Logged in delete_log : {0}".format(ex))



@route('/config/mqtt', method='GET')
def get_config_mqtt():
    """Read Mqtt config data from database

    Raises:
      IOError: Unable to read from database.
      ConnectionError: If unable to connect to database
    Return:
      Config data : Return config data
    """
    try:
        myclient = pymongo.MongoClient(MONGODB_URL)
        mydb = myclient["mindspheredeviceconnectorservice"]
        mycol = mydb["config"]

        config_data = "["
        for row in mycol.find({"MqttConfigValues.destination": "MQTT_TOPIC"},\
                              {"_id": 0}):
            if config_data == "[":
                config_data += json.dumps(row)
            else:
                config_data += "," + json.dumps(row)
        config_data += "]"
        response.content_type = 'application/json'
        config_data = config_data.replace('\'', '"')
        myclient.close()
        return config_data
    except pymongo.errors.PyMongoError as ex:
        log_exception("ERROR", "Logged in get_config_mqtt : {0}".format(ex))


@route('/config/mqtt', method='PUT')
def update_config_mqtt():
    """Update Mqtt config data to database

    Raises:
      IOError: Unable to update to database.
      ConnectionError: If unable to connect to database
    Return:
      Config data : Return config data
    """
    try:
        myclient = pymongo.MongoClient(MONGODB_URL)
        mydb = myclient["mindspheredeviceconnectorservice"]
        mycol = mydb["config"]
        data = request.body.read().decode("utf-8")
        json_data = json.loads(data)
        mycol.delete_one({"MqttConfigValues.destination": "MQTT_TOPIC"})
        mycol.insert_one(json_data)
        myclient.close()
        check_mqtt_config_values()
    except (KeyError, AttributeError, ValueError, TypeError,\
            pymongo.errors.PyMongoError) as ex:
        log_exception("ERROR", "Logged in update_config_mqtt : {0}".format(ex))


@route('/config/rest', method='GET')
def get_config_rest():
    """Read Rest config data from database

    Raises:
      IOError: Unable to read from database.
      ConnectionError: If unable to connect to database
    Return:
      Config data : Return config data
    """
    try:
        myclient = pymongo.MongoClient(MONGODB_URL)
        mydb = myclient["mindspheredeviceconnectorservice"]
        mycol = mydb["config"]
        config_data = "["
        for row in mycol.find({"RestConfigValues.destination": "REST_ENDPOINT"}\
                              , {"_id": 0}):
            if config_data == "[":
                config_data += json.dumps(row)
            else:
                config_data += "," + json.dumps(row)
        config_data += "]"
        response.content_type = 'application/json'
        config_data = config_data.replace('\'', '"')
        myclient.close()
        return config_data
    except pymongo.errors.PyMongoError as ex:
        log_exception("ERROR", "Logged in get_config_rest : {0}".format(ex))


@route('/config/rest', method='PUT')
def update_config_rest():
    """Update Rest config data to database

    Raises:
      IOError: Unable to update to database.
      ConnectionError: If unable to connect to database
    Return:
      Config data : Return config data
    """
    try:
        myclient = pymongo.MongoClient(MONGODB_URL)
        mydb = myclient["mindspheredeviceconnectorservice"]
        mycol = mydb["config"]
        data = request.body.read().decode("utf-8")
        json_data = json.loads(data)
        mycol.delete_one({"RestConfigValues.destination": "REST_ENDPOINT"})
        mycol.insert_one(json_data)
        myclient.close()
        check_rest_config_values()
    except (KeyError, AttributeError, ValueError, TypeError, \
            pymongo.errors.PyMongoError) as ex:
        log_exception("ERROR", "Logged in update_config_rest : {0}".format(ex))


MONGO_DB_IP = os.environ['EXPORT_CLIENT_MONGO_URL']
MONGODB_URL = "mongodb://" + str(MONGO_DB_IP) + ":27017/"


check_mqtt_config_values()
check_rest_config_values()

run(host='0.0.0.0', port=8105)
