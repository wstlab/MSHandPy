_flash_data = {}

def flash_read(address, buffer):
    for i in range(len(buffer)):
        buffer[i] = _flash_data.get(address + i, 0)

def flash_write(address, buffer):
    for i in range(len(buffer)):
        _flash_data[address + i] = buffer[i]

def flash_erase(address, size):
    for i in range(size):
        if address + i in _flash_data:
            del _flash_data[address + i]