import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import configparser
import shutil
import threading
import subprocess
from pathlib import Path
import requests
import re
from requests.exceptions import RequestException, Timeout, ConnectionError
import time
import psutil
from collections import deque
import webbrowser
import datetime

class ResourceMonitorWindow:
    def __init__(self, parent, server_tab_id, process_pid):
        """
        初始化资源监控窗口
        :param parent: 父窗口
        :param server_tab_id: 服务器标签ID
        :param process_pid: 服务器进程PID
        """
        self.parent = parent
        self.server_tab_id = server_tab_id
        self.pid = process_pid
        self.process = None
        self.running = True
        
        # 数据缓存（保留最近60个数据点）
        self.cpu_data = deque(maxlen=60)
        self.memory_data = deque(maxlen=60)
        
        # 创建窗口
        self.window = tk.Toplevel(parent)
        self.window.title(f"Server Resource Monitoring - {server_tab_id}")
        self.window.geometry("800x500")
        self.window.protocol("WM_DELETE_WINDOW", self.stop_monitoring)
        
        # 创建UI组件
        self.create_widgets()
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self.monitor_resources, daemon=True)
        self.monitor_thread.start()

    def create_widgets(self):
        """创建窗口组件"""
        # 状态标签
        self.status_frame = ttk.Frame(self.window)
        self.status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(self.status_frame, text="CPU Usage:").pack(side=tk.LEFT, padx=5)
        self.cpu_label = ttk.Label(self.status_frame, text="0%")
        self.cpu_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(self.status_frame, text="Memory Usage:").pack(side=tk.LEFT, padx=5)
        self.memory_label = ttk.Label(self.status_frame, text="0%")
        self.memory_label.pack(side=tk.LEFT, padx=5)
        
        # 图表画布
        self.canvas_frame = ttk.LabelFrame(self.window, text="Resource Usage Trends")
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 控制按钮
        self.btn_frame = ttk.Frame(self.window)
        self.btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(
            self.btn_frame,
            text="Refresh",
            command=self.force_refresh
        ).pack(side=tk.RIGHT, padx=5)

    def monitor_resources(self):
        """监控服务器资源使用情况的线程函数"""
        try:
            self.process = psutil.Process(self.pid)
        except psutil.NoSuchProcess:
            self.window.after(0, lambda: self.show_error("The process could not be found and may have already terminated."))
            return
        
        while self.running and self.process.is_running():
            # 每次循环前检查窗口是否存在
            if not hasattr(self, 'window') or not self.window.winfo_exists():
                self.running = False
                break
                
            try:
                # 获取资源使用数据
                cpu_percent = self.process.cpu_percent(interval=1)
                memory_percent = self.process.memory_percent()
                
                # 缓存数据
                self.cpu_data.append(cpu_percent)
                self.memory_data.append(memory_percent)
                
                # 更新UI
                self.window.after(0, lambda: self.update_ui(cpu_percent, memory_percent))
                
                # 1秒采样一次
                time.sleep(1)
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                self.window.after(0, lambda: self.show_error(f"Monitoring error: {str(e)}"))
                break
            except Exception as e:
                # 捕获其他可能的异常
                if self.running:
                    print(f"Monitor thread exception: {str(e)}")
                break

    def update_ui(self, cpu, memory):
        """更新UI显示，增加存在性检查"""
        # 检查窗口是否仍然存在
        if not hasattr(self, 'window') or not self.window.winfo_exists():
            return
            
        # 检查组件是否仍然存在
        try:
            # 更新数值标签
            self.cpu_label.config(text=f"{cpu:.1f}%")
            self.memory_label.config(text=f"{memory:.1f}%")
            
            # 绘制图表
            self.draw_chart()
        except tk.TclError:
            # 组件已被销毁，停止更新
            self.running = False

    def draw_chart(self):
        """绘制资源使用趋势图表"""
        self.canvas.delete("all")
        width = self.canvas.winfo_width() or 800
        height = self.canvas.winfo_height() or 400
        
        if width < 100 or height < 100:
            return
            
        # 绘制坐标轴
        padding = 40
        chart_width = width - 2 * padding
        chart_height = height - 2 * padding
        
        # X轴和Y轴
        self.canvas.create_line(padding, padding, padding, height - padding, width=2)
        self.canvas.create_line(padding, height - padding, width - padding, height - padding, width=2)
        
        # Y轴刻度 (0-100%)
        for i in range(0, 101, 20):
            y = height - padding - (i / 100 * chart_height)
            self.canvas.create_line(padding - 5, y, padding, y)
            self.canvas.create_text(padding - 10, y, text=f"{i}%", anchor=tk.E)
        
        # 绘制CPU使用率曲线
        if len(self.cpu_data) >= 2:
            cpu_points = []
            for idx, value in enumerate(self.cpu_data):
                x = padding + (idx / (len(self.cpu_data) - 1)) * chart_width
                y = height - padding - (value / 100 * chart_height)
                cpu_points.extend([x, y])
            
            self.canvas.create_line(cpu_points, fill="blue", width=2)
            self.canvas.create_text(padding + 10, padding + 10, text="CPU", fill="blue", anchor=tk.W)
        
        # 绘制内存使用率曲线
        if len(self.memory_data) >= 2:
            mem_points = []
            for idx, value in enumerate(self.memory_data):
                x = padding + (idx / (len(self.memory_data) - 1)) * chart_width
                y = height - padding - (value / 100 * chart_height)
                mem_points.extend([x, y])
            
            self.canvas.create_line(mem_points, fill="red", width=2)
            self.canvas.create_text(padding + 60, padding + 10, text="内存", fill="red", anchor=tk.W)

    def force_refresh(self):
        """强制刷新数据"""
        if self.process and self.process.is_running():
            try:
                cpu = self.process.cpu_percent(interval=0.1)
                memory = self.process.memory_percent()
                self.update_ui(cpu, memory)
            except Exception as e:
                self.show_error(f"Refresh failed: {str(e)}")

    def show_error(self, message):
        """显示错误信息"""
        ttk.Label(
            self.status_frame,
            text=message,
            foreground="red"
        ).pack(side=tk.LEFT, padx=10)

    def stop_monitoring(self):
        """停止监控并关闭窗口"""
        self.running = False
        self.window.destroy()

