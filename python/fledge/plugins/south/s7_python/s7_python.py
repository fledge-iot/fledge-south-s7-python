# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge.readthedocs.io/
# FLEDGE_END


# ***********************************************************************
# * DISCLAIMER:
# *
# * All sample code is provided by ACDP for illustrative purposes only.
# * These examples have not been thoroughly tested under all conditions.
# * ACDP provides no guarantee nor implies any reliability,
# * serviceability, or function of these programs.
# * ALL PROGRAMS CONTAINED HEREIN ARE PROVIDED TO YOU "AS IS"
# * WITHOUT ANY WARRANTIES OF ANY KIND. ALL WARRANTIES INCLUDING
# * THE IMPLIED WARRANTIES OF NON-INFRINGEMENT, MERCHANTABILITY
# * AND FITNESS FOR A PARTICULAR PURPOSE ARE EXPRESSLY DISCLAIMED.
# ************************************************************************


import copy
import json
import logging

import snap7
from snap7.util import *
from snap7.types import *

from fledge.common import logger
from fledge.plugins.common import utils
from fledge.services.south import exceptions

""" Plugin for reading data from a S7 TCP data source

    This plugin uses the snap7 library, to install this perform the following steps:

        pip install python-snap7

    You can learn more about this library here:
        https://pypi.org/project/python-snap7/
    The library is licensed under the BSD License (BSD).

    As an example of how to use this library:

        import snap7
        
        client = snap7.client.Client()
        client.connect("127.0.0.1", 0, 0, 1012)
        client.get_connected()

        data = client.db_read(1, 0, 4)
        
        print(data)
        ???client.close()

"""

__author__ = "Sebastian Kropatschek"
__copyright__ = "Copyright (c) 2018 ACDP"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


""" _DEFAULT_CONFIG with S7 Entities Map

    The coils and registers each have a read-only table and read-write table.
    
        Coil	Read-write	1 bit
        Discrete input	Read-only	1 bit
        Input register	Read-only	16 bits
        Holding register	Read-write	16 bits 
"""

_DEFAULT_CONFIG = {
    'plugin': {
        'description': 'Siemens S7 TCP South Service Plugin',
        'type': 'string',
        'default': 's7',
        'readonly': 'true'
    },
    'assetName': {
        'description': 'Asset name',
        'type': 'string',
        'default': 'S7 TCP',
        'order': "1",
        'displayName': 'Asset Name',
        'mandatory': 'true'
    },
    'host': {
        'description': 'Host IP address of the PLC',
        'type': 'string',
        'default': '127.0.0.1',
        'order': '2',
        'displayName': 'Host TCP Address'
    },
    'rack': {
        'description': 'Rack number where the PLC is located',
        'type': 'integer',
        'default': '0',
        'order': '3',
        'displayName': 'Rack'
    },
    'slot': {
        'description': 'Slot number where the CPU is located.',
        'type': 'integer',
        'default': '0',
        'order': '4',
        'displayName': 'Slot'
    },
    'port': {
        'description': 'Port of the PLC',
        'type': 'integer',
        'default': '102',
        'order': '5',
        'displayName': 'Port'
    },
    'map': {
        'description': 'S7 register map',
        'type': 'JSON',
        'default': json.dumps({
            "DB": {
                "788": {
                    "0.0":   {"name": "Job",             "type": "String[255]"},
                    "256.0": {"name": "Count",           "type": "UInt"},
                    "258.0": {"name": "Active",          "type": "Bool"},
                    "258.1": {"name": "TESTVAR_Bits",    "type": "Bool"},
                    "260.0": {"name": "TESTVAR_Word",    "type": "Word"},
                    "262.0": {"name": "TESTVAR_Int",     "type": "Int"},
                    "264.0": {"name": "TESTVAR_DWord",   "type": "DWord"},
                    "268.0": {"name": "TESTVAR_DInt",    "type": "DInt"},
                    "272.0": {"name": "TESTVAR_Real",    "type": "Real"},
                    "276.0": {"name": "TESTVAR_String",  "type": "String"},
                    "532.0": {"name": "TESTVAR_ChArray", "type": "Char[10]"}
                }
            }
        }),
        'order': '6',
        'displayName': 'Register Map'
    }
}


_LOGGER = logger.setup(__name__, level=logging.INFO)
""" Setup the access to the logging system of Fledge """

