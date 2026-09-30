@echo off
chcp 65001 >nul 2>nul
title Sim-Handpy 虚拟掌控板 - 桌面版
setlocal

REM 项目根目录 = bat 所在目录(无论从哪里启动都能正确定位)
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
cd /d "%ROOT%"

echo.
echo ==================================================
echo       Sim-Handpy 虚拟掌控板 - 桌面版启动器
echo ==================================================
echo.
echo  项目目录: %ROOT%
echo.

REM ---- 0. 检查必要文件 ----
if not exist "%ROOT%\requirements.txt" (
    echo [错误] 在 bat 所在目录未找到 requirements.txt
    echo         路径: %ROOT%
    echo         请确保 bat 与所有项目文件在同一个文件夹内
    echo         不要单独拷贝 bat 文件，需拷贝整个文件夹
    echo.
    pause
    exit /b 1
)
if not exist "%ROOT%\start_vm.py" (
    echo [错误] 在 bat 所在目录未找到 start_vm.py
    echo         路径: %ROOT%
    echo         请确保 bat 与所有项目文件在同一个文件夹内
    echo.
    pause
    exit /b 1
)
echo [检查] 项目文件完整                 OK

REM ---- 0. 检查系统 Python ----
where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未在系统 PATH 中找到 Python
    echo         请安装 Python 3.10+:
    echo         https://www.python.org/downloads/
    echo         安装时务必勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
echo [检查] 系统 Python                  %PY_VER%

REM ---- 0b. 清理残留进程和端口 ----
echo [清理] 检查残留进程 ...
python "%ROOT%\_cleanup.py"
if errorlevel 1 echo       (清理脚本执行完毕，可能有部分进程未能终止)

REM ---- 菜单 1: 虚拟环境 ----
:menu_venv
echo.
echo ==================================================
echo  是否创建虚拟环境 (.venv)?
echo ==================================================
echo  [Y] 是 - 创建虚拟环境，退出时自动删除(可移植，推荐)
echo  [N] 否 - 使用系统 Python(需提前装好依赖)
echo ==================================================
set "venv_choice="
set /p "venv_choice=请选择 [Y/N](默认 Y): "

if "%venv_choice%"=="" set "venv_choice=Y"
if /I "%venv_choice%"=="Y" goto use_venv
if /I "%venv_choice%"=="N" goto use_system
echo [错误] 输入无效，请输入 Y 或 N
goto menu_venv

:use_venv
echo.
echo [信息] 已选择虚拟环境模式，退出时自动清理 .venv
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
set "CLEANUP_VENV=1"

REM 第 1 步：检查已有 venv 是否可用
set "VENV_OK=0"
if exist "%ROOT%\.venv\Scripts\python.exe" (
    echo [1/3] 检查已有虚拟环境 ...
    "%ROOT%\.venv\Scripts\python.exe" --version >nul 2>nul
    if errorlevel 1 (
        echo       已有 .venv 损坏(python.exe 无法运行)，正在删除重建 ...
        rmdir /s /q "%ROOT%\.venv" 2>nul
    ) else (
        "%ROOT%\.venv\Scripts\python.exe" -m pip --version >nul 2>nul
        if errorlevel 1 (
            echo       已有 .venv 缺少 pip，正在删除重建 ...
            rmdir /s /q "%ROOT%\.venv" 2>nul
        ) else (
            echo       已有虚拟环境正常，直接复用
            set "VENV_OK=1"
        )
    )
) else (
    echo [1/3] 未检测到虚拟环境，开始创建 ...
)

if "%VENV_OK%"=="0" (
    if exist "%ROOT%\.venv" rmdir /s /q "%ROOT%\.venv" 2>nul
    echo       正在创建虚拟环境 .venv ...
    python -m venv "%ROOT%\.venv"
    if errorlevel 1 (
        echo [错误] 虚拟环境创建失败
        echo        请检查 Python 是否正确安装并可在命令行运行
        pause
        exit /b 1
    )
    echo       虚拟环境创建成功
    echo       检查 pip 是否可用 ...
    "%ROOT%\.venv\Scripts\python.exe" -m pip --version >nul 2>nul
    if errorlevel 1 (
        echo       pip 缺失，正在用 ensurepip 修复 ...
        "%ROOT%\.venv\Scripts\python.exe" -m ensurepip --upgrade >nul 2>nul
        "%ROOT%\.venv\Scripts\python.exe" -m pip --version >nul 2>nul
        if errorlevel 1 (
            echo [错误] 虚拟环境中 pip 不可用，请删除 .venv 后重试
            pause
            exit /b 1
        )
        echo       pip 修复成功
    )
)