def clean_ansi_codes(text):
    """移除所有ANSI转义序列"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

class DownloadManager:
    """增强版下载管理器（解决超时和界面卡死问题）"""
    def __init__(self, root):
        self.root = root
        self.active_downloads = {}  # 存储活跃下载任务
        self.lock = threading.Lock()  # 线程安全锁

    def start_download(self, url, save_path, progress_callback=None, completion_callback=None):
        """启动带进度监控的下载（线程安全版）"""
        with self.lock:
            if url in [data['url'] for data in self.active_downloads.values()]:
                return False  # 避免重复下载

            download_id = str(hash(url + save_path))
            self.active_downloads[download_id] = {
                'url': url,
                'path': save_path,
                'active': True,
                'progress': 0
            }

            threading.Thread(
                target=self._download_file,
                args=(download_id, url, save_path, progress_callback, completion_callback),
                daemon=True
            ).start()
            return True

    def _download_file(self, download_id, url, save_path, progress_callback, completion_callback):
        """实际下载线程（含超时处理和断点续传）"""
        temp_path = f"{save_path}.tmp"
        try:
            # 创建会话并配置参数
            session = requests.Session()
            session.max_redirects = 5
            session.stream = True
            
            # 第一次尝试获取文件信息（带重试）
            response = self._retry_request(
                lambda: session.head(url, timeout=10),
                max_retries=2,
                delay=1
            )
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            # 断点续传检查
            if os.path.exists(temp_path):
                downloaded = os.path.getsize(temp_path)
                headers = {'Range': f'bytes={downloaded}-'}
            else:
                headers = {}
                os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # 分块下载（主下载循环）
            with session.get(
                url,
                headers=headers,
                stream=True,
                timeout=(10, 30)  # 连接10秒，读取30秒超时
            ) as response:
                response.raise_for_status()
                
                # 更新进度最大值
                if progress_callback and total_size > 0:
                    self.root.after(0, lambda: progress_callback(0, total_size))
                
                chunk_size = 8192  # 8KB分块
                update_interval = max(total_size // 100, 1024 * 1024)  # 至少1MB更新间隔
                
                with open(temp_path, 'ab' if downloaded else 'wb') as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if not self._is_download_active(download_id):
                            raise Exception("Download canceled by user")
                            
                        if chunk:  # 过滤keep-alive空块
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # 控制进度更新频率
                            if downloaded % update_interval == 0:
                                progress = downloaded / total_size * 100 if total_size > 0 else 0
                                self._update_download_progress(
                                    download_id,
                                    progress,
                                    downloaded,
                                    total_size,
                                    progress_callback
                                )
                
                # 下载完成重命名文件
                os.replace(temp_path, save_path)
                
            # 成功回调
            self._safe_callback(
                completion_callback,
                True,
                None,
                download_id
            )

        except Exception as e:
            # 失败处理
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
                    
            self._safe_callback(
                completion_callback,
                False,
                str(e),
                download_id
            )
        finally:
            # 确保清理下载状态
            with self.lock:
                if download_id in self.active_downloads:
                    del self.active_downloads[download_id]

    def _retry_request(self, request_func, max_retries=3, delay=1):
        """带重试机制的请求封装"""
        last_exception = None
        for attempt in range(max_retries):
            try:
                return request_func()
            except (RequestException, Timeout, ConnectionError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    time.sleep(delay * (attempt + 1))  # 指数退避
        raise last_exception

    def _is_download_active(self, download_id):
        """检查下载是否仍活跃"""
        with self.lock:
            return (download_id in self.active_downloads and 
                    self.active_downloads[download_id]['active'])

    def _update_download_progress(self, download_id, progress, downloaded, total_size, callback):
        """安全更新下载进度"""
        with self.lock:
            if download_id in self.active_downloads:
                self.active_downloads[download_id]['progress'] = progress
                
        if callback:
            self.root.after(0, lambda: callback(progress))

    def _safe_callback(self, callback, success, error_msg, download_id):
        """安全执行回调（确保在主线程）"""
        if callback:
            self.root.after(0, lambda: callback(success, error_msg))

    def cancel_download(self, url):
        """取消指定下载任务"""
        with self.lock:
            for download_id, data in list(self.active_downloads.items()):
                if data['url'] == url:
                    data['active'] = False
                    return True
        return False

    def cancel_all(self):
        """取消所有下载任务"""
        with self.lock:
            for download_id in list(self.active_downloads.keys()):
                self.active_downloads[download_id]['active'] = False

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import requests
import threading
import json

class ServerCreationWizard:
    def __init__(self, root, callback):
        self.root = root
        self.callback = callback
        
        # 创建向导窗口
        self.window = tk.Toplevel(root)
        self.window.title("Create New Server")
        self.window.geometry("600x500")
        self.window.transient(root)
        self.window.grab_set()
        
        # 向导步骤
        self.current_step = 0
        self.steps = [
            "Server Basic Information",
            "Server type and version",
            "Server location",
            "Confirm Information"
        ]
        
        # 服务器数据
        self.server_data = {
            'name': '',
            'core_type': 'vanilla',
            'core_version': '',
            'path': '',
            'custom_script': '',
            'core_url': '',
            'actual_core_file': ''  # 新增：实际下载的文件名
        }
        
        # 可用版本缓存
        self.available_versions = {
            'vanilla': [],
            'paper': [],
            'spigot': []
        }
        
        # 初始化UI
        self._setup_ui()
        
        # 加载可用版本
        self._load_available_versions()
    
    def _setup_ui(self):
        """设置向导界面"""
        # 步骤指示器
        self.step_label = ttk.Label(self.window, text=f"Step {self.current_step+1}/{len(self.steps)}: {self.steps[self.current_step]}", font=('Arial', 10, 'bold'))
        self.step_label.pack(pady=10)
        
        # 主容器
        self.main_frame = ttk.Frame(self.window)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 导航按钮
        self.nav_frame = ttk.Frame(self.window)
        self.nav_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.prev_btn = ttk.Button(self.nav_frame, text="Previous step", command=self._prev_step, state=tk.DISABLED)
        self.prev_btn.pack(side=tk.LEFT)
        
        self.next_btn = ttk.Button(self.nav_frame, text="Next step", command=self._next_step)
        self.next_btn.pack(side=tk.RIGHT)
        
        # 初始化所有步骤
        self._init_step0()
        self._init_step1()
        self._init_step2()
        self._init_step3()
        
        # 默认显示第一步
        self._show_step(0)
    
    def _show_step(self, step):
        """显示指定步骤"""
        for widget in self.main_frame.winfo_children():
            widget.pack_forget()
        
        self.current_step = step
        self.step_label.config(text=f"Step {self.current_step+1}/{len(self.steps)}: {self.steps[self.current_step]}")
        
        # 更新按钮状态
        self.prev_btn.config(state=tk.NORMAL if step > 0 else tk.DISABLED)
        if step == len(self.steps) - 1:
            self.next_btn.config(text="Done")
        else:
            self.next_btn.config(text="Next step")
        
        if step == 0:
            self.step0_frame.pack(fill=tk.BOTH, expand=True)
        elif step == 1:
            self.step1_frame.pack(fill=tk.BOTH, expand=True)
        elif step == 2:
            self.step2_frame.pack(fill=tk.BOTH, expand=True)
        elif step == 3:
            self._update_confirmation()
            self.step3_frame.pack(fill=tk.BOTH, expand=True)
    
    def _init_step0(self):
        """初始化步骤0：基本信息"""
        self.step0_frame = ttk.Frame(self.main_frame)
        
        ttk.Label(self.step0_frame, text="Server Name:", font=('Arial', 9)).pack(anchor=tk.W, pady=(10, 5))
        self.name_entry = ttk.Entry(self.step0_frame, font=('Arial', 9))
        self.name_entry.pack(fill=tk.X, pady=5)
        self.name_entry.bind('<KeyRelease>', lambda e: self._validate_step0())
        
        ttk.Label(self.step0_frame, text="Server Type:", font=('Arial', 9)).pack(anchor=tk.W, pady=(10, 5))
        self.core_type_var = tk.StringVar(value='vanilla')
        core_type_frame = ttk.Frame(self.step0_frame)
        core_type_frame.pack(fill=tk.X, pady=5)
        
        ttk.Radiobutton(core_type_frame, text="Vanilla (Official original version)", variable=self.core_type_var, value='vanilla', command=self._on_core_type_change).pack(anchor=tk.W)
        ttk.Radiobutton(core_type_frame, text="Paper (Optimized version)", variable=self.core_type_var, value='paper', command=self._on_core_type_change).pack(anchor=tk.W)
        ttk.Radiobutton(core_type_frame, text="Spigot (Plugin version)", variable=self.core_type_var, value='spigot', command=self._on_core_type_change).pack(anchor=tk.W)
    
    def _init_step1(self):
        """初始化步骤1：版本选择"""
        self.step1_frame = ttk.Frame(self.main_frame)
        
        ttk.Label(self.step1_frame, text="Server Version:", font=('Arial', 9)).pack(anchor=tk.W, pady=(10, 5))
        
        # 版本选择框架
        version_frame = ttk.Frame(self.step1_frame)
        version_frame.pack(fill=tk.X, pady=5)
        
        self.version_var = tk.StringVar()
        self.version_combobox = ttk.Combobox(version_frame, textvariable=self.version_var, state="readonly")
        self.version_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.version_combobox.bind('<<ComboboxSelected>>', lambda e: self._validate_step1())
        
        # 刷新按钮
        ttk.Button(
            version_frame, 
            text="Refresh version", 
            command=self._load_available_versions
        ).pack(side=tk.RIGHT)
        
        # 版本加载状态
        self.version_status = ttk.Label(self.step1_frame, text="Loading version list...", foreground="blue")
        self.version_status.pack(anchor=tk.W, pady=5)
        
        # 版本说明
        desc_frame = ttk.LabelFrame(self.step1_frame, text="Version Notes")
        desc_frame.pack(fill=tk.X, pady=10)
        
        self.desc_text = tk.Text(desc_frame, height=4, wrap=tk.WORD, font=('Arial', 8))
        self.desc_text.pack(fill=tk.BOTH, padx=5, pady=5)
        self.desc_text.insert(tk.END, "Please select a server version. It is recommended to choose the stable version for the best experience.")
        self.desc_text.config(state=tk.DISABLED)
    
    def _init_step2(self):
        """初始化步骤2：服务器位置"""
        self.step2_frame = ttk.Frame(self.main_frame)
        
        ttk.Label(self.step2_frame, text="Server Path:", font=('Arial', 9)).pack(anchor=tk.W, pady=(10, 5))
        
        path_frame = ttk.Frame(self.step2_frame)
        path_frame.pack(fill=tk.X, pady=5)
        
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, font=('Arial', 9))
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.path_entry.bind('<KeyRelease>', lambda e: self._validate_step2())
        
        ttk.Button(
            path_frame, 
            text="Browse...", 
            command=self._browse_path
        ).pack(side=tk.RIGHT)
        
        # 路径验证信息
        self.path_status = ttk.Label(self.step2_frame, text="", font=('Arial', 8))
        self.path_status.pack(anchor=tk.W, pady=5)
        
        # 默认路径为当前目录下的servers文件夹
        default_path = str(Path.cwd() / "servers")
        self.path_var.set(default_path)
        self._validate_step2()
    
    def _init_step3(self):
        """初始化步骤3：确认信息"""
        self.step3_frame = ttk.Frame(self.main_frame)
        
        # 确认信息框
        confirm_frame = ttk.LabelFrame(self.step3_frame, text="Server configuration information")
        confirm_frame.pack(fill=tk.X, pady=10)
        
        self.confirmation_text = tk.Text(
            confirm_frame,
            height=6,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=('Arial', 9)
        )
        self.confirmation_text.pack(fill=tk.BOTH, padx=5, pady=5)
        
        # 自定义启动脚本
        script_frame = ttk.LabelFrame(self.step3_frame, text="Custom startup script")
        script_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        script_scrollbar = ttk.Scrollbar(script_frame)
        script_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.script_text = tk.Text(
            script_frame,
            height=6,
            wrap=tk.WORD,
            yscrollcommand=script_scrollbar.set,
            font=('Courier New', 9)
        )
        self.script_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        script_scrollbar.config(command=self.script_text.yview)
        
        # 设置默认启动脚本
        default_script = """@echo off
