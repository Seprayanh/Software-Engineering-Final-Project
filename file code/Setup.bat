@echo off
chcp 65001 >nul
title Todo Pro 自动环境配置工具
color 0A

echo ========================================================
echo       正在为您自动部署 Todo Pro 运行环境
echo ========================================================
echo.

cd /d "%~dp0"

:: 1. 检查 Python 是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [错误] 未检测到 Python！
    echo 请先下载并安装 Python (记得勾选 "Add to PATH")。
    pause
    exit
)

:: 2. 清理旧的失败环境 (防止之前的报错残留)
if exist venv (
    echo [信息] 检测到旧环境，正在清理以确保安装纯净...
    rmdir /s /q venv
)

:: 3. 创建全新虚拟环境
echo [1/3] 正在创建虚拟环境 (venv)...
python -m venv venv
if not exist venv\Scripts\python.exe (
    color 0C
    echo [错误] 虚拟环境创建失败。请检查文件夹权限。
    pause
    exit
)

:: 4. 激活并安装依赖 (关键步骤)
echo [2/3] 正在升级安装工具...
call venv\Scripts\activate
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

echo [3/3] 正在安装核心组件 (click, pywebview, rich)...
pip install click rich pywebview plyer pyngrok -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo ========================================================
echo [成功] 环境配置完毕！
echo 现在您可以直接双击 TodoPro.vbs 启动程序了。
echo ========================================================
echo.
echo 按任意键退出...
pause >nul
del "%~f0" & exit