REM 第 2 步：安装依赖
echo [2/3] 安装依赖包 ...
echo       升级 pip ...
"%ROOT%\.venv\Scripts\python.exe" -m pip install --upgrade pip -q 2>nul
echo       安装核心依赖(numpy/opencv/psutil/wmi/pyserial)...
echo       使用清华镜像源 ...
"%ROOT%\.venv\Scripts\python.exe" -m pip install -r "%ROOT%\requirements.txt" -q -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo       清华镜像失败，切换到官方 PyPI 源 ...
    "%ROOT%\.venv\Scripts\python.exe" -m pip install -r "%ROOT%\requirements.txt" -q
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请检查网络连接
        echo        可手动执行: pip install -r requirements.txt
        pause
        exit /b 1
    )
)
echo       核心依赖安装完成
if exist "%ROOT%\requirements-optional.txt" (
    echo       安装可选依赖(PyAudio/Pillow)...
    "%ROOT%\.venv\Scripts\python.exe" -m pip install -r "%ROOT%\requirements-optional.txt" -q -i https://pypi.tuna.tsinghua.edu.cn/simple 2>nul
    if errorlevel 1 (
        echo    [警告] 可选包安装失败，已跳过(麦克风检测/录屏功能不可用)
    ) else (
        echo       可选依赖安装完成
    )
)
goto menu_mode

:use_system
echo.
echo [信息] 已选择系统 Python 模式
set "PYTHON=python"
set "CLEANUP_VENV=0"
echo [1/3] 跳过虚拟环境创建
echo [2/3] 检查系统 Python 依赖 ...
python -c "import numpy,psutil,serial" 2>nul
if errorlevel 1 (
    echo [错误] 系统 Python 缺少必要的依赖包
    echo        缺少: numpy / psutil / pyserial 中的一个或多个
    echo        请手动安装: pip install -r "%ROOT%\requirements.txt"
    echo        或重新运行并选择 [Y] 创建虚拟环境
    pause
    exit /b 1
)
echo       依赖检查通过
goto menu_mode

:menu_mode
echo.
echo ==================================================
echo  请选择启动模式:
echo ==================================================
echo  [1] Thonny  代码学习模式 - 在 Thonny IDE 里写 Python
echo  [2] Mind+   图形化积木 - 需要 com0com, 首次需管理员
echo  [3] 两者都启动
echo ==================================================
set "mode_choice="
set /p "mode_choice=请选择 [1/2/3] (默认 1): "

if "%mode_choice%"=="" set "mode_choice=1"
if "%mode_choice%"=="1" (
    set "MODE=thonny"
    goto run_launch
)
if "%mode_choice%"=="2" (
    set "MODE=mindplus"
    goto run_launch
)
if "%mode_choice%"=="3" (
    set "MODE=both"
    goto run_launch
)
echo [错误] 输入无效，请输入 1、2 或 3
goto menu_mode

:run_launch
echo.
echo ==================================================
echo  启动模式: %MODE%
echo ==================================================
echo.

REM ---- 3. 启动 ----
echo [3/3] 正在启动虚拟掌控板(模式=%MODE%)...
echo       关闭此窗口或按 Ctrl+C 可停止所有服务
echo.

"%PYTHON%" "%ROOT%\start_vm.py" --mode %MODE%

if errorlevel 1 (
    echo.
    echo [!] 启动过程中出现问题，请截图上方日志以便排查
    pause
)

REM ---- 4. 清理 ----
if "%CLEANUP_VENV%"=="1" (
    echo.
    echo 正在清理虚拟环境 .venv ...
    if exist "%ROOT%\.venv" (
        rmdir /s /q "%ROOT%\.venv" 2>nul
        if exist "%ROOT%\.venv" (
            echo    [警告] 部分文件被占用，.venv 已保留，下次启动时自动清理
        ) else (
            echo    清理完成，文件夹已恢复可移植状态
        )
    )
)

echo.
echo 按任意键关闭窗口 ...
pause >nul
endlocal