title Minecraft Server - %CD%
java -Xms1G -Xmx2G -jar {core_name} nogui
echo Server has stopped.
echo Press any key to exit...
pause >nul"""
        self.script_text.insert(tk.END, default_script)
        
        # 脚本说明
        ttk.Label(self.step3_frame, text="Tip: {core_name} will be automatically replaced with the actual server core filename", 
                 font=('Arial', 8), foreground="gray").pack(anchor=tk.W)
    
    def _update_confirmation(self):
        """更新确认信息"""
        self.confirmation_text.config(state=tk.NORMAL)
        self.confirmation_text.delete(1.0, tk.END)
        
        info = f"""Server Name: {self.server_data['name']}
Server Type: {self.server_data['core_type']}
Server Version: {self.server_data['core_version']}
Server Path: {self.server_data['path']}
Full path: {Path(self.server_data['path']) / self.server_data['name']}

Download URL: {self.server_data.get('core_url', 'To be generated')}
"""
        self.confirmation_text.insert(tk.END, info)
        self.confirmation_text.config(state=tk.DISABLED)
    
    def _on_core_type_change(self):
        """服务器类型改变时的处理"""
        self._load_available_versions()
        self._validate_step0()
    
    def _validate_step0(self):
        """验证步骤0"""
        name = self.name_entry.get().strip()
        if name:
            self.next_btn.config(state=tk.NORMAL)
        else:
            self.next_btn.config(state=tk.DISABLED)
    
    def _validate_step1(self):
        """验证步骤1"""
        if self.version_var.get():
            self.next_btn.config(state=tk.NORMAL)
        else:
            self.next_btn.config(state=tk.DISABLED)
    
    def _validate_step2(self):
        """验证步骤2"""
        path = self.path_var.get().strip()
        if path:
            # 检查路径是否有效
            try:
                Path(path)
                self.path_status.config(text="The path is valid", foreground="green")
                self.next_btn.config(state=tk.NORMAL)
            except Exception:
                self.path_status.config(text="Invalid path", foreground="red")
                self.next_btn.config(state=tk.DISABLED)
        else:
            self.path_status.config(text="Please enter the path", foreground="red")
            self.next_btn.config(state=tk.DISABLED)
    
    def _browse_path(self):
        """浏览选择服务器路径"""
        path = filedialog.askdirectory(title="Select server storage directory")
        if path:
            self.path_var.set(path)
            self._validate_step2()
    
    def _load_available_versions(self):
        """加载可用的服务器版本"""
        core_type = self.core_type_var.get()
        
        def worker():
            try:
                self.root.after(0, lambda: self.version_status.config(text="Loading version list...", foreground="blue"))
                
                if core_type == 'vanilla':
                    response = requests.get("https://launchermeta.mojang.com/mc/game/version_manifest.json", timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    versions = [v['id'] for v in data['versions'] if v['type'] == 'release'][:20]  # 只显示最近20个版本
                    
                elif core_type == 'paper':
                    response = requests.get("https://api.papermc.io/v2/projects/paper", timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    versions = data['versions'][-10:]  # 显示最近10个版本
                    
                elif core_type == 'spigot':
                    versions = self._get_spigot_versions()
                
                self.available_versions[core_type] = versions
                
                # 更新UI
                self.root.after(0, lambda: self._update_version_combobox(versions))
                self.root.after(0, lambda: self.version_status.config(text=f"找到 {len(versions)} 个可用版本", foreground="green"))
                
                # 更新版本说明
                desc = f"{core_type.capitalize()} Server - It is recommended to choose the latest stable version"
                self.root.after(0, lambda: self._update_version_desc(desc))
                
            except Exception as e:
                error_msg = f"Failed to load version: {str(e)}"
                self.root.after(0, lambda: self.version_status.config(text=error_msg, foreground="red"))
                self.root.after(0, lambda: self._update_version_combobox([]))
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _update_version_combobox(self, versions):
        """更新版本选择框"""
        self.version_combobox['values'] = versions
        if versions:
            self.version_combobox.set(versions[-1])  # 默认选择最新版本
            self.version_combobox.config(state="readonly")
        else:
            self.version_combobox.set("")
            self.version_combobox.config(state="disabled")
    
    def _update_version_desc(self, desc):
        """更新版本说明"""
        self.desc_text.config(state=tk.NORMAL)
        self.desc_text.delete(1.0, tk.END)
        self.desc_text.insert(tk.END, desc)
        self.desc_text.config(state=tk.DISABLED)
    
    def _prev_step(self):
        """上一步"""
        if self.current_step > 0:
            self._show_step(self.current_step - 1)
    
    def _next_step(self):
        """下一步"""
        if not self._validate_current_step():
            return
        
        if self.current_step < len(self.steps) - 1:
            self._show_step(self.current_step + 1)
        else:
            self._finish_creation()
    
    def _validate_current_step(self):
        """验证当前步骤数据"""
        if self.current_step == 0:
            name = self.name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Please enter the server name")
                return False
            self.server_data['name'] = name
            self.server_data['core_type'] = self.core_type_var.get()
        
        elif self.current_step == 1:
            version = self.version_var.get()
            if not version:
                messagebox.showerror("Error", "Please select the server version")
                return False
            self.server_data['core_version'] = version
            
            # 生成下载URL
            core_url = self._get_core_url()
            if not core_url:
                messagebox.showerror("Error", "Unable to generate download link, please check if the version number is correct.")
                return False
            self.server_data['core_url'] = core_url
        
        elif self.current_step == 2:
            path = self.path_var.get().strip()
            if not path:
                messagebox.showerror("Error", "Please select the server path")
                return False
            
            # 验证路径
            try:
                Path(path)
            except Exception:
                messagebox.showerror("Error", "The path is invalid, please select a valid directory.")
                return False
            
            self.server_data['path'] = path
        
        return True
    
    def _get_core_url(self):
        """获取服务器核心下载URL"""
        core_type = self.server_data['core_type']
        version = self.server_data['core_version']
        
        try:
            if core_type == 'vanilla':
                return self._get_vanilla_url(version)
            elif core_type == 'paper':
                return self._get_paper_url(version)
            elif core_type == 'spigot':
                return self._get_spigot_url(version)
        except Exception as e:
            print(f"Failed to generate download URL: {e}")
            return ""
        
        return ""
    
    def _get_paper_url(self, version):
        """修复Paper下载URL生成"""
        try:
            # 方法1：尝试获取最新构建信息
            builds_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds"
            try:
                response = requests.get(builds_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data['builds']:
                        latest_build = data['builds'][-1]
                        build_number = latest_build['build']
                        return f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{build_number}/downloads/paper-{version}-{build_number}.jar"
            except:
                pass
            
            # 方法2：使用latest标签（备用方案）
            return f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/latest/downloads/paper-{version}-latest.jar"
            
        except Exception as e:
            print(f"获取Paper URL失败，使用备用方案: {e}")
            # 方法3：硬编码已知可用的URL
            return f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/latest/downloads/paper-{version}-latest.jar"
    
    def _get_vanilla_url(self, version):
        """获取Vanilla核心下载URL"""
        try:
            response = requests.get("https://launchermeta.mojang.com/mc/game/version_manifest.json", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            for version_info in data['versions']:
                if version_info['id'] == version:
                    detail_response = requests.get(version_info['url'], timeout=10)
                    detail_data = detail_response.json()
                    return detail_data['downloads']['server']['url']
            
            return f"https://piston-data.mojang.com/v1/objects/8f3112a1049751cc472ec13e397eade5336ca7ae/server.jar"  # 默认URL
            
        except Exception:
            return f"https://piston-data.mojang.com/v1/objects/8f3112a1049751cc472ec13e397eade5336ca7ae/server.jar"
    
    def _get_spigot_url(self, version):
        """获取Spigot核心下载URL"""
        # 使用可靠的下载源
        base_urls = [
            f"https://download.cdn.getbukkit.org/spigot/spigot-{version}.jar",
            f"https://cdn.getbukkit.org/spigot/spigot-{version}.jar"
        ]
        return base_urls[0]
    
    def _get_spigot_versions(self):
        """获取Spigot版本列表"""
        return ['1.20.1', '1.19.4', '1.18.2', '1.17.1', '1.16.5', '1.15.2', '1.14.4']
    
    def _finish_creation(self):
        """完成创建"""
        # 获取自定义脚本
        self.server_data['custom_script'] = self.script_text.get("1.0", tk.END).strip()
        
        # 开始下载
        self._start_download()
    
    def _start_download(self):
        """开始下载服务器核心"""
        # 创建下载窗口
        self.download_window = tk.Toplevel(self.window)
        self.download_window.title("Download Server Core")
        self.download_window.geometry("500x300")
        self.download_window.transient(self.window)
        self.download_window.grab_set()
        
        # 下载信息
        info_frame = ttk.Frame(self.download_window)
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(info_frame, text="Downloading server core files...", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        
        # 显示详细信息
        details_text = f"""Server Type: {self.server_data['core_type']}
