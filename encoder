import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import datetime
import re
import json

# File to store saved paths
SETTINGS_FILE = "encoder_settings.json"

def check_nvidia_gpu():
    try:
        result = subprocess.run(["nvidia-smi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              text=True, check=False)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def check_ffmpeg_nvenc_support():
    try:
        result = subprocess.run(["ffmpeg", "-encoders"], stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE, text=True, check=False)
        return result.returncode == 0 and "h264_nvenc" in result.stdout
    except FileNotFoundError:
        return False

class VideoEncoderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("视频编码工具")
        self.root.geometry("600x900")

        # 初始化变量
        self.source_folder = ""
        self.output_folder = ""
        self.is_running = False
        self.cancel_task = False
        self.thread_count = 1
        self.video_files = []

        # 必须先创建界面组件
        self.create_widgets()

        # 然后才能调用可能使用log_area的方法
        # 检测硬件支持
        self.has_nvidia_gpu = check_nvidia_gpu()
        self.has_ffmpeg_nvenc = check_ffmpeg_nvenc_support()
        
        # 加载设置（现在可以安全地使用log_area）
        self._load_settings()

        # 如果源文件夹已加载，开始扫描
        if self.source_folder:
            self.parent_folder_label.config(text=self.source_folder, fg="black")
            self.root.after(100, self._scan_subfolders_threaded)

    def _load_settings(self):
        """从文件加载保存的设置"""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                    self.source_folder = settings.get('source_folder', '')
                    self.output_folder = settings.get('output_folder', '')
            except json.JSONDecodeError:
                self.log("警告: 设置文件损坏，将使用默认设置。")
            except Exception as e:
                self.log(f"加载设置时发生错误: {e}")

    def _save_settings(self):
        """保存当前设置到文件"""
        settings = {
            'source_folder': self.source_folder,
            'output_folder': self.output_folder
        }
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            self.log(f"保存设置时发生错误: {e}")

    def create_widgets(self):
        """创建 GUI 组件"""
        # 父文件夹选择
        tk.Label(self.root, text="选择父文件夹：", font=("Arial", 10)).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.parent_folder_label = tk.Label(self.root, text="未选择", fg="gray", font=("Arial", 10))
        self.parent_folder_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        tk.Button(self.root, text="选择文件夹", command=self.choose_parent_folder, 
                 font=("Arial", 10)).grid(row=1, column=1, padx=10, pady=5)

        # 输出文件夹选择
        tk.Label(self.root, text="选择输出文件夹：", font=("Arial", 10)).grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.output_folder_label = tk.Label(self.root, text="未选择", fg="gray", font=("Arial", 10))
        self.output_folder_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        tk.Button(self.root, text="选择文件夹", command=self.choose_output_folder, 
                 font=("Arial", 10)).grid(row=3, column=1, padx=10, pady=5)

        # 视频参数设置
        tk.Label(self.root, text="视频比特率：", font=("Arial", 10)).grid(row=4, column=0, padx=10, pady=10, sticky="w")
        self.bitrate_entry = tk.Entry(self.root, width=10, font=("Arial", 10))
        self.bitrate_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")
        self.bitrate_entry.insert(0, "3M")

        tk.Label(self.root, text="最大比特率：", font=("Arial", 10)).grid(row=5, column=0, padx=10, pady=10, sticky="w")
        self.maxrate_entry = tk.Entry(self.root, width=10, font=("Arial", 10))
        self.maxrate_entry.grid(row=5, column=1, padx=10, pady=5, sticky="w")
        self.maxrate_entry.insert(0, "5M")

        tk.Label(self.root, text="缓冲区大小：", font=("Arial", 10)).grid(row=6, column=0, padx=10, pady=10, sticky="w")
        self.bufsize_entry = tk.Entry(self.root, width=10, font=("Arial", 10))
        self.bufsize_entry.grid(row=6, column=1, padx=10, pady=5, sticky="w")
        self.bufsize_entry.insert(0, "5M")

        tk.Label(self.root, text="音频比特率：", font=("Arial", 10)).grid(row=7, column=0, padx=10, pady=10, sticky="w")
        self.audio_bitrate_entry = tk.Entry(self.root, width=10, font=("Arial", 10))
        self.audio_bitrate_entry.grid(row=7, column=1, padx=10, pady=5, sticky="w")
        self.audio_bitrate_entry.insert(0, "128k")

        # 线程数输入
        tk.Label(self.root, text="线程数：", font=("Arial", 10)).grid(row=8, column=0, padx=10, pady=10, sticky="w")
        self.thread_entry = tk.Entry(self.root, width=10, font=("Arial", 10))
        self.thread_entry.grid(row=8, column=1, padx=10, pady=5, sticky="w")
        self.thread_entry.insert(0, "1")

        # 渲染方式选择
        self.render_mode = tk.StringVar(value="cpu")
        tk.Label(self.root, text="渲染方式：", font=("Arial", 10)).grid(row=9, column=0, padx=10, pady=10, sticky="w")
        tk.Radiobutton(self.root, text="CPU 渲染", variable=self.render_mode, 
                      value="cpu", font=("Arial", 10)).grid(row=9, column=1, padx=10, pady=5, sticky="w")
        self.gpu_button = tk.Radiobutton(self.root, text="显卡渲染", variable=self.render_mode, 
                                       value="gpu", font=("Arial", 10))
        self.gpu_button.grid(row=10, column=1, padx=10, pady=5, sticky="w")

        # 进度条
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=500, mode="determinate")
        self.progress.grid(row=11, column=0, padx=10, pady=20, columnspan=2)

        # 日志输出
        self.log_area = scrolledtext.ScrolledText(self.root, width=70, height=10, font=("Arial", 10))
        self.log_area.grid(row=12, column=0, padx=10, pady=10, columnspan=2)
        self.log_area.config(state=tk.DISABLED)

        # 按钮
        self.encode_button = tk.Button(
            self.root, text="开始编码", command=self.start_encode, 
            bg="green", fg="white", font=("Arial", 10)
        )
        self.encode_button.grid(row=13, column=0, padx=10, pady=20, columnspan=1)

        self.cancel_button = tk.Button(
            self.root, text="取消", command=self.cancel_encode, 
            bg="red", fg="white", font=("Arial", 10)
        )
        self.cancel_button.grid(row=13, column=1, padx=10, pady=20, columnspan=1)
        self.cancel_button.config(state=tk.DISABLED)

    def log(self, message):
        """在日志区域显示消息"""
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S]")
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"{timestamp} {message}\n")
        self.log_area.config(state=tk.DISABLED)
        self.log_area.yview(tk.END)

    def choose_parent_folder(self):
        """选择父文件夹"""
        initial_dir = self.source_folder if self.source_folder else os.path.expanduser("~")
        folder = filedialog.askdirectory(title="选择父文件夹", initialdir=initial_dir)
        if folder:
            self.source_folder = folder
            self.parent_folder_label.config(text=folder, fg="black")
            self.log(f"已选择父文件夹：{folder}")
            self._save_settings()
            threading.Thread(target=self._scan_subfolders_threaded, daemon=True).start()

    def _scan_subfolders_threaded(self):
        """扫描子文件夹"""
        self.video_files = []
        for root, _, files in os.walk(self.source_folder):
            for file in files:
                if file.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.webm')):
                    self.video_files.append(os.path.join(root, file))
        self.root.after(0, lambda: self.log(f"找到 {len(self.video_files)} 个视频文件"))

    def choose_output_folder(self):
        """选择输出文件夹"""
        initial_dir = self.output_folder if self.output_folder else os.path.expanduser("~")
        folder = filedialog.askdirectory(title="选择输出文件夹", initialdir=initial_dir)
        if folder:
            self.output_folder = folder
            self.output_folder_label.config(text=folder, fg="black")
            self.log(f"已选择输出文件夹：{folder}")
            self._save_settings()

    def _validate_bitrate_input(self, value):
        """验证比特率格式"""
        return re.fullmatch(r"^\d+(\.\d+)?[kKmMgG]?$", value) is not None

    def run_ffmpeg(self, command):
        """运行FFmpeg命令"""
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            process = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                creationflags=creationflags
            )
            self.log(f"FFmpeg 命令执行成功")
        except subprocess.CalledProcessError as e:
            self.log(f"FFmpeg 错误：{e.stderr}")
            raise

    def encode_video(self, input_path, output_path):
        """编码单个视频"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        encoder = "h264_nvenc" if self.render_mode.get() == "gpu" else "libx264"
        preset = "p5" if encoder == "h264_nvenc" else "medium"
        
        command = [
            "ffmpeg", "-i", input_path,
            "-vf", "scale=1080:1920", "-r", "25",
            "-c:v", encoder, "-preset", preset,
            "-b:v", self.bitrate_entry.get(),
            "-maxrate", self.maxrate_entry.get(),
            "-bufsize", self.bufsize_entry.get(),
            "-c:a", "aac", "-b:a", self.audio_bitrate_entry.get(),
            "-movflags", "faststart",
            "-loglevel", "error",
            output_path
        ]
        
        try:
            self.run_ffmpeg(command)
            self.root.after(0, lambda: self.log(f"成功编码: {input_path}"))
        except Exception as e:
            self.root.after(0, lambda: self.log(f"编码失败: {input_path}"))
            raise

    def start_encode(self):
        """开始编码任务"""
        if not all([
            self._validate_inputs(),
            self.source_folder,
            self.output_folder,
            self.video_files
        ]):
            return

        self.is_running = True
        self.cancel_task = False
        self.encode_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        
        threading.Thread(target=self._encode_videos_threaded, daemon=True).start()

    def _validate_inputs(self):
        """验证所有输入"""
        if not all(self._validate_bitrate_input(entry.get()) for entry in [
            self.bitrate_entry, self.maxrate_entry, 
            self.bufsize_entry, self.audio_bitrate_entry
        ]):
            messagebox.showerror("错误", "请输入有效的比特率格式（如3M或128k）")
            return False
        
        try:
            self.thread_count = max(1, int(self.thread_entry.get()))
        except ValueError:
            messagebox.showerror("错误", "请输入有效的线程数")
            return False
            
        return True

    def _encode_videos_threaded(self):
        """在后台线程中编码视频"""
        self.root.after(0, lambda: self.progress.config(maximum=len(self.video_files), value=0))
        
        with ThreadPoolExecutor(max_workers=self.thread_count) as executor:
            futures = []
            for video_file in self.video_files:
                if self.cancel_task:
                    break
                
                relative_path = os.path.relpath(video_file, self.source_folder)
                output_path = os.path.join(self.output_folder, os.path.splitext(relative_path)[0] + ".mp4")
                futures.append(executor.submit(self.encode_video, video_file, output_path))

            for i, future in enumerate(as_completed(futures), 1):
                if self.cancel_task:
                    break
                try:
                    future.result()
                except Exception:
                    pass
                self.root.after(0, lambda: self.progress.config(value=i))
                self.root.after(0, lambda: self.log(f"进度: {i}/{len(self.video_files)}"))

        self._finish_encoding()

    def _finish_encoding(self):
        """完成编码后的清理工作"""
        self.is_running = False
        self.encode_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.DISABLED)
        
        if self.cancel_task:
            self.log("任务已取消")
            messagebox.showinfo("取消", "编码任务已取消")
        else:
            self.log("任务完成")
            messagebox.showinfo("完成", "所有视频编码完成")

    def cancel_encode(self):
        """取消编码任务"""
        self.cancel_task = True
        self.log("正在取消任务...")

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoEncoderApp(root)
    root.mainloop()
