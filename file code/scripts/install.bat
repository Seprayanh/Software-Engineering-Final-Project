@echo off
chcp 65001
:: 获取当前脚本所在目录
cd /d "%~dp0"

:: 关键：检测是否在 scripts 子文件夹，如果是，则向上移动一级到项目根目录
if exist "..\main.py" (
    echo [INFO] 检测到脚本在子目录，正在切换到项目根目录...
    cd ..
)

echo ========================================================
echo        正在为您配置 TODO Pro 全能开发环境
echo ========================================================

:: 1. 检查根目录下是否有 venv，没有则创建
if not exist "venv" (
    echo [1/4] 正在创建虚拟环境 (venv)...
    python -m venv venv
) else (
    echo [1/4] 虚拟环境已存在。
)

:: 2. 激活环境
echo [2/4] 正在激活虚拟环境...
call venv\Scripts\activate

:: 3. 升级 pip (使用清华源加速)
echo [3/4] 正在升级 pip...
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

:: 4. 安装所有依赖 (合并了你的 requirement.txt 和打包所需的库)
:: 包含了: rich, plyer, pyngrok (你的原需求) + pywin32, winshell (快捷方式) + auto-py-to-exe (打包)
echo [4/4] 正在一键安装所有库...
pip install click rich plyer pywebview pyngrok pywin32 winshell pyinstaller auto-py-to-exe -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo ========================================================
echo      恭喜！环境配置完成！
echo      现在你可以直接运行根目录下的 main.py
echo      或者输入 auto-py-to-exe 开始打包。
echo ========================================================
pause