Version: {self.server_data['core_version']}
Download URL: {self.server_data['core_url']}"""
        
        details_label = ttk.Label(info_frame, text=details_text, justify=tk.LEFT)
        details_label.pack(anchor=tk.W, pady=5)
        
        # 进度条
        progress_frame = ttk.Frame(self.download_window)
        progress_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(progress_frame, text="Download progress:").pack(anchor=tk.W)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=400
        )
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.progress_label = ttk.Label(progress_frame, text="Preparing to download...")
        self.progress_label.pack(anchor=tk.W)
        
        # 控制按钮
        btn_frame = ttk.Frame(self.download_window)
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self._cancel_download)
        self.cancel_btn.pack(side=tk.RIGHT)
        
        # 在后台线程中下载
        self.download_cancelled = False
        threading.Thread(target=self._download_core, daemon=True).start()
    
    def _cancel_download(self):
        """取消下载"""
        self.download_cancelled = True
        if hasattr(self, 'download_window') and self.download_window.winfo_exists():
            self.download_window.destroy()
        messagebox.showinfo("Info", "Download canceled")
    
    def _download_core(self):
        """下载服务器核心"""
        try:
            # 准备服务器目录
            server_dir = Path(self.server_data['path']) / self.server_data['name']
            server_dir.mkdir(parents=True, exist_ok=True)
            
            # 从URL中提取实际文件名
            core_url = self.server_data['core_url']
            expected_filename = core_url.split('/')[-1]
            save_path = server_dir / expected_filename
            
            self.root.after(0, lambda: self.progress_label.config(text=f"Download file: {expected_filename}"))
            
            # 开始下载
            response = requests.get(core_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.download_cancelled:
                        raise Exception("Download canceled by user")
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # 更新进度
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            self.root.after(0, lambda: self.progress_var.set(progress))
                            self.root.after(0, lambda: self.progress_label.config(
                                text=f"Downloading: {downloaded/1024/1024:.1f}MB / {total_size/1024/1024:.1f}MB ({progress:.1f}%)"
                            ))
            
            # 验证下载的文件
            if not self._validate_jar_file(save_path):
                raise Exception("The downloaded file is not a valid JAR file")
            
            # 记录实际文件名
            self.server_data['actual_core_file'] = expected_filename
            
            # 下载成功
            self.root.after(0, lambda: self._handle_download_completion(True, None))
            
        except Exception as e:
            if not self.download_cancelled:
                self.root.after(0, lambda: self._handle_download_completion(False, str(e)))
    
    def _validate_jar_file(self, file_path):
        """验证JAR文件是否有效"""
        try:
            if not os.path.exists(file_path):
                return False
            
            file_size = os.path.getsize(file_path)
            if file_size < 1024:  # 小于1KB的文件无效
                return False
            
            # 检查JAR文件头
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if header[:2] != b'PK':  # JAR文件以PK开头
                    return False
            
            return True
        except Exception:
            return False
    
    def _handle_download_completion(self, success, error_msg=None):
        """处理下载完成事件（修复版）"""
        # 关闭下载窗口
        if hasattr(self, 'download_window') and self.download_window.winfo_exists():
            self.download_window.destroy()
        
        if not success:
            self._handle_download_failure(error_msg)
            return
        
        # 下载成功后的处理
        server_dir = Path(self.server_data['path']) / self.server_data['name']
        try:
            # 确保目录存在
            server_dir.mkdir(parents=True, exist_ok=True)
            
            # 查找实际的JAR文件（修复文件检测问题）
            jar_files = list(server_dir.glob("*.jar"))
            if not jar_files:
                raise Exception("No server core files (.jar files) were found")
            
            # 使用实际找到的JAR文件
            actual_core_file = jar_files[0].name
            self.server_data['actual_core_file'] = actual_core_file
            
            # 保存启动脚本（使用实际找到的核心文件名）
            script_content = self.server_data['custom_script'].replace("{core_name}", actual_core_file)
            
            bat_path = server_dir / "start.bat"
            bat_path.write_text(script_content, encoding='utf-8')
            
            # 创建服务器配置文件
            self._create_server_config(server_dir)
            
            # 回调主程序
            self.callback(self.server_data)
            
            # 显示成功消息
            messagebox.showinfo(
                "Server created successfully", 
                f"✅ Server created successfully!\n\n"
                f"Name: {self.server_data['name']}\n"
                f"Type: {self.server_data['core_type']}\n"
                f"Version: {self.server_data['core_version']}\n"
                f"Path: {server_dir}\n"
                f"Core File: {actual_core_file}\n\n"
                f"You can start the server now！"
            )
            
            # 关闭向导窗口
            self.window.destroy()
            
        except Exception as e:
            self._handle_download_failure(f"Unable to complete server creation: {str(e)}")
            self._cleanup_failed_creation(server_dir)
    
    def _create_server_config(self, server_dir):
        """创建服务器配置文件"""
        config = {
            'server_name': self.server_data['name'],
            'server_type': self.server_data['core_type'],
            'server_version': self.server_data['core_version'],
            'core_file': self.server_data['actual_core_file'],
            'created_time': time.strftime("%Y-%m-%d %H:%M:%S"),
            'path': str(server_dir)
        }
        
        config_path = server_dir / "msm_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def _handle_download_failure(self, error_msg):
        """处理下载失败"""
        # 构建详细的错误信息
        detailed_error = f"""Unable to download the server core:

Error Message: {error_msg}

Please check:
1. Whether the network connection is normal
2. Whether the download address is valid
3. Whether there is enough disk space
4. The settings of your firewall or security software