UNIT = 0x0
"""  The slave unit this request is targeting """

client = None


def plugin_info():
    """ Returns information about the plugin.

    Args:
    Returns:
        dict: plugin information
    Raises:
    """

    return {
        'name': 's7',
        'version': '1.9.1',
        'mode': 'poll',
        'type': 'south',
        'interface': '1.0',
        'config': _DEFAULT_CONFIG
    }


def plugin_init(config):
    """ Initialise the plugin.

    Args:
        config: JSON configuration document for the plugin configuration category
    Returns:
        handle: JSON object to be used in future calls to the plugin
    Raises:
    """
    return copy.deepcopy(config)


def plugin_poll(handle):
    """ Poll readings from the s7 device and returns it in a JSON document as a Python dict.

    Available for poll mode only.

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
        returns a reading in a JSON document, as a Python dict, if it is available
        None - If no reading is available
    Raises:
    """

    try:
        global client
        if client is None:
            try:
                address = handle['host']['value']
                port = int(handle['port']['value'])
                rack = int(handle['rack']['value'])
                slot = int(handle['slot']['value'])
            except Exception as ex:
                e_msg = 'Failed to parse S7 TCP host address and / or port configuration.'
                _LOGGER.error('%s %s', e_msg, str(ex))
                raise ValueError(e_msg)
            try:
                client = snap7.client.Client()
                client_connected = client.connect(host, rack, slot, port)
                if client_connected:
                    _LOGGER.info('S7 TCP Client is connected. %s:%d', host, port)
                else:
                    raise RuntimeError("S7 TCP Connection failed!")
            except:
                client = None
                _LOGGER.warn('Failed to connect! S7 TCP host %s on port %d, rack %d and slot %d ', host, port, rack, slot)
                return

        unit_id = UNIT
        s7_map = json.loads(handle['map']['value'])

        readings = {}

        

        offsets = { "Bool":1,"Int": 2,"Real":4,"Time":4,"DInt":4,"UDInt":4}
        
        
        db = s7_map['DB']
        if len(db) > 0:
            for dbnumber, variable in db.items():
                if len(variable) > 0:
                    for name, item in variable.items():
                        print(int(dbnumber), str(name), int(item['address']), int(str(item['address']).split('.')[1]), offsets.get(str(item['type'])))  
                        #data = ReadDB(client, int(dbnumber), int(item['address']), S7WLReal) 
                        
                        if data is None:
                            #_LOGGER.error
                            print('Failed to read DB: %s name: %s  address: %f', dbnumber, name, float(item['address']))
                        else:
                            readings.update({name: data }) 

        wrapper = {
            'asset': handle['assetName']['value'],
            'timestamp': utils.local_timestamp(),
            'readings': readings
        }

    except Exception as ex:
        _LOGGER.error('Failed to read data from s7 device. Got error %s', str(ex))
        raise ex
    else:
        return wrapper


def plugin_reconfigure(handle, new_config):
    """ Reconfigures the plugin

    it should be called when the configuration of the plugin is changed during the operation of the south service.
    The new configuration category should be passed.

    Args:
        handle: handle returned by the plugin initialisation call
        new_config: JSON object representing the new configuration category for the category
    Returns:
        new_handle: new handle to be used in the future calls
    Raises:
    """

    _LOGGER.info("Old config for S7 TCP plugin {} \n new config {}".format(handle, new_config))

    diff = utils.get_diff(handle, new_config)

    # TODO
    if 'address' in diff or 'port' in diff:
        plugin_shutdown(handle)
        new_handle = plugin_init(new_config)
        _LOGGER.info("Restarting S7 TCP plugin due to change in configuration keys [{}]".format(', '.join(diff)))
    else:
        new_handle = copy.deepcopy(new_config)

    return new_handle


def plugin_shutdown(handle):
    """ Shutdowns the plugin doing required cleanup

    To be called prior to the south service being shut down.

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
    Raises:
    """
    global client
    try:
        if client is not None:
            # TODO
            # client.close()
            _LOGGER.info('S7 TCP client connection closed.')
    except Exception as ex:
        _LOGGER.exception('Error in shutting down S7 TCP plugin; %s', str(ex))
        raise ex
    else:
        client = None
        _LOGGER.info('S7 TCP plugin shut down.')
