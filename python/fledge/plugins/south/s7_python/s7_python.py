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
import math
import struct

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
__copyright__ = "Copyright (c) 2021 Austrian Center for Digital Production (ACDP)"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


""" _DEFAULT_CONFIG with S7 Entities Map

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
                    "0.0":   {"name": "Job",               "type": "String[254]"},
                    "256.0": {"name": "Count",             "type": "UINT"},
                    "258.0": {"name": "Active",            "type": "BOOL"},
                    "258.1": {"name": "TESTVAR_Bits",      "type": "BOOL"},
                    "260.0": {"name": "TESTVAR_Word",      "type": "WORD"},
                    "262.0": {"name": "TESTVAR_Int",       "type": "INT"},
                    "264.0": {"name": "TESTVAR_DWord",     "type": "DWORD"},
                    "268.0": {"name": "TESTVAR_DInt",      "type": "DINT"},
                    "272.0": {"name": "TESTVAR_Real",      "type": "REAL"},
                    "276.0": {"name": "TESTVAR_String",    "type": "STRING"},
                    "532.0": {"name": "TESTVAR_ChArray",   "type": "Char[11]"},
                    "544.0": {"name": "TESTVAR_Char",      "type": "Char"},
                    "546.0": {"name": "StaticVar",         "type": "Int"},
                    "548.0": {"name": "TESTVAR_Time_Min",  "type": "Time"},
                    "552.0": {"name": "TESTVAR_Time_Max",  "type": "Time"},
                    "556.0": {"name": "TESTVAR_LTime_Min", "type": "LTime"},
                    "564.0": {"name": "TESTVAR_LTime_Max", "type": "LTime"}

                },
                "789": {
                    "1288.0": {"name": "Max_Usint",   "type": "USInt"},
                    "1290.0": {"name": "Max_UInt",    "type": "UInt"},
                    "1292.0": {"name": "Max_ULInt",   "type": "ULInt"},
                    "1300.0": {"name": "Min_SInt",    "type": "SInt"},
                    "1301.0": {"name": "Max_SInt",    "type": "SInt"},
                    "1302.0": {"name": "Min_Int",     "type": "Int"},
                    "1304.0": {"name": "Max_Int",     "type": "Int"},
                    "1306.0": {"name": "Min_DInt",    "type": "DInt"},
                    "1310.0": {"name": "Max_DInt",    "type": "DInt"},
                    "1314.0": {"name": "Min_LInt",    "type": "LInt"},
                    "1322.0": {"name": "Max_LInt",    "type": "LInt"},
                    "1330.0": {"name": "Min_Real",    "type": "Real"},
                    "1334.0": {"name": "Max_Real",    "type": "Real"},
                    "1338.0": {"name": "Min_LReal",   "type": "LReal"},
                    "1346.0": {"name": "Max_LReal",   "type": "LReal"},
                    "1354.0": {"name": "Min_Date",    "type": "Date_And_Time"},
                    "1362.0": {"name": "Max_Date",    "type": "Date_And_Time"},
                    "1370.0": {"name": "Test_Byte",   "type": "Byte"},
                    "1371.3": {"name": "Test_Bool_4", "type": "Bool"},
                    "12.0":   {"name": "ArrayOfInt",  "type": "Int[0..9]"}
                },
                "11": {
                    "0.0": {
                        "name": "MyUDTs",
                        "type": "Struct[0..20]",
                        "defintion": {
                            "0.0":   {"name": "Produktionsauftrag", "type": "String"},
                            "256.0": {"name": "ProductionId",       "type": "DWord"},
                            "260.0": {"name": "TargetLengthFront",  "type": "Real"},
                            "264.0": {"name": "TargetLengthBack",   "type": "Real"},
                            "268.0": {"name": "ActualLengthFront",  "type": "Real"},
                            "272.0": {"name": "ActualLengthBack",   "type": "Real"},
                            "276.0": {"name": "CycleTime",          "type": "Time"},
                            "280.0": {"name": "Timestamp",          "type": "Date_And_Time"}
                        },
                        "offset": 0
                    }
                }
            }
        }),
        'order': '6',
        'displayName': 'Register Map'
    },
    "saveAs": {
        "description": "The way arrays and objects are stored",
        "type": "enumeration",
        'options': ['flat', 'escaped', 'object'],
        "default": 'flat',
        'order': '7',
        'displayName': 'Store Readings'
    }
}


_LOGGER = logger.setup(__name__, level=logging.DEBUG)
#_LOGGER = logger.setup(__name__, level=logging.WARN)
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
                client.connect(host, rack, slot, port)
                client_connected = client.get_connected()

                if client_connected:
                    _LOGGER.info(
                        'S7 TCP Client is connected. %s:%d', host, port)
                else:
                    raise RuntimeError("S7 TCP Connection failed!")
            except:
                client = None
                _LOGGER.warn(
                    'Failed to connect! S7 TCP host %s on port %d, rack %d and slot %d ', host, port, rack, slot)
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
                        a.append([byte_index, byte_index
                                 + get_type_size(item) - 1])

                    _LOGGER.debug("union_range(a): %s", str(union_range(a)))

                    for start, end in union_range(a):
                        size = end - start + 1
                        _LOGGER.debug("DEBUG: dbnumber: %s start: %s, end: %s, size: %s", str(
                            dbnumber), str(start), str(end), str(size))
                        try:
                            buffer_ = client.read_area(
                                snap7.types.Areas.DB, int(dbnumber), start, size)

                            for index, item in variable.items():
                                byte_index, bool_index = get_byte_and_bool_index(
                                    index)

                                if start <= byte_index and byte_index <= end:
                                    _LOGGER.debug("DEBUG: byte_index - start: %d, byte_index: %d, start: %d, bool_index: %d, type: %s",
                                                  byte_index - start, byte_index, start, bool_index, item['type'])
                                    data = get_value(
                                        buffer_, byte_index - start, item, bool_index)

                                    if data is None:
                                        _LOGGER.error('Failed to read DB: %s index: %s name: %s', str(
                                            dbnumber), str(index), str(item['name']))
                                    else:
                                        if handle["saveAs"]["value"] == "flat":
                                            for element in list(walk(data, "DB" + dbnumber + "_" + item['name'])):
                                                readings.update(element)

                                        elif handle["saveAs"]["value"] == "escaped":

                                            #_LOGGER.warn('No support for escaped JSON currently')

                                            # _LOGGER.debug(
                                            #     'json.dumps(data)=' + json.dumps(data))
                                            # _LOGGER.debug(
                                            #     'json.dumps(json.dumps(data))=' + json.dumps(json.dumps(data)))
                                            # readings.update({"DB" + dbnumber + "_" + item['name']:
                                            #                  "[{\\\"Produktionsauftrag\\\": \\\"P12346789\\\", \\\"ProductionId\\\": 6636321}]"})
                                            readings.update(
                                                {"DB" + dbnumber + "_" + item['name']: escape_json(json.dumps(data))})
                                        else:
                                            readings.update(
                                                {"DB" + dbnumber + "_" + item['name']:  data})

                        except Exception as ex:
                            _LOGGER.error('Failed to read area from s7 device: dbnumber: %s start: %s, end: %s, size: %s Got error %s', str(
                                dbnumber), str(start), str(end), str(size), str(ex))
                            raise ex

        _LOGGER.debug('DEBUG OUT=' + str(readings))

        wrapper = {
            'asset': handle['assetName']['value'],
            'timestamp': utils.local_timestamp(),
            'readings': readings
        }

    except Exception as ex:
        _LOGGER.error(
            'Failed to read data from s7 device. Got error %s', str(ex))
        client.disconnect()
        client = None
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

    _LOGGER.info("Old config for S7 TCP plugin {} \n new config {}".format(
        handle, new_config))

    diff = utils.get_diff(handle, new_config)

    # TODO
    if 'host' in diff or 'rack' in diff or 'slot' in diff or 'port' in diff:
        plugin_shutdown(handle)
        new_handle = plugin_init(new_config)
        _LOGGER.info("Restarting S7 TCP plugin due to change in configuration keys [{}]".format(
            ', '.join(diff)))
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
            client.disconnect()
            # client = None
            _LOGGER.info('S7 TCP client connection closed.')
    except Exception as ex:
        _LOGGER.exception('Error in shutting down S7 TCP plugin; %s', str(ex))
        raise ex
    else:
        # client.disconnect()
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


# TODO: check return format: hex or dec
# TODO: in the future the function will be implemented in the snap7.util package
def get_byte_(bytearray_: bytearray, byte_index: int) -> int:
    """Get byte value from bytearray.
    Notes:
        WORD 8bit 1bytes Decimal number unsigned B#(0) to B#(255) => 0 to 255
    Args:
        bytearray_: buffer to be read from.
        byte_index: byte index to be read.
    Returns:
        value get from the byte index.
    """
    data = bytearray_[byte_index:byte_index + 1]
    data[0] = data[0] & 0xff
    packed = struct.pack('B', *data)
    value = struct.unpack('B', packed)[0]
    return value


def get_char_(bytearray_: bytearray, byte_index: int):
    """Get char value from bytearray.

    Args:
        bytearray_: buffer to be read from.
        byte_index: byte index to be read.
    Returns:
        value get from the byte index.
    """
    data = bytearray_[byte_index:byte_index + 1]
    data[0] = data[0] & 0xff
    packed = struct.pack('B', *data)
    value = struct.unpack('s', packed)[0]
    return value


def get_value(bytearray_, byte_index, item, bool_index):

    type_name = item['type'].strip().lower()

    type_size = {"bool": 1, "byte": 1, "char": 1, "word": 2, "dword": 4, "usint": 1,  "uint": 2, "udint": 4,
                 "ulint": 8, "sint": 1, "int": 2, "dint": 4, "lint": 8,  "real": 4, "lreal": 8, "string": 256, "time": 4, "ltime": 8, "date_and_time": 8}

    if type_name in type_size.keys():
        return get_value_(bytearray_, byte_index, type_name, bool_index)

    if type_name == 'struct':
        if 'defintion' in item.keys():
            # return json.dumps(get_struct_values(bytearray_, byte_index, item['defintion']))
            return get_struct_values(bytearray_, byte_index, item['defintion'])
        else:
            _LOGGER.warn('Struct data type needs a dict key "defintion"')
            raise ValueError

    if 'offset' in item.keys():
        offset = int(item['offset'])
    else:
        offset = 0

    type_split = type_name.split('[')
    if len(type_split) == 2 and "]" == type_name[-1]:
        array_size = get_array_size(type_split[1][:-1])

        if type_split[0] == 'string':
            # add 2 for S7 String Type
            string_size = array_size + 2
            _LOGGER.debug("get_value: string_size: %d", string_size)
            return get_value_(bytearray_, byte_index, 'string', string_size)

        if type_split[0] == 'bool':
            a = []

            for n in range(0, array_size, 1):
                bool_byte_index, bool_index = divmod(n, 8)
                _LOGGER.debug("Bool byte_index: %d, bool_index: %d",
                              byte_index + bool_byte_index, bool_index)
                a.append(get_value_(bytearray_, byte_index
                         + bool_byte_index, type_split[0], bool_index))

            return a

        if type_split[0] == 'struct':
            if 'defintion' in item.keys():
                struct_size = get_struct_size(item['defintion'])

                a = []
                for n in range(byte_index, byte_index + (struct_size + offset) * array_size, struct_size + offset):
                    print(n)
                    a.append(get_struct_values(
                        bytearray_, n, item['defintion']))

                return a
                # return json.dumps(a)

            else:
                raise ValueError

        if type_split[0] in type_size.keys():
            a = []

            _LOGGER.debug("Read Array: byte_index: %s", str(byte_index))
            _LOGGER.debug("Read Array: type_size[type_split[0]: %s", str(
                type_size[type_split[0]]))
            _LOGGER.debug("Read Array: array_size: %s", str(array_size))
            _LOGGER.debug("Read Array: Range: START: %s, STOP: %s, STEP: %s", str(byte_index), str(
                byte_index + (type_size[type_split[0]] + offset) * array_size + 1), str(type_size[type_split[0]] + offset))
            _LOGGER.debug("RANGE: %s", str(range(byte_index, byte_index + (
                type_size[type_split[0]] + offset) * array_size, type_size[type_split[0]] + offset)))

            for n in range(byte_index, byte_index + (type_size[type_split[0]] + offset) * array_size, type_size[type_split[0]] + offset):
                _LOGGER.debug("Read Array: n: %s", str(n))
                a.append(get_value_(bytearray_, n, type_split[0]))

            return a
            # return json.dumps(a)

    if type_split[0] == 'string' and len(type_split) == 3 and "]" == type_name[-1]:

        string_size = get_array_size(type_split[1][:-1]) + 2
        _LOGGER.debug(
            "get_value: Array of String: string_size: %d", string_size)
        array_size = get_array_size(type_split[2][:-1])
        _LOGGER.debug(
            "get_value: Array of String: array_size: %d", array_size)

        _LOGGER.debug("Read String Array: byte_index: %s", str(byte_index))
        _LOGGER.debug("Read String Array: type_size[type_split[0]: %s", str(
            type_size[type_split[0]]))
        _LOGGER.debug("Read String Array: array_size: %s", str(array_size))
        _LOGGER.debug("Read String Array: string_size: %s", str(string_size))
        _LOGGER.debug("Read String Array: Range: START: %s, STOP: %s, STEP: %s", str(
            byte_index), str((string_size + offset) * array_size), str(string_size + offset))
        _LOGGER.debug("RANGE: %s", str(range(byte_index, byte_index
                      + (string_size + offset) * array_size, string_size + offset)))

        a = []
        for n in range(byte_index, byte_index + (string_size + offset) * array_size, string_size + offset):
            _LOGGER.debug("Read String Array: n: %s", str(n))
            a.append(get_value_(bytearray_, n, 'string', string_size - 2))
        return a
        # return json.dumps(a)

    raise ValueError


def get_value_(bytearray_, byte_index, type_, bool_index=None, max_size=254):
    """ Gets the value for a specific type.
    Args:
        byte_index: byte index from where start reading.
        type_: type of data to read.
    Raises:
        :obj:`ValueError`: if the `type_` is not handled.
    Returns:
        Value read according to the `type_`
    """

    type_ = type_.strip().lower()

    _LOGGER.debug("get_value_: byte_index: type_: bool_index: , max_size: )", str(
        byte_index), str(type_), str(bool_index), str(max_size))

    if type_ == 'bool':
        if bool_index == None:
            _LOGGER.warn('type is bool, but bool_index is not set')
            return None
        else:
            return get_bool(bytearray_, byte_index, bool_index)

    elif type_ == 'string':
        return get_string(bytearray_, byte_index, max_size)

    elif type_ == 'real':
        return get_real(bytearray_, byte_index)

    elif type_ == 'lreal':
        return get_lreal(bytearray_, byte_index)

    elif type_ == 'word':
        return get_word(bytearray_, byte_index)

    elif type_ == 'dword':
        return get_dword(bytearray_, byte_index)

    elif type_ == 'lword':
        return get_lword(bytearray_, byte_index)

    elif type_ == 'sint':
        return get_sint(bytearray_, byte_index)

    elif type_ == 'int':
        return get_int(bytearray_, byte_index)

    elif type_ == 'dint':
        return get_dint(bytearray_, byte_index)

    elif type_ == 'lint':
        return get_lint(bytearray_, byte_index)

    elif type_ == 'usint':
        return get_usint(bytearray_, byte_index)

    elif type_ == 'uint':
        return get_uint(bytearray_, byte_index)

    elif type_ == 'udint':
        return get_udint(bytearray_, byte_index)

    elif type_ == 'ulint':
        return get_ulint(bytearray_, byte_index)

    elif type_ == 'byte':
        return get_byte_(bytearray_, byte_index)

    elif type_ == 'char':
        #return chr(get_char_(bytearray_, byte_index))
        return get_char_(bytearray_, byte_index)

    elif type_ == 'time':
        return get_dint(bytearray_, byte_index)

    elif type_ == 'ltime':
        return get_lint(bytearray_, byte_index)

    elif type_ == 's5time':
        data_s5time = get_s5time(bytearray_, byte_index)
        return data_s5time

    elif type_ == 'date_and_time':
        data_dt = get_dt(bytearray_, byte_index)
        return data_dt

    # add these two not implemented data typ to avoid error
    elif type_ == 'date':
        _LOGGER.warn('DATE not implemented')
        return None

    elif type_ == 'time_of_day':
        _LOGGER.warn('TIME_OF_DAY not implemented')
        return None

    _LOGGER.warn('Unknown Data Type %s not implemented', str(type_))
    return None


def get_array_size(dimension):
    # [0..7] -> 0, 1, 2, ..., 6, 7 -> array_size = 7 - 0 + 1 = 8
    if m := re.match(r'(\d+)\.\.(\d+)', dimension):
        return int(m.group(2)) - int(m.group(1)) + 1

    # [8] -> 0, 1, 2, ..., 6, 7 -> array_size = 8
    if m := re.match(r'(\d+)', dimension):
        return int(m.group(1))

    _LOGGER.warn('unsupoortes array dimension or definition, %s',
                 str(dimension))
    raise ValueError


def get_struct_size(defintion):
    s = sorted(defintion, key=lambda t: convert_key(t[0]))

    if (convert_key(min(s)) != 0):
        _LOGGER.warn(
            'Struct data type does not contain dict key "0.0",  %s', str(defintion))
        raise ValueError

    try:
        return convert_key(max(s)) + get_type_size_(defintion[max(s)]["type"])
    except:
        raise ValueError


def convert_key(key):
    try:
        return int(float(key))
    except ValueError:
        return key


def get_type_size_(type_name):
    type_size = {"bool": 1, "byte": 1, "char": 1, "word": 2, "dword": 4, "usint": 1,  "uint": 2, "udint": 4,
                 "ulint": 8, "sint": 1, "int": 2, "dint": 4, "lint": 8,  "real": 4, "lreal": 8, "string": 256, "time": 4, "ltime": 8, "date_and_time": 8}

    type_name = type_name.strip().lower()

    if type_name in type_size.keys():
        return type_size[type_name]

    _LOGGER.warn('Unkown type %s', str(type_name))
    raise ValueError


def get_type_size(item):
    type_size = {"bool": 1, "byte": 1, "char": 1, "word": 2, "dword": 4, "usint": 1,  "uint": 2, "udint": 4,
                 "ulint": 8, "sint": 1, "int": 2, "dint": 4, "lint": 8,  "real": 4, "lreal": 8, "string": 256, "time": 4, "ltime": 8, "date_and_time": 8}

    type_name = item['type'].strip().lower()

    if type_name in type_size.keys():
        return type_size[type_name]

    if type_name == 'struct':
        if 'defintion' in item.keys():
            return get_struct_size(item['defintion'])
        else:
            _LOGGER.warn('Struct data type needs a dict key "defintion"')
            raise ValueError

    if 'offset' in item.keys():
        offset = int(item['offset'])
    else:
        offset = 0

    type_split = type_name.split('[')
    if len(type_split) == 2 and "]" == type_name[-1]:
        array_size = get_array_size(type_split[1][:-1])

        if type_split[0] == 'string':
            # add 2 for S7 String Type
            string_size = array_size + 2
            _LOGGER.debug(
                "get_type_size: string: string_size: %d", string_size)
            return string_size

        if type_split[0] == 'struct':
            if 'defintion' in item.keys():
                return (get_struct_size(item['defintion']) + offset) * array_size
            else:
                raise ValueError

        if type_split[0] == 'bool':
            return math.ceil(array_size/8)

        if type_split[0] in type_size.keys():
            return (type_size[type_split[0]] + offset) * array_size

    if type_split[0] == 'string' and len(type_split) == 3 and "]" == type_name[-1]:
        # add 2 for S7 String Type
        string_size = get_array_size(type_split[1][:-1]) + 2
        _LOGGER.debug(
            "get_type_size: Array of string: string_size: %d", string_size)
        array_size = get_array_size(type_split[2][:-1])
        _LOGGER.debug(
            "get_type_size: Array of string: array_size: %d", array_size)
        return array_size * string_size

    _LOGGER.warn(
        'data type is not supported or does not exist,  %s', str(type_name))
    raise ValueError


def get_byte_and_bool_index(index):
    index = str(index)
    index_split = index.split('.')
    byte_index = int(index_split[0])
    bool_index = 0
    if len(index_split) == 2:
        bool_index = int(index_split[1])

    return byte_index, bool_index


def get_struct_values(bytearray_, byte_index, defintion):
    o = {}

    for index, item in defintion.items():
        struct_byte_index, bool_index = get_byte_and_bool_index(index)

        _LOGGER.debug("Read Struct: byte_index: %s", str(byte_index))
        _LOGGER.debug("Read Struct: struct_byte_index: %s",
                      str(struct_byte_index))
        _LOGGER.debug("Read Struct: item: %s", str(item))

        type_name = item['type'].strip().lower()
        type_split = type_name.split('[')

        type_size = {"bool": 1, "byte": 1, "char": 1, "word": 2, "dword": 4, "usint": 1,  "uint": 2, "udint": 4,
                     "ulint": 8, "sint": 1, "int": 2, "dint": 4, "lint": 8,  "real": 4, "lreal": 8, "string": 256, "time": 4, "ltime": 8, "date_and_time": 8}

        if type_name in type_size.keys():
            o[item['name']] = get_value_(
                bytearray_, byte_index + struct_byte_index, type_name, bool_index)

        elif len(type_split) == 2 and "]" == type_name[-1]:
            array_size = get_array_size(type_split[1][:-1])

            if type_split[0] == 'string':
                o[item['name']] = get_value_(
                    bytearray_, byte_index + struct_byte_index, type_name, bool_index, array_size)

            elif type_split[0] == 'bool':
                a = []

                for n in range(0, array_size, 1):
                    bool_byte_index, bool_index = divmod(n, 8)
                    _LOGGER.debug("Bool byte_index: %d, bool_index: %d",
                                  byte_index + bool_byte_index, bool_index)
                    a.append(get_value_(bytearray_, byte_index
                             + bool_byte_index, 'bool', bool_index))

                o[item['name']] = a

            elif type_split[0] in type_size.keys():
                a = []
                for n in range(byte_index + struct_byte_index, byte_index + struct_byte_index + (type_size[type_split[0]]) * array_size, type_size[type_split[0]]):
                    print(n)
                    a.append(get_value_(bytearray_, n, type_split[0]))

                o[item['name']] = a

            else:
                pass
        else:
            pass

    return o


def bool_(value):
    if value in (True, "True", "true", 1, "1"):
        return True
    if value in (False, "False", "false", 0, "0"):
        return False
    else:
        bool(value)


def walk(indict, pre=None, separator='_'):
    pre = pre if pre else ""
    if isinstance(indict, dict):
        for key, value in indict.items():
            if isinstance(value, dict):
                for d in walk(value,  pre + key):
                    yield d
            elif isinstance(value, list) or isinstance(value, tuple):
                for k, v in enumerate(value):
                    for d in walk(v, pre + separator + str(key) + separator + str(k)):
                        yield d
            else:
                yield {pre + separator + str(key): value}
    elif isinstance(indict, list) or isinstance(indict, tuple):
        for k, v in enumerate(indict):
            for d in walk(v, pre + separator + str(k)):
                yield d
    else:
        yield {pre: indict}


def escape_json(s):
    o = []
    for c in s:
        if c == '"':
            o += ["\\\""]
        elif c == '\\':
            o += ["\\\\"]
        elif c == '\b':
            o += ["\\b"]
        elif c == '\f':
            o += ["\f"]
        elif c == '\n':
            o += ["\\n"]
        elif c == '\r':
            o += ["\\r"]
        elif c == '\t':
            o += ["\\t"]
        # FIXME: add control char
        else:
            o += [c]
    return "".join(o)
