import os
import sys
import json

_nvs_storage = {}

def _get_data_dir():
    if getattr(sys, '_MEIPASS', None):
        return os.path.join(os.path.expanduser('~'), '.simhandpy')
    return os.path.join(os.path.dirname(__file__), '..')

_NVS_FILE = os.path.join(_get_data_dir(), 'nvs_data.json')

def _load_nvs():
    global _nvs_storage
    try:
        with open(_NVS_FILE, 'r') as f:
            _nvs_storage = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _nvs_storage = {}

def _save_nvs():
    with open(_NVS_FILE, 'w') as f:
        json.dump(_nvs_storage, f)

_load_nvs()

class NVS:
    def __init__(self, namespace):
        self.namespace = namespace
        if namespace not in _nvs_storage:
            _nvs_storage[namespace] = {}

    def set_i32(self, key, value):
        _nvs_storage[self.namespace][key] = {'type': 'i32', 'value': value}
        _save_nvs()

    def get_i32(self, key):
        if key not in _nvs_storage[self.namespace]:
            raise OSError("Key not found")
        return _nvs_storage[self.namespace][key]['value']

    def set_str(self, key, value):
        _nvs_storage[self.namespace][key] = {'type': 'str', 'value': value}
        _save_nvs()

    def get_str(self, key):
        if key not in _nvs_storage[self.namespace]:
            raise OSError("Key not found")
        return _nvs_storage[self.namespace][key]['value']

    def commit(self):
        _save_nvs()