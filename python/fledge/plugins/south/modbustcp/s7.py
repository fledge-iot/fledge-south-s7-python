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

""" Plugin for reading data from a Modbus TCP data source

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
        client.close()

"""

__author__ = "Sebastian Kropatschek"
__copyright__ = "Copyright (c) 2018 ACDP"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


""" _DEFAULT_CONFIG with Modbus Entities Map

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
    'address': {
        'description': 'IP address of the PLC',
        'type': 'string',
        'default': '127.0.0.1',
        'order': '3',
        'displayName': 'TCP Address'
    },
    'rack': {
        'description': 'Rack number where the PLC is located',
        'type': 'integer',
        'default': '0',
        'order': '4',
        'displayName': 'Rack'
    },
    'slot': {
        'description': 'Slot number where the CPU is located.',
        'type': 'integer',
        'default': '0',
        'order': '5',
        'displayName': 'Slot'
    },
    'port': {
        'description': 'Port of the PLC',
        'type': 'integer',
        'default': '102',
        'order': '6',
        'displayName': 'Port'
    },
    'map': {
        'description': 'Modbus register map',
        'type': 'JSON',
        'default': json.dumps({
            "job": {
                "type": "String",
                "address": 0
            }
        }),
        'order': '7',
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
        'version': '1.9.0',
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
    """ Poll readings from the modbus device and returns it in a JSON document as a Python dict.

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
                address = handle['address']['value']
                port = int(handle['port']['value'])
                rack = int(handle['rack']['value'])
                slot = int(handle['slot']['value'])
            except Exception as ex:
                e_msg = 'Failed to parse Modbus TCP address and / or port configuration.'
                _LOGGER.error('%s %s', e_msg, str(ex))
                raise ValueError(e_msg)
            try:
                client = ModbusTcpClient(host=address, port=port)
                client_connected = client.connect()
                if client_connected:
                    _LOGGER.info('Modbus TCP Client is connected. %s:%d', address, port)
                else:
                    raise RuntimeError("Modbus TCP Connection failed!")
            except:
                client = None
                _LOGGER.warn('Failed to connect! Modbus TCP host %s on port %d', address, port)
                return

        """ 
        read_coils(self, address, count=1, **kwargs)  
        read_discrete_inputs(self, address, count=1, **kwargs)
        read_holding_registers(self, address, count=1, **kwargs)
        read_input_registers(self, address, count=1, **kwargs)
        
            - address: The starting address to read from
            - count: The number of coils / discrete or registers to read
            - unit: The slave unit this request is targeting
            
            On TCP/IP, the MODBUS server is addressed using its IP address; therefore, the MODBUS Unit Identifier is useless. 

            Remark : The value 0 is also accepted to communicate directly to a MODBUS TCP device.
        """
        unit_id = UNIT
        modbus_map = json.loads(handle['map']['value'])

        readings = {}

        # Read coils
        coils_address_info = modbus_map['coils']
        if len(coils_address_info) > 0:
            for k, address in coils_address_info.items():
                coil_bit_values = client.read_coils(int(address), 1, unit=unit_id)
                if coil_bit_values is None:
                    _LOGGER.error('Failed to read coil %d', address)
                else:
                    readings.update({k: coil_bit_values.bits[0]})

        # Discrete input
        discrete_input_info = modbus_map['inputs']
        if len(discrete_input_info) > 0:
            for k, address in discrete_input_info.items():
                read_discrete_inputs = client.read_discrete_inputs(int(address), 1, unit=unit_id)
                if read_discrete_inputs is None:
                    _LOGGER.error('Failed to read input %d', address)
                else:
                    readings.update({k:  read_discrete_inputs.bits[0]})

        # Holding registers
        holding_registers_info = modbus_map['registers']
        if len(holding_registers_info) > 0:
            for k, address in holding_registers_info.items():
                register_values = client.read_holding_registers(int(address), 1, unit=unit_id)
                if register_values is None:
                    _LOGGER.error('Failed to read holding register %d', address)
                else:
                    readings.update({k: register_values.registers[0]})

        # Read input registers
        input_registers_info = modbus_map['inputRegisters']
        if len(input_registers_info) > 0:
            for k, address in input_registers_info.items():
                read_input_reg = client.read_input_registers(int(address), 1, unit=unit_id)
                if read_input_reg is None:
                    _LOGGER.error('Failed to read input register %d', address)
                else:
                    readings.update({k: read_input_reg.registers[0] })

        wrapper = {
            'asset': handle['assetName']['value'],
            'timestamp': utils.local_timestamp(),
            'readings': readings
        }

    except Exception as ex:
        _LOGGER.error('Failed to read data from modbus device. Got error %s', str(ex))
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

    _LOGGER.info("Old config for Modbus TCP plugin {} \n new config {}".format(handle, new_config))

    diff = utils.get_diff(handle, new_config)

    if 'address' in diff or 'port' in diff:
        plugin_shutdown(handle)
        new_handle = plugin_init(new_config)
        _LOGGER.info("Restarting Modbus TCP plugin due to change in configuration keys [{}]".format(', '.join(diff)))
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
            client.close()
            _LOGGER.info('Modbus TCP client connection closed.')
    except Exception as ex:
        _LOGGER.exception('Error in shutting down Modbus TCP plugin; %s', str(ex))
        raise ex
    else:
        client = None
        _LOGGER.info('Modbus TCP plugin shut down.')
