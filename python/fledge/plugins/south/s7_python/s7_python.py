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
import re

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
        'default': 's7_python',
        'readonly': 'true'
    },
    'assetName': {
        'description': 'Asset name',
        'type': 'string',
        'default': 'S7',
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
                    "0.0":   {"name": "Job",             "type": "String[254]"},
                    "256.0": {"name": "Count",           "type": "UINT"},
                    "258.0": {"name": "Active",          "type": "BOOL"},
                    "258.1": {"name": "TESTVAR_Bits",    "type": "BOOL"},
                    "260.0": {"name": "TESTVAR_Word",    "type": "WORD"},
                    "262.0": {"name": "TESTVAR_Int",     "type": "INT"},
                    "264.0": {"name": "TESTVAR_DWord",   "type": "DWORD"},
                    "268.0": {"name": "TESTVAR_DInt",    "type": "DINT"},
                    "272.0": {"name": "TESTVAR_Real",    "type": "REAL"}#,
                    #"276.0": {"name": "TESTVAR_String",  "type": "STRING"}#,
                    #"532.0": {"name": "TESTVAR_ChArray", "type": "Char[11]"}
                },            
                "789": {
                    "1288.0": {"name": "Max_Usint", "type": "USInt"},
                    "1290.0": {"name": "Max_UInt", "type": "UInt"},
                    "1292.0": {"name": "Max_ULInt", "type": "ULInt"},
                    "1300.0": {"name": "Min_SInt", "type": "SInt"},
                    "1301.0": {"name": "Max_SInt", "type": "SInt"},
                    "1302.0": {"name": "Min_Int", "type": "Int"},
                    "1304.0": {"name": "Max_Int", "type": "Int"},
                    "1306.0": {"name": "Min_DInt", "type": "DInt"},
                    "1310.0": {"name": "Max_DInt", "type": "DInt"},
                    "1314.0": {"name": "Min_LInt", "type": "LInt"},
                    "1322.0": {"name": "Max_LInt", "type": "LInt"},
                    "1330.0": {"name": "Min_Real", "type": "Real"},
                    "1334.0": {"name": "Max_Real", "type": "Real"},
                    "1338.0": {"name": "Min_LReal", "type": "LReal"},
                    "1346.0": {"name": "Max_LReal", "type": "LReal"},
                    "1354.0": {"name": "Min_Date", "type": "Date_And_Time"},
                    "1362.0": {"name": "Max_Date", "type": "Date_And_Time"}
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
        'name': 's7_south_python',
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
                host = handle['host']['value']
                port = int(handle['port']['value'])
                rack = int(handle['rack']['value'])
                slot = int(handle['slot']['value'])
            except Exception as ex:
                e_msg = 'Failed to parse S7 TCP host address and / or port configuration.'
                _LOGGER.error('%s %s', e_msg, str(ex))
                raise ValueError(e_msg)
            try:
                client = snap7.client.Client()
                client.connect('192.168.1.1', 0, 0)

                #client_connected = client.connect(host, rack, slot, port)
                #client.connect(host, rack, slot)
                client_connected = client.get_connected()
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
        
        db = s7_map['DB']

        readings = {}

        if len(db.keys()) > 0:
            for dbnumber, variable in db.items():
                if len(variable.keys()) > 0:
                    a = []
                    for index, item in variable.items():
                        byte_index = int(index.split('.')[0])
                        a.append([byte_index, byte_index + get_type_size(item['type']) - 1])

                    for start, end in union_range(a):
                        size = end - start + 1
                        _LOGGER.warn("DEBUG: dbnumber: %s start: %s, end: %s, size: %s", str(dbnumber), str(start), str(end), str(size))
                        buffer_ = client.read_area(snap7.types.areas.DB, int(dbnumber), start, size)

                        for index, item in variable.items():
                            byte_index = int(index.split('.')[0])
                            if start <= byte_index and byte_index <= end:
                                _LOGGER.warn("DEBUG: start: %s, type: %s", str(float(index) - start), item['type'])
                                data = get_value(buffer_, float(index) - start, item['type'])

                                if data is None:
                                    _LOGGER.error('Failed to read DB: %s index: %s name: %s', str(dbnumber), str(index), str(item['name']))
                                else:
                                    readings.update({"DB" + dbnumber + "_" + item['name']: data })


        _LOGGER.warn('DEBUG OUT='+ str(readings))

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
    if 'host' in diff or 'port' in diff:
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


def union_range(a):
    b = []
    for begin, end in sorted(a):
        if b and b[-1][1] >= begin - 1:
            b[-1][1] = max(b[-1][1], end)
        else:
            b.append([begin, end])

    return b


def get_lreal(bytearray_: bytearray, byte_index: int) -> float:
    """Get real value.
    Notes:
        Datatype `LReal` is represented in 8 bytes in the PLC..
        Maximum possible value is 2.2250738585072014E-308.
        Lower posible value is -1.7976931348623157E+308
    Args:
        bytearray_: buffer to read from.
        byte_index: byte index to reading from.
    Returns:
        Real value.
    """
    data = bytearray_[byte_index:byte_index + 8]
    value = struct.unpack('>d', struct.pack('8B', *data))[0]
    return value


def get_lword(bytearray_: bytearray, byte_index: int) -> int:
    """ Gets the lword from the buffer.
    Notes:
        Datatype `lword` consists in 8 bytes in the PLC.
        The maximum value posible is ``
    Args:
        bytearray_: buffer to read.
        byte_index: byte index from where to start reading.
    Returns:
        Value read.
    
    """
    data = bytearray_[byte_index:byte_index + 4]
    value = struct.unpack('>Q', struct.pack('8B', *data))[0]
    return value


def get_uint(bytearray_: bytearray, byte_index: int) -> int:
    """Get uint value from bytearray.
    Notes:
        Datatype `uint` in the PLC is represented in two bytes
    Args:
        bytearray_: buffer to read from.
        byte_index: byte index to start reading from.
    Returns:
        Int value.
    """
    data = bytearray_[byte_index:byte_index + 2]
    data[1] = data[1] & 0xff
    data[0] = data[0] & 0xff
    packed = struct.pack('2B', *data)
    value = struct.unpack('>H', packed)[0]
    return value


def get_udint(bytearray_: bytearray, byte_index: int) -> int:
    """Get udint value from bytearray.
    Notes:
        Datatype `udint` consists in 4 bytes in the PLC.
        Maximum possible value is 4294967295.
        Lower posible value is 0.
    Args:
        bytearray_: buffer to read.
        byte_index: byte index from where to start reading.
    Returns:
        Int value
    Examples:

    """
    data = bytearray_[byte_index:byte_index + 4]
    value = struct.unpack('>L', struct.pack('4B', *data))[0]
    return value


def get_ulint(bytearray_: bytearray, byte_index: int) -> int:
    """Get udint value from bytearray.
    Notes:
        Datatype `ulint` consists in 8 bytes in the PLC.
        Maximum possible value is ????.
        Lower posible value is 0.
    Args:
        bytearray_: buffer to read.
        byte_index: byte index from where to start reading.
    Returns:
        Value read.
    Examples:

    """
    data = bytearray_[byte_index:byte_index + 8]
    value = struct.unpack('>Q', struct.pack('8B', *data))[0]
    return value


def get_lint(bytearray_: bytearray, byte_index: int) -> int:
    """Get lint value from bytearray.
    Notes:
        Datatype `LInt` consists in 8 bytes in the PLC.
        Maximum possible value is ????.
        Lower posible value is -????.
    Args:
        bytearray_: buffer to read.
        byte_index: byte index from where to start reading.
    Returns:
        Int value.
    """
    data = bytearray_[byte_index:byte_index + 8]
    value = struct.unpack('>q', struct.pack('8B', *data))[0]
    return value


def get_value(bytearray_, byte_index, type_):
    """ Gets the value for a specific type.
    Args:
        byte_index: byte index from where start reading.
        type_: type of data to read.
    Raises:
        :obj:`ValueError`: if the `type_` is not handled.
    Returns:
        Value read according to the `type_`
    """

    type_ = type_.strip().upper()

    if type_ == 'BOOL':
        byte_index, bool_index = str(byte_index).split('.')
        return get_bool(bytearray_, int(float(byte_index)), int(bool_index))


    byte_index = int(float(byte_index))

    if type_.startswith('STRING'):
        max_size = re.search(r'\d+', type_)
        #(\d+\.\.)?(\d+)    0..9
        #if max_size is None:

           #raise Snap7Exception("Max size could not be determinate. re.search() returned None")
        max_size_grouped = max_size.group(0)
        max_size_int = int(max_size_grouped)
        return get_string(bytearray_, byte_index, max_size_int)

    elif type_ == 'REAL':
        return get_real(bytearray_, byte_index)
    
    elif type_ == 'LREAL':
        return get_lreal(bytearray_, byte_index)
    
    elif type_ == 'WORD':
        return get_word(bytearray_, byte_index)

    elif type_ == 'DWORD':
        return get_dword(bytearray_, byte_index)
    
    elif type_ == 'LWORD':
        return get_lword(bytearray_, byte_index)

    elif type_ == 'SINT':
        return get_sint(bytearray_, byte_index)

    elif type_ == 'INT':
        return get_int(bytearray_, byte_index)
    
    elif type_ == 'DINT':
        return get_dint(bytearray_, byte_index)
    
    elif type_ == 'LINT':
        return get_lint(bytearray_, byte_index)
    
    elif type_ == 'USINT':
        return get_usint(bytearray_, byte_index)
    
    elif type_ == 'UINT':
        return get_uint(bytearray_, byte_index)

    elif type_ == 'UDINT':
        return get_udint(bytearray_, byte_index)

    elif type_ == 'ULINT':
        return get_ulint(bytearray_, byte_index)

    elif type_ == 'BYTE':
        return get_byte(bytearray_, byte_index)

    elif type_ == 'CHAR':
        return chr(get_usint(bytearray_, byte_index))

    elif type_ == 'S5TIME':
        data_s5time = get_s5time(bytearray_, byte_index)
        return data_s5time

    elif type_ == 'DATE_AND_TIME':
        data_dt = get_dt(bytearray_, byte_index)
        return data_dt

    # add these three not implemented data typ to avoid error
    elif type_ == 'TIME':
        _LOGGER.warn('read TIME not implemented')
        return None

    elif type_ == 'DATE':
        _LOGGER.warn('DATE not implemented')
        return None

    elif type_ == 'TIME_OF_DAY':
        _LOGGER.warn('TIME_OF_DAY not implemented')
        return None
    
    _LOGGER.warn(' Unknown Data Type %s not implemented', str(type_))
    return None


def get_type_size(type_name):

    type_name = type_name.strip().upper()

    type_size = { "BOOL": 1, "BYTE": 1, "CHAR": 1, "WORD": 2, "DWORD": 4, "USINT": 1,  "UINT": 2, "UDINT": 4, "ULINT": 8, "SINT": 1, "INT": 2, "DINT":4, "LINT":8,  "REAL":4, "LREAL":8, "STRING": 256, "DATE_AND_TIME": 8}

    if type_name in type_size.keys():
        return type_size[type_name]

    type_split = type_name.split('[')
    if  len (type_split) == 2 and "]" == type_name[-1]:
        array_size = int(type_split[1][:-1]) # +1 because array start with 0

        if type_split[0] == 'STRING':
            return array_size + 2

        if type_split[0] in type_size.keys():
            return type_size[type_split[0]] * array_size

    if  type_split[0] == 'STRING' and len (type_split) == 3 and "]" == type_name[-1]:
        string_size = int(type_split[1][:-1]) + 2 # +1 because array start with 0
        array_size = int(type_split[2][:-1]) # +1 because array start with 0
        return array_size * string_size

    if type_split[0] == 'STRING':
        return array_size

    raise ValueError