Server Information:
- Type: {self.server_data['core_type']}
- Version: {self.server_data['core_version']}
- Download URL: {self.server_data.get('core_url', 'N/A')}"""
        
        messagebox.showerror("Download failed", detailed_error)
        
        # 清理失败的文件
        if 'server_dir' in locals():
            server_dir = Path(self.server_data['path']) / self.server_data['name']
            self._cleanup_failed_creation(server_dir)
    
    def _cleanup_failed_creation(self, server_dir):
        """清理创建失败的服务器目录"""
        try:
            if server_dir.exists():
                # 只删除下载的核心文件，保留其他可能的手动文件
                for jar_file in server_dir.glob("*.jar"):
                    try:
                        jar_file.unlink()
                    except:
                        pass
                # 删除配置文件
                for config_file in server_dir.glob("*.json"):
                    try:
                        config_file.unlink()
                    except:
                        pass
        except Exception as e:
            print(f"Cleanup failed: {e}")


class MinecraftServerManager:
    def __init__(self, root):
            self.root = root
            self.root.title("Minecraft Server Manager v1.1")
            self.root.geometry("800x600")
            
            # 图标设置
            icon_path = r"download.ico"
            try:
                self.root.iconbitmap(icon_path)
            except Exception as e:
                messagebox.showerror("Error", f"Error:{e}。If you see this error in the .exe application, please contact the developer as soon as possible!")
            
            # 配置目录和文件
            self.msm_dir = Path.home() / ".msm"
            self.msm_dir.mkdir(exist_ok=True)
            self.config_file = self.msm_dir / "MSM.ini"
            
            # 配置解析器
            self.config = configparser.ConfigParser()
            
            # 安全地读取配置文件
            if self.config_file.exists():
                try:
                    self.config.read(self.config_file, encoding='utf-8')
                except Exception as e:
                    print(f"读取配置文件失败: {e}")
                    # 创建新的配置文件
                    self.config = configparser.ConfigParser()
            
            # UI初始化
            self.main_frame = ttk.Frame(root)
            self.main_frame.pack(fill=tk.BOTH, expand=True)
            
            self.notebook = ttk.Notebook(self.main_frame)
            self.notebook.pack(fill=tk.BOTH, expand=True)
            
            # 控制按钮区域
            control_frame = ttk.Frame(self.main_frame)
            control_frame.pack(fill=tk.X, pady=5)
            
            ttk.Button(
                control_frame,
                text="Create Server",
                command=self.show_server_wizard
            ).pack(side=tk.LEFT, padx=10)
            
            ttk.Button(
                control_frame,
                text="Add Server",
                command=self.add_existing_server
            ).pack(side=tk.LEFT, padx=10)
            
            # 初始化数据结构
            self.tabs = {}
            self.server_processes = {}
            
            # 安全地加载服务器
            try:
                self.load_servers()
            except Exception as e:
                print(f"An error occurred while loading the server: {e}")
                # 继续运行程序，只是无法加载已有服务器
            
            # 窗口关闭事件
            root.protocol("WM_DELETE_WINDOW", self.on_main_window_close)

    def on_main_window_close(self):
        """主窗口关闭事件处理"""
        # 检查是否有正在运行的服务器
        running_servers = [
            tab_id for tab_id, process in self.server_processes.items() 
            if process.poll() is None
        ]
        
        if running_servers:
            # 构建警告消息
            server_list = "\n".join(f"- {tab_id}" for tab_id in running_servers)
            message = (
                f"The following servers are still running：\n{server_list}\n\n"
                "现在退出将强制关闭这些服务器！\n"
                "Are you sure you want to continue?？"
            )
            
            # 弹出确认对话框
            if not messagebox.askyesno(
                "Confirm exit",
                message,
                icon='warning'
            ):
                return  # 用户取消退出
            
            # 强制停止所有服务器
            for tab_id in running_servers:
                try:
                    process = self.server_processes[tab_id]
                    process.kill()  # 强制终止
                    self.log_to_console(tab_id, "⚠️ The server has been forcibly terminated")
                except Exception as e:
                    self.log_to_console(tab_id, f"❌ Termination failed: {str(e)}")
        
        # 保存配置
        self.save_servers()
        
        # 销毁主窗口
        self.root.destroy()

    def add_existing_server(self):
        """添加已有服务器到列表（完全修复版）"""
        try:
            server_dir = filedialog.askdirectory(
                title="Select an existing server directory",
                initialdir=str(Path.home())
            )
            
            if not server_dir:
                return
                
            server_path = Path(server_dir)
            
            # 修复：验证路径是否存在
            if not server_path.exists():
                messagebox.showerror("Error", "The selected path does not exist")
                return
            
            # 修复：验证服务器目录
            if not self.validate_existing_server(server_path):
                messagebox.showerror(
                    "Error",
                    "Invalid server directory\n"
                    "The directory must contain at least one of the following files.:\n"
                    "- server.jar\n" 
                    "- start.bat\n"
                    "- Any .jar file (server core)"
                )
                return
                
            # 修复：检查是否已添加
            for tab_id, tab_data in self.tabs.items():
                existing_path = tab_data['path_var'].get()
                if existing_path and Path(existing_path) == server_path:
                    messagebox.showinfo("Info", "The server already exists in the list.")
                    self.notebook.select(tab_id)
                    return
            
            # 修复：安全地添加服务器
            tab_id = self.add_server_tab(str(server_path))
            if not tab_id:
                raise Exception("Unable to create server tab")
                
            # 修复：安全地选择标签页
            def safe_select():
                try:
                    if tab_id in self.tabs:
                        self.notebook.select(tab_id)
                        self.log_to_console(tab_id, f"✅ Existing server added: {server_path.name}")
                except Exception as e:
                    print(f"Failed to select the tab: {e}")
            
            self.root.after(100, lambda: self.safe_select_tab(tab_id))  # 延迟选择，确保标签页已创建
            
        except Exception as e:
            error_msg = f"Failed to add server: {str(e)}"
            print(error_msg)
            messagebox.showerror("Error", error_msg)
                
            server_path = Path(server_dir)
            
            # 修复：验证路径是否存在
            if not server_path.exists():
                messagebox.showerror("Error", "The selected path does not exist")
                return
            
            # 验证服务器目录结构
            if not self.validate_existing_server(server_path):
                messagebox.showerror(
                    "Error",
                    "Invalid server directory\n"
                    "Must include one of the following documents:\n"
                    "- server.jar\n"
                    "- start.bat\n"
                    "Or contains valid server core files"
                )
                return
                
            # 添加服务器标签页
            try:
                tab_id = self.add_server_tab(str(server_path))
                if tab_id:
                    self.notebook.select(tab_id)
                    self.log_to_console(tab_id, f"✅ Existing server added: {server_path}")
                else:
                    messagebox.showerror("Error", "Failed to add server")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add server: {str(e)}")
        
    def validate_existing_server(self, server_path):
        """验证服务器目录是否有效"""
        # 首先检查路径是否存在
        if not server_path.exists():
            return False
        
        # 检查是否存在任一必需文件
        required_files = [
            server_path / "server.jar",
            server_path / "start.bat"
        ]
        
        # 检查是否有任何JAR文件（可能是服务器核心）
        jar_files = list(server_path.glob("*.jar"))
        
        # 如果目录中有JAR文件，也认为是有效的服务器目录
        if jar_files:
            return True
        
        # 检查是否存在必需文件
        return any(f.exists() for f in required_files)
        
    def validate_existing_server(self, server_path):
        """验证服务器目录是否有效"""
        # 首先检查路径是否存在
        if not server_path.exists():
            return False
        
        # 检查是否存在任一必需文件
        required_files = [
            server_path / "server.jar",
            server_path / "start.bat"
        ]
        
        # 检查是否有任何JAR文件（可能是服务器核心）
        jar_files = list(server_path.glob("*.jar"))
        
        # 如果目录中有JAR文件，也认为是有效的服务器目录
        if jar_files:
            return True
        
        # 检查是否存在必需文件
        return any(f.exists() for f in required_files)

    # 以下保持原有代码不变...
    def safe_select_tab(self, tab_id):
        """安全选择标签页（防止Invalid slave specification错误）"""
        try:
            # 检查标签页是否存在且有效
            if (tab_id in self.tabs and 
                hasattr(self.tabs[tab_id], 'frame') and 
                self.tabs[tab_id]['frame'].winfo_exists()):
                
                self.notebook.select(tab_id)
                return True
            else:
                print(f"⚠️ Tab {tab_id} does not exist or has been destroyed")
                return False
        except Exception as e:
            print(f"❌ Failed to select tab: {str(e)}")
            return False
    
    def load_servers(self):
        """修复配置加载逻辑 - 容忍缺失的配置项"""
        try:
            if not self.config_file.exists():
                print("⚠️ Configuration file does not exist, skipping load")
                return
                
            # 重新读取配置文件
            config = configparser.ConfigParser()
            config.read(self.config_file, encoding='utf-8')
            
            if 'Servers' not in config:
                print("⚠️ There is no 'Servers' section in the configuration file.")
                return
                
            servers_loaded = 0
            servers_skipped = 0
            
            # 修复：收集所有server_开头的键
            server_keys = [key for key in config['Servers'] if key.startswith('server_')]
            
            if not server_keys:
                print("⚠️ No valid server configuration found")
                return
            
            # 按数字排序处理
            server_keys.sort(key=lambda x: int(x.split('_')[1]) if '_' in x and x.split('_')[1].isdigit() else 0)
            
            for key in server_keys:
                path = config['Servers'][key]
                if not path or not Path(path).exists():
                    print(f"⚠️ Path does not exist, skipping {key}: {path}")
                    servers_skipped += 1
                    continue
                    
                try:
                    tab_id = self.add_server_tab(path)
                    if tab_id:
                        servers_loaded += 1
                        print(f"✅ Load Server: {key} -> {Path(path).name}")
                    else:
                        servers_skipped += 1
                        print(f"❌ Failed to create tab: {key}")
                except Exception as e:
                    servers_skipped += 1
                    print(f"❌ Failed to load server {key}: {str(e)}")
            
            print(f"📊 Server load complete: {servers_loaded} complete, {servers_skipped} failed")
            
        except Exception as e:
            print(f"❌ Failed to load configuration: {str(e)}")
            # 不中断程序运行，继续启动

    def save_servers(self):
        """修复配置保存逻辑 - 避免竞态条件删除"""
        try:
            # 确保配置目录存在
            self.msm_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建新的配置对象
            new_config = configparser.ConfigParser()
            new_config['Servers'] = {}
            
            # 安全地保存所有有效的服务器
            valid_servers = 0
            for i, (tab_id, tab_data) in enumerate(self.tabs.items()):
                path = tab_data['path_var'].get()
                if path and Path(path).exists():
                    new_config['Servers'][f'server_{i}'] = path
                    valid_servers += 1
            
            # 使用临时文件确保原子性写入
            temp_file = self.config_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                new_config.write(f)
            
            # 原子性替换
            if self.config_file.exists():
                self.config_file.unlink()
            temp_file.rename(self.config_file)
            
            print(f"✅ Saved {valid_servers} server configurations")
            
        except Exception as e:
            print(f"❌ 保存配置失败: {str(e)}")

    def show_server_wizard(self):
        """显示服务器创建向导"""
        ServerCreationWizard(self.root, self.handle_server_creation)

    def handle_server_creation(self, server_data):
        """处理新服务器创建请求（修复版）"""
        def worker():
            tab_id = None
            try:
                # 准备路径
                server_dir = Path(server_data['path']) / server_data['name']
                
                # 修复：确保目录存在
                server_dir.mkdir(parents=True, exist_ok=True)
                
                # 在主线程创建标签页
                def create_tab():
                    nonlocal tab_id
                    try:
                        tab_id = self.add_server_tab(str(server_dir))
                        # 修复：检查标签页是否成功创建
                        if tab_id and tab_id in self.tabs:
                            self.notebook.select(tab_id)
                            self.log_to_console(tab_id, f"✅ Server tab created successfully: {tab_id}")
                        else:
                            raise Exception("Failed to create tab")
                    except Exception as e:
                        raise Exception(f"Failed to create tab: {str(e)}")
                
                self.root.after(0, create_tab)
                
                # 等待标签页创建完成
                import time
                timeout = 5  # 5秒超时
                start_time = time.time()
                while tab_id is None and time.time() - start_time < timeout:
                    time.sleep(0.1)
                
                if tab_id is None:
                    raise Exception("Tab creation timed out")
                
                # 下载核心文件
                core_name = f"{server_data['core_type']}-{server_data['core_version']}.jar"
                self.root.after(0, lambda: self.log_to_console(tab_id, "Starting to download the server core..."))
                
                if not self.download_core(server_data['core_url'], str(server_dir / core_name)):
                    raise Exception("Core download failed")
                
                # 保存启动脚本
                bat_path = server_dir / "start.bat"
                script_content = server_data['custom_script'].replace(
                    "{core_name}", core_name
                )
                
                with open(bat_path, 'w', encoding='utf-8') as f:
                    f.write(script_content)
                
                self.log_to_console(tab_id, "The startup script has been generated")
                
                # 更新配置
                self.root.after(0, lambda: (
                    self.save_servers(),
                    self.log_to_console(tab_id, "✅ Server created successfully"),
                    messagebox.showinfo("Success", f"Server '{server_data['name']}' has been created!\nPath: {server_dir}")
                ))
                
            except Exception as e:
                error_msg = f"❌ Creation failed: {str(e)}"
                print(error_msg)
                
                # 清理残留文件
                if 'server_dir' in locals() and server_dir.exists():
                    try:
                        shutil.rmtree(server_dir, ignore_errors=True)
                    except:
                        pass
                
                # 在主线程显示错误
                def show_error():
                    if tab_id and tab_id in self.tabs:
                        self.log_to_console(tab_id, error_msg)
                    messagebox.showerror("Error", f"Server creation failed:\n{str(e)}")
                
                self.root.after(0, show_error)
        
        # 启动工作线程
        threading.Thread(target=worker, daemon=True).start()

    def download_core(self, url, save_path):
        """下载服务器核心文件（修复版，增加完整性检查）"""
        try:
            # 创建临时文件
            temp_path = f"{save_path}.tmp"
            
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            # 确保目录存在
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
            
            # 修复：验证文件完整性
            if not self.validate_jar_file(temp_path):
                raise Exception("The downloaded file is corrupted or is not a valid JAR file.")
            
            # 重命名临时文件
            os.replace(temp_path, save_path)
            
            # 修复：再次验证最终文件
            if not self.validate_jar_file(save_path):
                raise Exception("Final file verification failed")
            
            return True
            
        except Exception as e:
            # 清理临时文件
            if 'temp_path' in locals() and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            print(f"Download failed: {str(e)}")
            return False

    def validate_jar_file(self, file_path):
        """验证JAR文件是否有效"""
        try:
            if not os.path.exists(file_path):
                return False
            
            file_size = os.path.getsize(file_path)
            if file_size < 1024:  # 小于1KB的文件肯定无效
                return False
            
            # 检查文件头（JAR文件以PK开头）
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if header[:2] != b'PK':
                    return False
            
            return True
        except Exception:
            return False

    def edit_start_script(self, tab_id):
        """编辑服务器的启动脚本"""
        if tab_id not in self.tabs:
            return
            
        # 获取服务器路径
        server_path = self.tabs[tab_id]['path_var'].get()
        if not server_path or not os.path.exists(server_path):
            messagebox.showerror("Error", "The server path does not exist")
            return
            
        # 启动脚本路径
        script_path = os.path.join(server_path, "start.bat")
        
        # 读取现有脚本内容
        script_content = ""
        if os.path.exists(script_path):
            try:
                with open(script_path, 'r', encoding='utf-8') as f:
                    script_content = f.read()
            except Exception as e:
                messagebox.showerror("Error", f"Unable to read the startup script: {str(e)}")
                return
        
        # 创建编辑窗口
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"Edit startup script - {tab_id}")
        edit_window.geometry("600x400")
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(edit_window)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 文本编辑区域
        text_widget = tk.Text(
            edit_window,
            yscrollcommand=scrollbar.set,
            wrap=tk.WORD,
            undo=True
        )
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.config(command=text_widget.yview)
        
        # 插入现有内容
        text_widget.insert(tk.END, script_content)
        
        # 按钮区域
        btn_frame = ttk.Frame(edit_window)
        btn_frame.pack(fill=tk.X, pady=10, padx=10)
        
        def save_script():
            """保存编辑后的脚本"""
            try:
                new_content = text_widget.get("1.0", tk.END)
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                messagebox.showinfo("Success", "The startup script has been saved")
                edit_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Save failed: {str(e)}")
        
        ttk.Button(btn_frame, text="Save", command=save_script).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=edit_window.destroy).pack(side=tk.RIGHT)

    def start_resource_monitor(self, tab_id):
        """启动资源监控窗口"""
        if tab_id not in self.server_processes:
            messagebox.showinfo("Info", "Please start the server first.")
            return
            
        process = self.server_processes[tab_id]
        if process.poll() is not None:
            messagebox.showinfo("Info", "The server is not running")
            return
            
        # 创建并显示监控窗口
        self.resource_monitor = ResourceMonitorWindow(
            self.root,
            tab_id,
            process.pid
        )

    def check_and_accept_eula(self, tab_id):
        """检测并处理Minecraft EULA同意情况"""
        if tab_id not in self.tabs:
            messagebox.showerror("Error", "The server tab does not exist")
            return
        
        # 获取服务器路径
        server_path = Path(self.tabs[tab_id]['path_var'].get())
        if not server_path.exists():
            messagebox.showerror("Error", "The server path does not exist")
            return
        
        # 检查EULA文件
        eula_path = server_path / "eula.txt"
        
        try:
            # 检查EULA文件是否存在
            if not eula_path.exists():
                self._handle_missing_eula(tab_id, eula_path)
                return
            
            # 读取EULA文件内容
            with open(eula_path, 'r', encoding='utf-8') as f:
                eula_content = f.read()
            
            # 检查是否已同意EULA
            if 'eula=true' in eula_content.lower():
                messagebox.showinfo("EULA Status", "✅ Minecraft EULA has been agreed")
            elif 'eula=false' in eula_content.lower():
                self._handle_unaccepted_eula(tab_id, eula_path)
            else:
                # EULA文件格式异常
                self._handle_corrupted_eula(tab_id, eula_path)
                
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while checking the EULA:\n{str(e)}")

    def _handle_missing_eula(self, tab_id, eula_path):
        """处理缺失EULA文件的情况"""
        server_name = tab_id
        
        # 显示EULA内容预览
        eula_text = self._get_eula_content()
        
        result = messagebox.askyesno(
            "Minecraft EULA Agreement",
            f"The server '{server_name}' did not find the EULA file.\n\n"
            f"Minecraft servers require you to agree to the Minecraft EULA in order to run.\n\n"
            f"Preview of the main contents of the EULA:\n"
            f"• You agree to comply with the Minecraft End User License Agreement\n"
            f"• You are responsible for the operation and use of the server.\n"
            f"• Prohibited from running unauthorized commercial servers\n\n"
            f"Please refer to the full EULA: https://aka.ms/MinecraftEULA\n\n"
            f"Whether to agree to the Minecraft EULA and create the eula.txt file？",
            icon='question'
        )
        
        if result:
            self._create_eula_file(eula_path, True)
            self.log_to_console(tab_id, "✅ Minecraft EULA has been agreed")
            messagebox.showinfo("Success", "The EULA file has been created and set to agreed.")
        else:
            self.log_to_console(tab_id, "❌ The user has not agreed to the Minecraft EULA")

    def _handle_unaccepted_eula(self, tab_id, eula_path):
        """处理未同意EULA的情况"""
        server_name = tab_id
        
        result = messagebox.askyesno(
            "Minecraft EULA Agreement",
            f"The EULA for server '{server_name}' has not been agreed to.\n\n"
            f"Current status: eula=false\n\n"
            "Minecraft servers require you to agree to the EULA in order to run properly.\n\n"
            "Do you agree to the Minecraft EULA now？",
            icon='warning'
        )
        
        if result:
            self._create_eula_file(eula_path, True)
            self.log_to_console(tab_id, "✅ Minecraft EULA has been agreed")
            messagebox.showinfo("Success", "The EULA has been updated to an agreed status")
        else:
            self.log_to_console(tab_id, "⚠️ The EULA remains in an unaccepted state.")

    def _handle_corrupted_eula(self, tab_id, eula_path):
        """处理损坏的EULA文件"""
        server_name = tab_id
        
        result = messagebox.askyesno(
            "EULA file error",
            f"The EULA file format of the server '{server_name}' is abnormal.\n\n"
            "Whether to recreate the EULA file and set it to agreed？",
            icon='error'
        )
        
        if result:
            self._create_eula_file(eula_path, True)
            self.log_to_console(tab_id, "✅ Repaired and agreed to the EULA")
            messagebox.showinfo("Success", "The EULA file has been repaired")
        else:
            # 备份原文件
            backup_path = eula_path.with_suffix('.txt.bak')
            try:
                shutil.copy2(eula_path, backup_path)
                self.log_to_console(tab_id, f"⚠️ The original EULA file has been backed up to: {backup_path.name}")
            except:
                pass

    def _get_eula_content(self):
        """获取EULA内容摘要"""
        return """#Minecraft EULA Summary
    • You must comply with the Minecraft End User License Agreement.
    • You are fully responsible for the operation and use of the server.
    • Prohibited from running unauthorized commercial servers
    • You must comply with Mojang's business model guidelines.

    Please refer to the full EULA content: https://aka.ms/MinecraftEULA"""

    def _create_eula_file(self, eula_path, accepted=True):
        """创建或更新EULA文件"""
        eula_content = f"""#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://aka.ms/MinecraftEULA).
    #{datetime.datetime.now().strftime('%a %b %d %H:%M:%S %Z %Y')}
    eula={str(accepted).lower()}
    """
        
        # 确保目录存在
        eula_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入EULA文件
        with open(eula_path, 'w', encoding='utf-8') as f:
            f.write(eula_content)

    def auto_check_eula_on_start(self, tab_id):
        """启动服务器时自动检查EULA（在start_server方法中调用）"""
        server_path = Path(self.tabs[tab_id]['path_var'].get())
        eula_path = server_path / "eula.txt"
        
        # 检查EULA是否存在且已同意
        if eula_path.exists():
            try:
                with open(eula_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'eula=true' in content.lower():
                        return True  # EULA已同意，可以启动
            except:
                pass
        
        # EULA未同意，提示用户
        self.root.after(0, lambda: self._prompt_eula_before_start(tab_id))
        return False

    def _prompt_eula_before_start(self, tab_id):
        """启动前提示EULA同意"""
        server_name = tab_id
        server_path = Path(self.tabs[tab_id]['path_var'].get())
        eula_path = server_path / "eula.txt"
        
        result = messagebox.askyesno(
            "Minecraft EULA Agreement",
            f"Starting the server '{server_name}' requires agreeing to the Minecraft EULA.\n\n"
            "Do you want to agree to the EULA now and start the server?？",
            icon='question'
        )
        
        if result:
            self._create_eula_file(eula_path, True)
            self.log_to_console(tab_id, "✅ Minecraft EULA has been agreed")
            # 延迟启动服务器，确保EULA文件已写入
            self.root.after(100, lambda: self._delayed_start_server(tab_id))
        else:
            self.log_to_console(tab_id, "❌ Launch canceled: Minecraft EULA not agreed")

    def _delayed_start_server(self, tab_id):
        """延迟启动服务器（确保EULA文件已保存）"""
        self.start_server(tab_id)

    def add_server_tab(self, initial_path=None):
        """添加新的服务器标签页（修复版）"""
        try:
            # 生成唯一ID
            tab_id = f"server_{len(self.tabs)}"
                
            # 修复：检查路径有效性
            if initial_path and not Path(initial_path).exists():
                # 创建目录
                Path(initial_path).mkdir(parents=True, exist_ok=True)
                
            tab_frame = ttk.Frame(self.notebook)
            display_name = Path(initial_path).name if initial_path else "New Server"
                
            # 修复：确保标签页名称不为空
            if not display_name or display_name == ".":
                display_name = "New Server"
                    
            self.notebook.add(tab_frame, text=display_name)
                
            # 路径变量
            path_var = tk.StringVar(value=initial_path or "")
            path_var.trace_add('write', lambda *args: self.save_servers())
                
            # 控制按钮区域
            control_frame = ttk.Frame(tab_frame)
            control_frame.pack(fill=tk.X, pady=5, padx=5)
            
            # 启动按钮
            start_btn = ttk.Button(
                control_frame,
                text="Start",
                command=lambda: self.start_server(tab_id)
            )
            start_btn.pack(side=tk.LEFT, padx=2)
            
            # 停止按钮
            stop_btn = ttk.Button(
                control_frame,
                text="Stop",
                command=lambda: self.stop_server(tab_id),
                state=tk.DISABLED
            )
            stop_btn.pack(side=tk.LEFT, padx=2)
            
            # 重启按钮
            restart_btn = ttk.Button(
                control_frame,
                text="Restart",
                command=lambda: self.restart_server(tab_id),
                state=tk.DISABLED
            )
            restart_btn.pack(side=tk.LEFT, padx=2)
            
            # 编辑server.properties按钮
            edit_prop_btn = ttk.Button(
                control_frame,
                text="Edit server.properties",
                command=lambda: self.edit_server_properties(tab_id)
            )
            edit_prop_btn.pack(side=tk.LEFT, padx=2)
            # 编辑启动脚本按钮
            edit_script_btn = ttk.Button(
                control_frame,
                text="Edit startup script",
                command=lambda: self.edit_start_script(tab_id)
            )
            edit_script_btn.pack(side=tk.LEFT, padx=5)
            # 监控资源按钮
            ttk.Button(
                control_frame,
                text="Monitoring resources",
                command=lambda: self.start_resource_monitor(tab_id)
            ).pack(side=tk.LEFT, padx=5)
            # EULA
            ttk.Button(
                control_frame,
                text="EULA",
                command=lambda: self.check_and_accept_eula(tab_id)
            ).pack(side=tk.LEFT, padx=5)
            # 帮助按钮
            ttk.Button(
                control_frame,
                text="Help...",
                command=lambda: webbrowser.open("http://xg-2.frp.one:12935")
            ).pack(side=tk.RIGHT, padx=5)
            
            # 路径显示与浏览
            path_frame = ttk.Frame(tab_frame)
            path_frame.pack(fill=tk.X, padx=5)
            
            ttk.Label(path_frame, text="Server Path:").pack(side=tk.LEFT)
            path_entry = ttk.Entry(path_frame, textvariable=path_var)
            path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            ttk.Button(
                path_frame,
                text="Browse",
                command=lambda: self.browse_server_path(tab_id)
            ).pack(side=tk.RIGHT, padx=5)
            
            # 日志区域
            log_frame = ttk.LabelFrame(tab_frame, text="Console output")
            log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            log_scrollbar = ttk.Scrollbar(log_frame)
            log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            log_text = tk.Text(
                log_frame,
                wrap=tk.WORD,
                yscrollcommand=log_scrollbar.set,
                state=tk.DISABLED,
                bg="#1a1a1a",
                fg="#ffffff",
                insertbackground="#ffffff"
            )
            log_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
            log_scrollbar.config(command=log_text.yview)
            
            # 指令输入区域
            command_frame = ttk.Frame(tab_frame)
            command_frame.pack(fill=tk.X, padx=5, pady=5)
            
            ttk.Label(command_frame, text="Command:").pack(side=tk.LEFT, padx=5)
            command_var = tk.StringVar()
            command_entry = ttk.Entry(command_frame, textvariable=command_var)
            command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            # 发送指令按钮
            send_btn = ttk.Button(
                command_frame,
                text="Send",
                command=lambda: self.send_command(tab_id)
            )
            send_btn.pack(side=tk.RIGHT, padx=5)
            
            # 绑定回车键发送指令
            command_entry.bind('<Return>', lambda event: self.send_command(tab_id))
            
            # 保存标签数据
            self.tabs[tab_id] = {
                'frame': tab_frame,
                'path_var': path_var,
                'start_btn': start_btn,
                'stop_btn': stop_btn,
                'restart_btn': restart_btn,
                'log_text': log_text,
                'command_var': command_var,
                'status_var': tk.StringVar(value="已停止")
            }
            
            # 立即保存配置
            self.save_servers()
            
            return tab_id
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create tab: {str(e)}")
            return None

    def browse_server_path(self, tab_id):
        """浏览服务器路径"""
        current_path = self.tabs[tab_id]['path_var'].get() or str(Path.home())
        path = filedialog.askdirectory(initialdir=current_path)
        if path:
            self.tabs[tab_id]['path_var'].set(path)
            # 更新标签页名称
            self.notebook.tab(
                self.tabs[tab_id]['frame'],
                text=Path(path).name
            )

    def start_server(self, tab_id):
        """启动服务器"""
        tab_data = self.tabs.get(tab_id)
        if not tab_data:
            return
            
        server_path = Path(tab_data['path_var'].get())
        if not server_path.exists():
            messagebox.showerror("Error", "The server path does not exist")
            return
            
        # 检查是否已有进程在运行
        if tab_id in self.server_processes and self.server_processes[tab_id].poll() is None:
            messagebox.showwarning("Warning", "The server is already running.")
            return
            
        # 查找启动脚本或核心文件
        start_script = server_path / "start.bat"
        core_files = list(server_path.glob("*.jar"))
        
        if start_script.exists():
            # 使用启动脚本
            cmd = str(start_script)
            cwd = str(server_path)
        elif core_files:
            # 使用找到的第一个JAR文件
            cmd = f'java -jar "{core_files[0].name}"'
            cwd = str(server_path)
        else:
            messagebox.showerror("Error", "Startup script or core file not found")
            return
            
        # 更新按钮状态
        tab_data['start_btn']['state'] = tk.DISABLED
        tab_data['stop_btn']['state'] = tk.NORMAL
        tab_data['restart_btn']['state'] = tk.NORMAL
        
        # 启动服务器进程
        try:
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                shell=True,
                text=True
            )
            
            self.server_processes[tab_id] = process
            self.log_to_console(tab_id, f"✅ The server has started: {cmd}")
            
            # 启动输出监控线程
            threading.Thread(
                target=self.monitor_server_output,
                args=(tab_id, process),
                daemon=True
            ).start()
            
        except Exception as e:
            self.log_to_console(tab_id, f"❌ Startup failed: {str(e)}")
            tab_data['start_btn']['state'] = tk.NORMAL
            tab_data['stop_btn']['state'] = tk.DISABLED
            tab_data['restart_btn']['state'] = tk.DISABLED

    def stop_server(self, tab_id):
        """停止服务器"""
        tab_data = self.tabs.get(tab_id)
        if not tab_data:
            return
            
        process = self.server_processes.get(tab_id)
        if not process or process.poll() is not None:
            messagebox.showinfo("Info", "The server is not running")
            return
            
        try:
            # 尝试优雅关闭
            self.log_to_console(tab_id, "⚠️ Stopping server...")
            process.stdin.write("stop\n")
            process.stdin.flush()
            
            # 等待关闭
            timeout = 10
            start_time = time.time()
            while process.poll() is None and time.time() - start_time < timeout:
                time.sleep(0.5)
                
            # 如果仍在运行则强制关闭
            if process.poll() is None:
                self.log_to_console(tab_id, "⚠️ The server is unresponsive and is being forcibly shut down...")
                process.kill()
                
            self.log_to_console(tab_id, f"✅ Server has stopped")
            
        except Exception as e:
            self.log_to_console(tab_id, f"❌ Stop failing: {str(e)}")
            
        finally:
            # 更新按钮状态
            tab_data['start_btn']['state'] = tk.NORMAL
            tab_data['stop_btn']['state'] = tk.DISABLED
            tab_data['restart_btn']['state'] = tk.DISABLED

    def restart_server(self, tab_id):
        """重启服务器"""
        def worker():
            self.stop_server(tab_id)
            # 等待一小段时间确保服务器已完全停止
            time.sleep(2)
            self.start_server(tab_id)
            
        threading.Thread(target=worker, daemon=True).start()

    def send_command(self, tab_id):
        """发送指令到服务器"""
        tab_data = self.tabs.get(tab_id)
        if not tab_data:
            return
            
        process = self.server_processes.get(tab_id)
        if not process or process.poll() is not None:
            messagebox.showinfo("Info", "Pelese start the server first.")
            return
            
        command = tab_data['command_var'].get().strip()
        if not command:
            return
            
        try:
            # 发送指令到服务器
            process.stdin.write(f"{command}\n")
            process.stdin.flush()
            self.log_to_console(tab_id, f">>> {command}")
            
            # 清空输入框
            tab_data['command_var'].set("")
        except Exception as e:
            self.log_to_console(tab_id, f"❌ Failed to send command: {str(e)}")

    def monitor_server_output(self, tab_id, process):
        """监控服务器输出并显示到日志区域"""
        while True:
            output = process.stdout.readline()
            if not output and process.poll() is not None:
                break
                
            if output:
                # 清理ANSI代码并添加时间戳
                clean_output = clean_ansi_codes(output.strip())
                timestamp = time.strftime("[%H:%M:%S]")
                self.log_to_console(tab_id, f"{timestamp} {clean_output}")
                
        # 进程结束后更新状态
        exit_code = process.poll()
        self.log_to_console(tab_id, f"💡 The server has exited, exit code: {exit_code}")
        tab_data = self.tabs.get(tab_id)
        if tab_data:
            self.root.after(0, lambda: (
                tab_data['start_btn'].config(state=tk.NORMAL),
                tab_data['stop_btn'].config(state=tk.DISABLED),
                tab_data['restart_btn'].config(state=tk.DISABLED)
            ))

    def log_to_console(self, tab_id, message):
        """将消息添加到控制台日志"""
        tab_data = self.tabs.get(tab_id)
        if not tab_data:
            return
            
        log_text = tab_data['log_text']
        self.root.after(0, lambda: (
            log_text.config(state=tk.NORMAL),
            log_text.insert(tk.END, message + "\n"),
            log_text.see(tk.END),
            log_text.config(state=tk.DISABLED)
        ))

    def edit_server_properties(self, tab_id):
        """编辑服务器的server.properties文件"""
        tab_data = self.tabs.get(tab_id)
        if not tab_data:
            return
            
        server_path = Path(tab_data['path_var'].get())
        properties_path = server_path / "server.properties"
        
        # 检查文件是否存在，如果不存在则创建默认文件
        if not properties_path.exists():
            if not self.create_default_properties(properties_path):
                messagebox.showerror("Error", "Cannot create server.properties file")
                return
        
        # 读取文件内容
        try:
            with open(properties_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"Unable to read file: {str(e)}")
            return
        
        # 创建编辑窗口
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"Edit the server.properties of {tab_id}")
        edit_window.geometry("800x600")
        edit_window.minsize(600, 400)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(edit_window)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 文本编辑区域
        text_widget = tk.Text(edit_window, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=text_widget.yview)
        
        # 插入文件内容
        text_widget.insert(tk.END, content)
        
        # 保存按钮
        def save_properties():
            try:
                new_content = text_widget.get(1.0, tk.END)
                with open(properties_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                messagebox.showinfo("Success", "server.properties has been saved")
                edit_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Save failed: {str(e)}")
        
        # 按钮区域
        btn_frame = ttk.Frame(edit_window)
        btn_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Button(btn_frame, text="Save", command=save_properties).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=edit_window.destroy).pack(side=tk.RIGHT)

    def create_default_properties(self, file_path):
        """创建默认的server.properties文件"""
        try:
            default_content = """#Minecraft server properties
#Thu Jan 01 00:00:00 UTC 2024
spawn-protection=16
max-tick-time=60000
query.port=25565
generator-settings=
force-gamemode=false
allow-nether=true
enforce-whitelist=false
gamemode=survival
broadcast-console-to-ops=true
enable-query=false
player-idle-timeout=0
difficulty=easy
spawn-monsters=true
broadcast-rcon-to-ops=true
op-permission-level=4
pvp=true
snooper-enabled=true
level-type=default
hardcore=false
enable-command-block=false
max-players=20
network-compression-threshold=256
resource-pack-sha1=
max-world-size=29999984
server-port=25565
server-ip=
spawn-npcs=true
allow-flight=false
level-name=world
view-distance=10
resource-pack=
spawn-animals=true
white-list=false
rcon.port=25575
debug=false
force-resource-pack=false
motd=A Minecraft Server
rcon.password=
enable-rcon=false
"""
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(default_content)
            return True
        except Exception as e:
            print(f"Failed to create the default properties file: {e}")
            return False

if __name__ == "__main__":
    root = tk.Tk()
    app = MinecraftServerManager(root)
    root.mainloop()

#add_existing_server