""" Unit tests for the S7 plugin """


__author__ = "Sebastian Kropatschek"
__copyright__ = "ACDP"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


import pytest

from python.fledge.plugins.south.s7_python import s7_python as s7

class TestS7:

    def test_plugin_info(self):
       
        plugin_info = s7.plugin_info()
        assert plugin_info == {
            'name': 's7_south_python',
            'version': '2.1.1',
            'mode': 'poll',
            'type': 'south',
            'interface': '1.0',
            'config': s7._DEFAULT_CONFIG
        }
