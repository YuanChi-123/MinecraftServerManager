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
        self.window.title(f"服务器资源监控 - {server_tab_id}")
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
        
        ttk.Label(self.status_frame, text="CPU使用率:").pack(side=tk.LEFT, padx=5)
        self.cpu_label = ttk.Label(self.status_frame, text="0%")
        self.cpu_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(self.status_frame, text="内存使用率:").pack(side=tk.LEFT, padx=5)
        self.memory_label = ttk.Label(self.status_frame, text="0%")
        self.memory_label.pack(side=tk.LEFT, padx=5)
        
        # 图表画布
        self.canvas_frame = ttk.LabelFrame(self.window, text="资源使用趋势")
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 控制按钮
        self.btn_frame = ttk.Frame(self.window)
        self.btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(
            self.btn_frame,
            text="刷新",
            command=self.force_refresh
        ).pack(side=tk.RIGHT, padx=5)

    def monitor_resources(self):
        """监控服务器资源使用情况的线程函数"""
        try:
            self.process = psutil.Process(self.pid)
        except psutil.NoSuchProcess:
            self.window.after(0, lambda: self.show_error("无法找到进程，可能已终止"))
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
                self.window.after(0, lambda: self.show_error(f"监控错误: {str(e)}"))
                break
            except Exception as e:
                # 捕获其他可能的异常
                if self.running:
                    print(f"监控线程异常: {str(e)}")
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
                self.show_error(f"刷新失败: {str(e)}")

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
                            raise Exception("下载被用户取消")
                            
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

