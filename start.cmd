@echo off
setlocal enabledelayedexpansion

REM 进入仓库根目录（脚本所在目录）
cd /d "%~dp0"

set VENV_DIR=.venv
set REQUIREMENTS=requirements.txt
set CONFIG=config.toml
set CONFIG_TEMPLATE=config-template.toml

REM 解析参数 --reinstall
set REINSTALL=false
if "%1"=="--reinstall" set REINSTALL=true

REM 选择 Python 命令
set PY=
where py >nul 2>nul && set PY=py -3
if "%PY%"=="" (
  where python >nul 2>nul && set PY=python
)
if "%PY%"=="" (
  echo [启动] 未找到 Python，请先安装 Python 3
  exit /b 1
)

REM 处理虚拟环境
if exist "%VENV_DIR%" (
  if /i "%REINSTALL%"=="true" (
    echo [启动] 重新创建虚拟环境 %VENV_DIR%
    rmdir /s /q "%VENV_DIR%"
  )
)

if not exist "%VENV_DIR%" (
  echo [启动] 创建虚拟环境 %VENV_DIR%
  %PY% -m venv "%VENV_DIR%"
  if errorlevel 1 exit /b 1
)

REM 激活虚拟环境
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
  echo [启动] 无法激活虚拟环境
  exit /b 1
)

echo [启动] 升级 pip
python -m pip install --upgrade pip

if exist "%REQUIREMENTS%" (
  echo [启动] 安装依赖 %REQUIREMENTS%
  python -m pip install -r "%REQUIREMENTS%"
) else (
  echo [启动] 未找到 %REQUIREMENTS%，跳过依赖安装
)

if not exist "%CONFIG%" if exist "%CONFIG_TEMPLATE%" (
  echo [启动] 生成默认配置 %CONFIG%
  copy /y "%CONFIG_TEMPLATE%" "%CONFIG%" >nul
)

echo [启动] 正在运行 Maicraft-Mai ... (Ctrl+C 退出)
python main.py

endlocal

