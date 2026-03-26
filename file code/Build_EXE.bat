@echo off
chcp 65001 >nul
echo ==========================================
echo       正在构建 TODO Pro 可执行文件 (EXE)
echo ==========================================
echo.

:: 1. 激活虚拟环境 (确保你已经运行过 Setup.bat)
if exist venv (
    call venv\Scripts\activate
) else (
    echo [错误] 找不到 venv 文件夹，请先运行 Setup.bat 安装环境！
    pause
    exit
)

:: 2. 安装 PyInstaller 打包工具
echo [INFO] 正在安装 PyInstaller...
pip install pyinstaller

:: 3. 开始打包
:: --noconsole: 不显示黑色控制台窗口
:: --onefile: 打包成单个 exe 文件
:: --name: 指定生成的 exe 名字
:: --add-data: 关键！把 src 文件夹（包含html/css）打包进去。注意 Windows 下分隔符是分号 ;
:: --clean: 清理缓存
echo.
echo [INFO] 正在打包，请耐心等待...
pyinstaller --noconsole --onefile --clean ^
    --name "TodoPro" ^
    --add-data "src;src" ^
    --add-data "data;data" ^
    main.py

echo.
echo ==========================================
echo [成功] 打包完成！
echo.
echo 你的 EXE 文件在 "dist" 文件夹中。
echo 正在为你打开文件夹...
echo ==========================================
start dist
pause