class ServerCreationWizard:
    def __init__(self, parent, callback):
        self.parent = parent
        self.callback = callback
        self.download_manager = DownloadManager(parent)
        
        # 创建向导窗口
        self.window = tk.Toplevel(parent)
        self.window.title("创建新服务器")
        self.window.geometry("550x550")
        self.window.resizable(False, False)
        
        # 主框架
        self.main_frame = ttk.Frame(self.window)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # 内容区域（带滚动条）
        self.canvas = tk.Canvas(self.main_frame, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # 配置滚动区域
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # 布局
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # 存储服务器数据
        self.server_data = {
            'name': '我的服务器',
            'path': str(Path.home() / "servers"),
            'core_type': 'Paper',
            'core_version': '1.20.1',
            'java_path': 'java',
            'xmx': '2G',
            'xms': '1G',
            'custom_script': None,
            'core_url': None
        }
        
        # 核心版本数据
        self.core_versions = {
            "Paper": {
                "1.20.1": "https://api.papermc.io/v2/projects/paper/versions/1.20.1/builds/177/downloads/paper-1.20.1-177.jar",
                "1.19.4": "https://api.papermc.io/v2/projects/paper/versions/1.19.4/builds/550/downloads/paper-1.19.4-550.jar"
            },
            "Spigot": {
                "1.20.1": "https://cdn.getbukkit.org/spigot/spigot-1.20.1.jar"
            }
        }
        
        # 创建表单控件
        self.create_basic_info_form()
        
        # 控制按钮区域
        self.create_control_buttons()
        
        # 自动检测Java路径
        self.window.after(100, self.auto_detect_java)

        self.window.protocol("WM_DELETE_WINDOW", self.on_window_close)
        self.server_process = None

    def on_window_close(self):
        """窗口关闭事件处理"""
        if self.server_process and self.server_process.poll() is None:
            if messagebox.askyesno(
                "确认关闭",
                "服务器仍在运行，关闭窗口将停止服务器。确定要继续吗？",
                icon='warning'
            ):
                self.stop_server()
            else:
                return  # 用户取消关闭
            
            self.window.destroy()

    def create_basic_info_form(self):
        """创建完整的基本信息表单"""
        # 服务器名称
        ttk.Label(self.scrollable_frame, text="服务器名称:").grid(
            row=0, column=0, sticky="w", pady=(10, 0), padx=10
        )
        self.name_var = tk.StringVar(value=self.server_data['name'])
        ttk.Entry(self.scrollable_frame, textvariable=self.name_var, width=40).grid(
            row=1, column=0, sticky="ew", padx=10, pady=(0, 10)
        )
        
        # 服务器路径
        path_frame = ttk.Frame(self.scrollable_frame)
        path_frame.grid(row=2, column=0, sticky="ew", padx=10)
        
        ttk.Label(path_frame, text="服务器路径:").pack(side="left")
        self.path_var = tk.StringVar(value=self.server_data['path'])
        ttk.Entry(path_frame, textvariable=self.path_var).pack(
            side="left", fill="x", expand=True, padx=5
        )
        ttk.Button(
            path_frame,
            text="浏览",
            command=self.browse_server_path,
            width=8
        ).pack(side="right")
        
        # 服务器核心
        core_frame = ttk.Frame(self.scrollable_frame)
        core_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(10, 0))
        
        ttk.Label(core_frame, text="核心类型:").pack(side="left")
        self.core_type_var = tk.StringVar(value=self.server_data['core_type'])
        ttk.Combobox(
            core_frame,
            textvariable=self.core_type_var,
            values=list(self.core_versions.keys()),
            state="readonly",
            width=10
        ).pack(side="left", padx=5)
        
        ttk.Label(core_frame, text="版本:").pack(side="left", padx=(10, 0))
        self.core_version_var = tk.StringVar(value=self.server_data['core_version'])
        self.version_combobox = ttk.Combobox(
            core_frame,
            textvariable=self.core_version_var,
            state="readonly",
            width=10
        )
        self.version_combobox.pack(side="left")
        
        # Java路径
        java_frame = ttk.Frame(self.scrollable_frame)
        java_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=(10, 0))
        
        ttk.Label(java_frame, text="Java路径:").pack(side="left")
        self.java_var = tk.StringVar(value=self.server_data['java_path'])
        ttk.Entry(java_frame, textvariable=self.java_var).pack(
            side="left", fill="x", expand=True, padx=5
        )
        ttk.Button(
            java_frame,
            text="浏览",
            command=self.browse_java_path,
            width=8
        ).pack(side="right")
        
        # 内存设置
        mem_frame = ttk.Frame(self.scrollable_frame)
        mem_frame.grid(row=5, column=0, sticky="ew", padx=10, pady=(10, 0))
        
        ttk.Label(mem_frame, text="内存设置:").pack(side="left")
        ttk.Label(mem_frame, text="Xms:").pack(side="left", padx=(10, 0))
        self.xms_var = tk.StringVar(value=self.server_data['xms'])
        ttk.Entry(mem_frame, textvariable=self.xms_var, width=8).pack(side="left")
        
        ttk.Label(mem_frame, text="Xmx:").pack(side="left", padx=(10, 0))
        self.xmx_var = tk.StringVar(value=self.server_data['xmx'])
        ttk.Entry(mem_frame, textvariable=self.xmx_var, width=8).pack(side="left")
        
        # 高级配置按钮
        ttk.Button(
            self.scrollable_frame,
            text="高级配置...",
            command=self.show_advanced_settings
        ).grid(row=6, column=0, pady=20)
        
        # 配置网格权重
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        
        # 绑定核心类型变化事件
        self.core_type_var.trace_add('write', self.update_core_versions)
        self.update_core_versions()

    def create_control_buttons(self):
        """创建垂直排列的控制按钮"""
        # 主按钮框架
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill="x", pady=(20, 10))
        
        # 使用内部框架实现垂直布局
        inner_frame = ttk.Frame(btn_frame)
        inner_frame.pack(side="right", padx=20)
        
        # 取消按钮在上
        ttk.Button(
            inner_frame,
            text="取消",
            command=self.window.destroy
        ).pack(pady=(0, 5), fill="x")  # 添加下方间距
        
        # 创建按钮在下
        ttk.Button(
            inner_frame,
            text="创建",
            command=self.finish_creation
        ).pack(fill="x")  # 填充水平空间

    def browse_server_path(self):
        """浏览服务器路径"""
        path = filedialog.askdirectory(
            title="选择服务器存储位置",
            initialdir=self.path_var.get()
        )
        if path:
            self.path_var.set(path)

    def browse_java_path(self):
        """浏览Java路径"""
        path = filedialog.askopenfilename(
            title="选择Java可执行文件",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
        )
        if path:
            self.java_var.set(path)

    def update_core_versions(self, *args):
        """更新核心版本选项"""
        versions = list(self.core_versions[self.core_type_var.get()].keys())
        self.version_combobox['values'] = versions
        if self.core_version_var.get() not in versions:
            self.core_version_var.set(versions[0])

    def auto_detect_java(self):
        """自动检测Java路径"""
        try:
            # 检查JAVA_HOME环境变量
            if java_home := os.getenv('JAVA_HOME'):
                java_path = Path(java_home) / 'bin' / 'java'
                if os.name == 'nt':  # Windows系统
                    java_path = java_path.with_suffix('.exe')
                if java_path.exists():
                    self.java_var.set(str(java_path))
                    return
            
            # 通过系统PATH查找
            if java_path := shutil.which('java'):
                self.java_var.set(java_path)
        except Exception:
            pass

    def show_advanced_settings(self):
        """显示高级配置窗口"""
        adv_window = tk.Toplevel(self.window)
        adv_window.title("高级配置")
        adv_window.resizable(False, False)
        
        # 脚本编辑区域
        script_frame = ttk.LabelFrame(adv_window, text="自定义启动脚本 (start.bat)")
        script_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(script_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.script_text = tk.Text(
            script_frame,
            yscrollcommand=scrollbar.set,
            wrap="word",
            height=15,
            width=60
        )
        self.script_text.pack(fill="both", expand=True)
        scrollbar.config(command=self.script_text.yview)
        
        # 生成默认脚本
        default_script = (
            '@echo off\n'
            f'"{self.java_var.get()}" -Xmx{self.xmx_var.get()} '
            f'-Xms{self.xms_var.get()} -jar {self.core_type_var.get()}-{self.core_version_var.get()}.jar\n'
            'pause'
        )
        self.script_text.insert("end", default_script)
        
        # 控制按钮
        btn_frame = ttk.Frame(adv_window)
        btn_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(
            btn_frame,
            text="确定",
            command=lambda: self.save_advanced_settings(adv_window)
        ).pack(side="right", padx=5)
        
        ttk.Button(
            btn_frame,
            text="取消",
            command=adv_window.destroy
        ).pack(side="right")

    def save_advanced_settings(self, window):
        """保存高级配置"""
        self.server_data['custom_script'] = self.script_text.get("1.0", "end-1c")
        window.destroy()
        messagebox.showinfo("提示", "高级配置已保存")

    def validate_server_path(self):
        """验证服务器路径有效性"""
        path = Path(self.path_var.get())
        try:
            path.mkdir(parents=True, exist_ok=True)
            test_file = path / "msm_test.tmp"
            test_file.touch()
            test_file.unlink()
            return True
        except Exception as e:
            messagebox.showerror("路径错误", f"路径不可用: {str(e)}")
            return False

    def finish_creation(self):
        """完成服务器创建流程（集成下载管理器版）"""
        # 1. 收集表单数据
        self.server_data.update({
            'name': self.name_var.get(),
            'path': self.path_var.get(),
            'core_type': self.core_type_var.get(),
            'core_version': self.core_version_var.get(),
            'java_path': self.java_var.get(),
            'xmx': self.xmx_var.get(),
            'xms': self.xms_var.get()
        })

        # 2. 验证输入数据
        if not self._validate_inputs():
            return

        # 3. 准备服务器目录
        server_dir = Path(self.server_data['path']) / self.server_data['name']
        try:
            server_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("路径错误", f"无法创建服务器目录: {str(e)}")
            return

        # 4. 获取核心下载URL
        try:
            self.server_data['core_url'] = self.core_versions[
                self.server_data['core_type']
            ][self.server_data['core_version']]
        except KeyError:
            messagebox.showerror("错误", "无法获取核心下载地址，请选择其他版本")
            return

        # 5. 生成默认启动脚本（如果未自定义）
        if not self.server_data.get('custom_script'):
            self.server_data['custom_script'] = self._generate_default_script()

        # 6. 显示下载窗口
        self._show_download_window()

        # 7. 启动下载
        core_name = f"{self.server_data['core_type']}-{self.server_data['core_version']}.jar"
        download_path = str(server_dir / core_name)
        
        if not self.download_manager.start_download(
            url=self.server_data['core_url'],
            save_path=download_path,
            progress_callback=self._update_download_progress,
            completion_callback=self._handle_download_completion
        ):
            messagebox.showerror("错误", "下载已在进行中")
            self._cleanup_failed_creation(server_dir)

    def _validate_inputs(self):
        """验证所有输入字段"""
        # 检查服务器名称
        if not self.server_data['name'].strip():
            messagebox.showerror("错误", "服务器名称不能为空")
            return False
        
        # 检查路径有效性
        try:
            test_file = Path(self.server_data['path']) / "msm_test.tmp"
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            messagebox.showerror("路径错误", f"路径不可用: {str(e)}")
            return False
        
        # 检查Java路径
        if not shutil.which(self.server_data['java_path']):
            if not messagebox.askyesno(
                "警告", 
                "Java路径未验证，可能无效。是否继续？",
                icon='warning'
            ):
                return False
        
        return True

    def _generate_default_script(self):
        """生成默认启动脚本"""
        return (
            '@echo off\n'
            f'"{self.server_data["java_path"]}" '
            f'-Xmx{self.server_data["xmx"]} '
            f'-Xms{self.server_data["xms"]} '
            f'-jar {self.server_data["core_type"]}-{self.server_data["core_version"]}.jar\n'
            'pause'
        )

    def _show_download_window(self):
        """显示下载进度窗口"""
        self.download_window = tk.Toplevel(self.window)
        self.download_window.title("下载服务器核心")
        self.download_window.geometry("400x150")
        self.download_window.resizable(False, False)
        
        # 防止窗口被关闭
        self.download_window.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # 进度组件
        ttk.Label(
            self.download_window, 
            text=f"正在下载 {self.server_data['core_type']} {self.server_data['core_version']}...",
            font=('TkDefaultFont', 10, 'bold')
        ).pack(pady=(15, 10))
        
        self.progress_bar = ttk.Progressbar(
            self.download_window,
            orient='horizontal',
            length=350,
            mode='determinate'
        )
        self.progress_bar.pack()
        
        self.status_label = ttk.Label(
            self.download_window,
            text="准备下载...",
            font=('TkDefaultFont', 9)
        )
        self.status_label.pack(pady=(10, 0))
        
        cancel_btn = ttk.Button(
            self.download_window,
            text="取消",
            command=self._cancel_download
        )
        cancel_btn.pack(pady=(10, 15))

    def _update_download_progress(self, progress):
        """更新下载进度"""
        if hasattr(self, 'download_window') and self.download_window.winfo_exists():
            self.progress_bar['value'] = progress
            self.status_label.config(
                text=f"下载中: {progress:.1f}% - {self._format_speed(progress)}"
            )
            self.download_window.update()

    def _format_speed(self, progress):
        """计算并格式化下载速度"""
        if not hasattr(self, '_download_start_time'):
            self._download_start_time = time.time()
            return "速度计算中..."
        
        elapsed = time.time() - self._download_start_time
        if elapsed < 1 or progress <= 0:
            return ""
        
        estimated_size = (self.progress_bar['maximum'] or 1) * (progress / 100)
        speed_kbps = (estimated_size / 1024) / elapsed
        return f"{speed_kbps:.1f} KB/s"

    def _handle_download_completion(self, success, error_msg=None):
        """处理下载完成事件"""
        # 清理计时器
        if hasattr(self, '_download_start_time'):
            del self._download_start_time
        
        # 关闭下载窗口
        if hasattr(self, 'download_window') and self.download_window.winfo_exists():
            self.download_window.destroy()
        
        if not success:
            self._handle_download_failure(error_msg)
            return
        
        # 下载成功后的处理
        server_dir = Path(self.server_data['path']) / self.server_data['name']
        try:
            # 保存启动脚本
            bat_path = server_dir / "start.bat"
            bat_path.write_text(self.server_data['custom_script'], encoding='utf-8')
            
            # 回调主程序
            self.callback(self.server_data)
            messagebox.showinfo(
                "成功", 
                f"服务器 '{self.server_data['name']}' 创建完成！\n"
                f"路径: {server_dir}"
            )
            self.window.destroy()
            
        except Exception as e:
            self._handle_download_failure(f"无法保存启动脚本: {str(e)}")
            self._cleanup_failed_creation(server_dir)

    def _handle_download_failure(self, error_msg):
        """处理下载失败"""
        messagebox.showerror(
            "下载失败", 
            f"无法下载服务器核心:\n{error_msg}\n\n"
            "请检查：\n"
            "1. 网络连接是否正常\n"
            "2. 下载地址是否有效\n"
            "3. 磁盘空间是否充足"
        )
        if hasattr(self, 'server_data') and 'path' in self.server_data:
            server_dir = Path(self.server_data['path']) / self.server_data['name']
            self._cleanup_failed_creation(server_dir)

    def _cleanup_failed_creation(self, server_dir):
        """清理创建失败的残留文件"""
        try:
            if server_dir.exists():
                shutil.rmtree(server_dir, ignore_errors=True)
        except Exception as e:
            print(f"清理失败: {str(e)}")

    def _cancel_download(self):
        """取消下载操作"""
        if hasattr(self, 'server_data') and 'core_url' in self.server_data:
            if messagebox.askyesno(
                "确认取消",
                "确定要取消服务器创建吗？\n已下载的文件将被删除。",
                icon='warning'
            ):
                self.download_manager.cancel_download(self.server_data['core_url'])
                if hasattr(self, 'download_window') and self.download_window.winfo_exists():
                    self.download_window.destroy()
                
                server_dir = Path(self.server_data['path']) / self.server_data['name']
                self._cleanup_failed_creation(server_dir)

    def monitor_server_output(self, process):
        """监控服务器输出，修复编码问题"""
        while True:
            try:
                # 读取字节并指定UTF-8编码，忽略无法解码的字符
                output = process.stdout.readline()
                if not output and process.poll() is not None:
                    break
                if output:
                    # 使用UTF-8解码，遇到错误时忽略
                    decoded_output = output.decode('utf-8', errors='ignore').strip()
                    # 移除ANSI转义序列
                    cleaned_output = clean_ansi_codes(decoded_output)
                    # 在主线程更新UI
                    self.root.after(0, self.log_to_console, cleaned_output)
            except Exception as e:
                error_msg = f"输出处理错误: {str(e)}"
                self.root.after(0, self.log_to_console, error_msg)
                break

class MinecraftServerManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Minecraft Server Manager v1.0-T202510061206")
        self.root.geometry("800x600")
        icon_path = "download.ico"
        try:
            self.root.iconbitmap(icon_path)
        except Exception as e:
            messagebox.showerror("错误", f"Error:{e}。如果在.exe应用中看到此报错，请尽快联系开发者！")
        
        self.msm_dir = Path.home() / ".msm"
        self.msm_dir.mkdir(exist_ok=True)
        self.config_file = self.msm_dir / "MSM.ini"
        
        self.config = configparser.ConfigParser()
        if self.config_file.exists():
            self.config.read(self.config_file)
        
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            control_frame,
            text="创建服务器",
            command=self.show_server_wizard
        ).pack(side=tk.LEFT, padx=10)
        
        self.tabs = {}
        self.server_processes = {}
        self.load_servers()

        ttk.Button(
            control_frame,
            text="添加已有服务器",
            command=self.add_existing_server
        ).pack(side=tk.LEFT, padx=10)

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
                f"以下服务器仍在运行：\n{server_list}\n\n"
                "现在退出将强制关闭这些服务器！\n"
                "确定要继续吗？"
            )
            
            # 弹出确认对话框
            if not messagebox.askyesno(
                "确认退出",
                message,
                icon='warning'
            ):
                return  # 用户取消退出
            
            # 强制停止所有服务器
            for tab_id in running_servers:
                try:
                    process = self.server_processes[tab_id]
                    process.kill()  # 强制终止
                    self.log_to_console(tab_id, "⚠️ 服务器已被强制终止")
                except Exception as e:
                    self.log_to_console(tab_id, f"❌ 终止失败: {str(e)}")
        
        # 保存配置
        self.save_servers()
        
        # 销毁主窗口
        self.root.destroy()

    def add_existing_server(self):
        """添加已有服务器到列表"""
        server_dir = filedialog.askdirectory(
            title="选择已有服务器目录",
            initialdir=str(Path.home())
        )
        
        if not server_dir:
            return
            
        server_path = Path(server_dir)
        
        # 验证服务器目录结构
        if not self.validate_existing_server(server_path):
            messagebox.showerror(
                "错误",
                "无效的服务器目录\n"
                "必须包含以下文件之一:\n"
                "- server.jar\n"
                "- start.bat"
            )
            return
            
        # 添加服务器标签页
        tab_id = self.add_server_tab(str(server_path))
        self.notebook.select(tab_id)
        self.save_servers()
        
    def validate_existing_server(self, server_path):
        """验证服务器目录是否有效"""
        required_files = [
            server_path / "server.jar",
            server_path / "start.bat"
        ]
        
        # 检查是否存在任一必需文件
        return any(f.exists() for f in required_files)

    def load_servers(self):
        """加载已有服务器配置"""
        if 'Servers' in self.config:
            for server_id, path in self.config['Servers'].items():
                if Path(path).exists():
                    self.add_server_tab(initial_path=path)

    def save_servers(self):
        """保存服务器配置"""
        self.config['Servers'] = {}
        for i, (tab_id, tab_data) in enumerate(self.tabs.items()):
            if path := tab_data['path_var'].get():
                self.config['Servers'][f'server_{i}'] = path
        
        with open(self.config_file, 'w') as f:
            self.config.write(f)

    def show_server_wizard(self):
        """显示服务器创建向导"""
        ServerCreationWizard(self.root, self.handle_server_creation)

    def handle_server_creation(self, server_data):
        """处理新服务器创建请求（线程安全版）"""
        def worker():
            tab_id = None  # 初始化标签页ID
            try:
                # 准备路径
                server_dir = Path(server_data['path']) / server_data['name']
                core_name = f"{server_data['core_type']}-{server_data['core_version']}.jar"
                
                # 在主线程创建标签页（避免重复）
                self.root.after(0, lambda: (
                    setattr(self, '_pending_tab_id', self.add_server_tab(str(server_dir))),
                    self.notebook.select(self._pending_tab_id)
                ))
                tab_id = self._pending_tab_id  # 获取创建的标签页ID
                
                # 下载核心文件
                self.root.after(0, lambda: self.log_to_console(tab_id, "开始下载服务器核心..."))
                if not self.download_core(server_data['core_url'], str(server_dir / core_name)):
                    raise Exception("核心下载失败")
                
                # 保存启动脚本
                bat_path = server_dir / "start.bat"
                self.root.after(0, lambda: (
                    bat_path.write_text(server_data['custom_script'], encoding='utf-8'),
                    self.log_to_console(tab_id, "启动脚本已生成")
                ))
                
                # 更新配置
                self.root.after(0, lambda: (
                    self.save_servers(),
                    self.log_to_console(tab_id, "✅ 服务器创建完成"),
                    messagebox.showinfo("成功", f"服务器 '{server_data['name']}' 已创建")
                ))
                
            except Exception as e:
                if tab_id:  # 如果标签页已创建
                    self.root.after(0, lambda: (
                        self.log_to_console(tab_id, f"❌ 创建失败: {str(e)}"),
                        messagebox.showerror("错误", str(e))
                    ))
                # 清理残留文件
                if 'server_dir' in locals() and server_dir.exists():
                    shutil.rmtree(server_dir, ignore_errors=True)
        
        # 启动工作线程
        threading.Thread(target=worker, daemon=True).start()

    def download_core(self, url, save_path):
        """下载服务器核心文件"""
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
            
            return True
        except Exception as e:
            print(f"下载失败: {str(e)}")
            return False

    def edit_start_script(self, tab_id):
        """编辑服务器的启动脚本"""
        if tab_id not in self.tabs:
            return
            
        # 获取服务器路径
        server_path = self.tabs[tab_id]['path_var'].get()
        if not server_path or not os.path.exists(server_path):
            messagebox.showerror("错误", "服务器路径不存在")
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
                messagebox.showerror("错误", f"无法读取启动脚本: {str(e)}")
                return
        
        # 创建编辑窗口
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"编辑启动脚本 - {tab_id}")
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
                messagebox.showinfo("成功", "启动脚本已保存")
                edit_window.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {str(e)}")
        
        ttk.Button(btn_frame, text="保存", command=save_script).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=edit_window.destroy).pack(side=tk.RIGHT)

    def start_resource_monitor(self, tab_id):
        """启动资源监控窗口"""
        if tab_id not in self.server_processes:
            messagebox.showinfo("提示", "请先启动服务器")
            return
            
        process = self.server_processes[tab_id]
        if process.poll() is not None:
            messagebox.showinfo("提示", "服务器未在运行")
            return
            
        # 创建并显示监控窗口
        self.resource_monitor = ResourceMonitorWindow(
            self.root,
            tab_id,
            process.pid
        )

    def add_server_tab(self, initial_path=None):
        """添加新的服务器标签页"""
        # 生成唯一ID
        tab_id = f"server_{len(self.tabs) + 1}"
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text=Path(initial_path).name if initial_path else "新服务器")
        
        # 路径变量
        path_var = tk.StringVar(value=initial_path)
        path_var.trace_add('write', lambda *args: self.save_servers())
        
        # 控制按钮区域
        control_frame = ttk.Frame(tab_frame)
        control_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # 启动按钮
        start_btn = ttk.Button(
            control_frame,
            text="启动",
            command=lambda: self.start_server(tab_id)
        )
        start_btn.pack(side=tk.LEFT, padx=2)
        
        # 停止按钮
        stop_btn = ttk.Button(
            control_frame,
            text="停止",
            command=lambda: self.stop_server(tab_id),
            state=tk.DISABLED
        )
        stop_btn.pack(side=tk.LEFT, padx=2)
        
        # 重启按钮
        restart_btn = ttk.Button(
            control_frame,
            text="重启",
            command=lambda: self.restart_server(tab_id),
            state=tk.DISABLED
        )
        restart_btn.pack(side=tk.LEFT, padx=2)
        
        # 编辑server.properties按钮
        edit_prop_btn = ttk.Button(
            control_frame,
            text="编辑 server.properties",
            command=lambda: self.edit_server_properties(tab_id)
        )
        edit_prop_btn.pack(side=tk.LEFT, padx=2)

        edit_script_btn = ttk.Button(
            control_frame,
            text="编辑启动脚本",
            command=lambda: self.edit_start_script(tab_id)
        )
        edit_script_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            control_frame,
            text="监控资源",
            command=lambda: self.start_resource_monitor(tab_id)
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            control_frame,
            text="帮助...",
            command=lambda: webbrowser.open("http://xg-2.frp.one:12935")
        ).pack(side=tk.RIGHT, padx=5)
        
        # 路径显示与浏览
        path_frame = ttk.Frame(tab_frame)
        path_frame.pack(fill=tk.X, padx=5)
        
        ttk.Label(path_frame, text="服务器路径:").pack(side=tk.LEFT)
        ttk.Entry(path_frame, textvariable=path_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(
            path_frame,
            text="浏览",
            command=lambda: self.browse_server_path(tab_id)
        ).pack(side=tk.RIGHT, padx=5)
        
        # 日志区域
        log_frame = ttk.LabelFrame(tab_frame, text="控制台输出")
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
        
        ttk.Label(command_frame, text="指令:").pack(side=tk.LEFT, padx=5)
        self.command_var = tk.StringVar()
        command_entry = ttk.Entry(command_frame, textvariable=self.command_var)
        command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 发送指令按钮
        send_btn = ttk.Button(
            command_frame,
            text="发送",
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
            'status_var': tk.StringVar(value="已停止"),
            'edit_script_btn': edit_script_btn,
            'command_var': self.command_var
        }
        
        return tab_id

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
            messagebox.showerror("错误", "服务器路径不存在")
            return
            
        # 检查是否已有进程在运行
        if tab_id in self.server_processes and self.server_processes[tab_id].poll() is None:
            messagebox.showwarning("警告", "服务器已经在运行中")
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
            messagebox.showerror("错误", "未找到启动脚本或核心文件")
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
            self.log_to_console(tab_id, f"✅ 服务器已启动: {cmd}")
            
            # 启动输出监控线程
            threading.Thread(
                target=self.monitor_server_output,
                args=(tab_id, process),
                daemon=True
            ).start()
            
        except Exception as e:
            self.log_to_console(tab_id, f"❌ 启动失败: {str(e)}")
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
            messagebox.showinfo("提示", "服务器未在运行")
            return
            
        try:
            # 尝试优雅关闭
            self.log_to_console(tab_id, "⚠️ 正在停止服务器...")
            process.stdin.write("stop\n")
            process.stdin.flush()
            
            # 等待关闭
            timeout = 10
            start_time = time.time()
            while process.poll() is None and time.time() - start_time < timeout:
                time.sleep(0.5)
                
            # 如果仍在运行则强制关闭
            if process.poll() is None:
                self.log_to_console(tab_id, "⚠️ 服务器无响应，强制关闭中...")
                process.kill()
                
            self.log_to_console(tab_id, f"✅ 服务器已停止")
            
        except Exception as e:
            self.log_to_console(tab_id, f"❌ 停止失败: {str(e)}")
            
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
            messagebox.showinfo("提示", "请先启动服务器")
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
            self.log_to_console(tab_id, f"❌ 发送指令失败: {str(e)}")

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
        self.log_to_console(tab_id, f"💡 服务器已退出，退出代码: {exit_code}")
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
                messagebox.showerror("错误", "无法创建server.properties文件")
                return
        
        # 读取文件内容
        try:
            with open(properties_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("错误", f"无法读取文件: {str(e)}")
            return
        
        # 创建编辑窗口
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"编辑 {tab_id} 的 server.properties")
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
                messagebox.showinfo("成功", "server.properties已保存")
                edit_window.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {str(e)}")
        
        # 按钮区域
        btn_frame = ttk.Frame(edit_window)
        btn_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Button(btn_frame, text="保存", command=save_properties).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=edit_window.destroy).pack(side=tk.RIGHT)

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
            print(f"创建默认properties文件失败: {e}")
            return False

if __name__ == "__main__":
    root = tk.Tk()
    app = MinecraftServerManager(root)
    root.mainloop()

#帮助...