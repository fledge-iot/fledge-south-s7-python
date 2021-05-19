# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge.readthedocs.io/
# FLEDGE_END

from unittest.mock import patch
import pytest

from python.fledge.plugins.south.modbustcp import modbustcp

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2018 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

config = modbustcp._DEFAULT_CONFIG


def test_plugin_contract():
    # Evaluates if the plugin has all the required methods
    assert callable(getattr(modbustcp, 'plugin_info'))
    assert callable(getattr(modbustcp, 'plugin_init'))
    assert callable(getattr(modbustcp, 'plugin_poll'))
    assert callable(getattr(modbustcp, 'plugin_shutdown'))
    assert callable(getattr(modbustcp, 'plugin_reconfigure'))


def test_plugin_info():
    assert modbustcp.plugin_info() == {
        'name': 'Modbus TCP',
        'version': '1.9.0',
        'mode': 'poll',
        'type': 'south',
        'interface': '1.0',
        'config': config
    }


def test_plugin_init():
    assert modbustcp.plugin_init(config) == config


@pytest.mark.skip(reason="To be implemented")
def test_plugin_poll():
    pass


@pytest.mark.skip(reason="To be implemented")
def test_plugin_reconfigure():
    pass


@pytest.mark.skip(reason="To be implemented")
def test_plugin_shutdown():
    pass
