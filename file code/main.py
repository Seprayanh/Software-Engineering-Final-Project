import sys
import os
import ctypes
import multiprocessing

# --- 单实例锁 (防止重复打开) ---
def is_already_running():
    if sys.platform == 'win32':
        mutex_name = "Global\\ToDoPro_Unique_Mutex_v2"
        kernel32 = ctypes.windll.kernel32
        mutex = kernel32.CreateMutexW(None, False, mutex_name)
        if kernel32.GetLastError() == 183:
            return True
        sys._singleton_mutex = mutex
    return False

# --- 路径处理工具 ---
def get_resource_path(relative_path):
    """获取资源绝对路径，兼容开发环境和打包后的EXE环境"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

if __name__ == '__main__':
    # 1. 防止多开
    if is_already_running():
        sys.exit(0)

    # 2. 多进程支持 (PyInstaller 必须)
    multiprocessing.freeze_support()
    
    # 3. 设置 AppID (让任务栏图标显示正确)
    if sys.platform == 'win32':
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('todopro.app.v1.0')
        except:
            pass

    # 4. 启动逻辑
    try:
        # 确保 src 目录在搜索路径中
        sys.path.append(get_resource_path("src"))
        
        from src.desktop import run_desktop
        run_desktop()
        
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        ctypes.windll.user32.MessageBoxW(0, f"Error: {e}\n\n{err_msg}", "Startup Failed", 0x10)