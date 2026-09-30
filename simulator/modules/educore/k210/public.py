def CheckCode(tmp):
    sum = 0
    for i in range(len(tmp)):
        sum += tmp[i]
    return sum & 0xff

def AI_Uart_CMD(uart, data_type, cmd, cmd_type, cmd_data=[0, 0, 0, 0, 0, 0, 0, 0]):
    check_sum = 0
    CMD = [0xAA, data_type, cmd, cmd_type]
    CMD.extend(cmd_data)
    for i in range(8-len(cmd_data)):
        CMD.append(0)
    for i in range(len(CMD)):
        check_sum = check_sum+CMD[i]
    CMD.append(check_sum & 0xFF)
    uart.write(bytes(CMD))

def AI_Uart_CMD_String(uart=None, cmd=0xfe, cmd_type=0xfe, cmd_data=[0, 0, 0], str_len=0, str_buf=''):
    check_sum = 0
    CMD = [0xAA, 0x02, cmd, cmd_type]
    CMD.extend(cmd_data)
    for i in range(3-len(cmd_data)):
        CMD.append(0)
    for i in range(len(CMD)):
        check_sum = check_sum + CMD[i]
    str_temp = bytes(str_buf, 'utf-8')
    str_len = len(str_temp)
    for i in range(len(str_temp)):
        check_sum = check_sum + str_temp[i]
    CMD = bytes(CMD) + bytes([str_len]) + str_temp + bytes([check_sum & 0xFF])
    uart.write(CMD)