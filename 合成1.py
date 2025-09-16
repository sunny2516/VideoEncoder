import os
import random
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import threading
from collections import defaultdict, deque

class FileExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("文件随机提取工具")
        self.root.geometry("600x900")

        # 初始化变量
        self.source_folders = []
        self.destination_folder = ""
        self.n = 1
        self.is_running = False
        self.cancel_task = False
        self.output_name_prefix = "output"
        self.thread_count = 1
        self.file_usage = defaultdict(int)  # 跟踪文件使用次数
        self.available_files = {}  # 每个子文件夹的可用文件列表
        self.max_usage_per_file = 3  # 每个文件最大使用次数，可调整
        self.recently_used = deque(maxlen=10)  # 最近使用缓存，避免短期重复

        # 创建界面组件
        self.create_widgets()

    def create_widgets(self):
        tk.Label(self.root, text="选择父文件夹（包含子文件夹）：", font=("Arial", 10)).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.parent_folder_label = tk.Label(self.root, text="未选择", fg="gray", font=("Arial", 10))
        self.parent_folder_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        tk.Button(self.root, text="选择父文件夹", command=self.choose_parent_folder, font=("Arial", 10)).grid(row=1, column=1, padx=10, pady=5)

        tk.Label(self.root, text="选择目标文件夹：", font=("Arial", 10)).grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.destination_folder_label = tk.Label(self.root, text="未选择", fg="gray", font=("Arial", 10))
        self.destination_folder_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        tk.Button(self.root, text="选择文件夹", command=self.choose_destination_folder, font=("Arial", 10)).grid(row=3, column=1, padx=10, pady=5)

        tk.Label(self.root, text="循环次数（n）：", font=("Arial", 10)).grid(row=4, column=0, padx=10, pady=10, sticky="w")
        self.n_entry = tk.Entry(self.root, width=10, font=("Arial", 10))
        self.n_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")
        self.n_entry.insert(0, "1")

        tk.Label(self.root, text="输出文件名前缀：", font=("Arial", 10)).grid(row=5, column=0, padx=10, pady=10, sticky="w")
        self.name_prefix_entry = tk.Entry(self.root, width=20, font=("Arial", 10))
        self.name_prefix_entry.grid(row=5, column=1, padx=10, pady=5, sticky="w")
        self.name_prefix_entry.insert(0, "output")

        tk.Label(self.root, text="线程数：", font=("Arial", 10)).grid(row=6, column=0, padx=10, pady=10, sticky="w")
        self.thread_entry = tk.Entry(self.root, width=10, font=("Arial", 10))
        self.thread_entry.grid(row=6, column=1, padx=10, pady=5, sticky="w")
        self.thread_entry.insert(0, "1")

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=500, mode="determinate")
        self.progress.grid(row=7, column=0, padx=10, pady=20, columnspan=2)

        self.log_area = scrolledtext.ScrolledText(self.root, width=70, height=10, font=("Arial", 10))
        self.log_area.grid(row=8, column=0, padx=10, pady=10, columnspan=2)
        self.log_area.config(state=tk.DISABLED)

        self.generate_button = tk.Button(
            self.root, text="生成", command=self.start_generate_files, bg="green", fg="white", font=("Arial", 10)
        )
        self.generate_button.grid(row=9, column=0, padx=10, pady=20, columnspan=1)

        self.cancel_button = tk.Button(
            self.root, text="取消", command=self.cancel_generate_files, bg="red", fg="white", font=("Arial", 10)
        )
        self.cancel_button.grid(row=9, column=1, padx=10, pady=20, columnspan=1)
        self.cancel_button.config(state=tk.DISABLED)

    def log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.config(state=tk.DISABLED)
        self.log_area.yview(tk.END)

    def choose_parent_folder(self):
        parent_folder = filedialog.askdirectory(title="选择父文件夹")
        if parent_folder:
            self.parent_folder_label.config(text=parent_folder, fg="black")
            self.source_folders = [
                os.path.join(parent_folder, f) for f in os.listdir(parent_folder) if os.path.isdir(os.path.join(parent_folder, f))
            ]
            self.available_files = {}
            for folder in self.source_folders:
                self.available_files[folder] = [
                    os.path.join(folder, f) for f in os.listdir(folder)
                    if os.path.isfile(os.path.join(folder, f)) and f.endswith((".mp4", ".avi", ".mkv"))
                ]
            self.log(f"已选择父文件夹：{parent_folder}")
            self.log(f"找到 {len(self.source_folders)} 个子文件夹，总计 {sum(len(files) for files in self.available_files.values())} 个视频文件")

    def choose_destination_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.destination_folder = folder
            self.destination_folder_label.config(text=folder, fg="black")
            self.log(f"已选择目标文件夹：{folder}")

    def merge_videos(self, video_files, output_path):
        list_file_path = os.path.join(self.destination_folder, "file_list.txt")
        with open(list_file_path, "w", encoding="utf-8") as f:
            f.writelines(f"file '{file}'\n" for file in video_files)

        command = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file_path,
            "-c", "copy",
            "-loglevel", "quiet",
            output_path,
        ]
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            self.log(f"合并视频失败：{e.stderr.decode('utf-8', errors='ignore')}")
            raise
        finally:
            os.remove(list_file_path)

    def select_file(self, folder):
        files = self.available_files[folder]
        if not files:
            return None

        available = [f for f in files if self.file_usage[f] < self.max_usage_per_file]
        if not available:
            for f in files:
                self.file_usage[f] = 0
            available = files

        # 过滤最近使用过的文件
        filtered = [f for f in available if f not in self.recently_used]
        if filtered:
            available = filtered

        # 按使用次数生成权重：次数越少，权重越大
        weights = [1 / (1 + self.file_usage[f]) for f in available]
        selected = random.choices(available, weights=weights, k=1)[0]

        self.file_usage[selected] += 1
        self.recently_used.append(selected)
        return selected

    def start_generate_files(self):
        if self.is_running:
            messagebox.showwarning("警告", "任务正在运行，请稍后再试！")
            return

        if not self.source_folders or not self.destination_folder:
            messagebox.showerror("错误", "请选择父文件夹和目标文件夹！")
            return

        try:
            n = int(self.n_entry.get())
            if n <= 0:
                messagebox.showerror("错误", "循环次数必须大于 0！")
                return
        except ValueError:
            messagebox.showerror("错误", "请输入有效的循环次数！")
            return

        try:
            self.thread_count = int(self.thread_entry.get())
            if self.thread_count <= 0:
                messagebox.showerror("错误", "线程数必须大于 0！")
                return
        except ValueError:
            messagebox.showerror("错误", "请输入有效的线程数！")
            return

        self.output_name_prefix = self.name_prefix_entry.get().strip()
        if not self.output_name_prefix:
            messagebox.showerror("错误", "请输入有效的输出文件名前缀！")
            return

        self.is_running = True
        self.cancel_task = False
        self.generate_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        self.log("任务开始...")

        threading.Thread(target=self.generate_files, args=(n,), daemon=True).start()

    def cancel_generate_files(self):
        self.cancel_task = True
        self.log("任务取消中...")

    def generate_files(self, n):
        self.progress["maximum"] = n
        self.progress["value"] = 0

        for i in range(n):
            if self.cancel_task:
                self.log("任务已取消")
                break

            selected_files = []
            for folder in self.source_folders:
                if self.available_files[folder]:
                    file = self.select_file(folder)
                    if file:
                        selected_files.append(file)

            if selected_files:
                output_name = f"{self.output_name_prefix}_{i + 1}.mp4"
                output_path = os.path.join(self.destination_folder, output_name)
                self.merge_videos(selected_files, output_path)

            self.progress["value"] += 1
            self.log(f"已完成 {i + 1}/{n} 次循环")
            self.root.update_idletasks()

        self.is_running = False
        self.generate_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.DISABLED)
        if not self.cancel_task:
            self.log("任务完成！")
            messagebox.showinfo("完成", f"文件已成功复制到 {self.destination_folder}！")
            os.startfile(self.destination_folder)

if __name__ == "__main__":
    root = tk.Tk()
    app = FileExtractorApp(root)
    root.mainloop()
