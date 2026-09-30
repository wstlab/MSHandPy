# -*- coding: utf-8 -*-
"""清理残留进程：杀死所有运行项目脚本的 Python 进程"""
import subprocess
import os
import sys
import ctypes
import time

KEYWORDS = ['vm_server', 'display_gui', 'start_vm', 'mindplus_usb',
            'virtual_usb', 'vm_websocket_server']
killed = 0

try:
    # 用 PowerShell 获取进程命令行（比 wmic 更新，兼容 Win10/11）
    result = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'vm_server|display_gui|start_vm|mindplus_usb|virtual_usb|vm_websocket_server' } | Select-Object ProcessId, CommandLine | ConvertTo-Json"],
        capture_output=True, timeout=10
    )
    stdout = result.stdout.decode('utf-8', errors='replace') if result.stdout else ""

    import json
    if stdout.strip():
        try:
            procs = json.loads(stdout)
            if not isinstance(procs, list):
                procs = [procs]
        except:
            procs = []

        for p in procs:
            pid = p.get('ProcessId')
            if pid and pid != os.getpid():
                subprocess.run(['taskkill', '/pid', str(pid), '/f'],
                               capture_output=True)
                print(f"  已终止 PID {pid}")
                killed += 1
except Exception as e:
    print(f"  清理过程出错: {e}")

if killed == 0:
    print("  无残留进程")
else:
    print(f"  共清理 {killed} 个残留进程")
    time.sleep(1)
