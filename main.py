import requests
import time
import vlc
import tkinter as tk
from tkinter import ttk
import threading
import os
from tkinter import messagebox
import sys

# 获取脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))
# 颁奖音乐文件路径
AWARD_MUSIC_PATH = os.path.join(script_dir, "award.mp3")

API_BASE = "http://127.0.0.1:8000"

class MusicPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("校园点歌系统播放器")
        self.root.geometry("500x300")
        self.root.resizable(True, True)
        
        # 设置窗口图标（如果有的话）
        try:
            self.root.iconbitmap(os.path.join(script_dir, "icon.ico"))
        except:
            pass  # 如果没有图标文件，忽略错误
        
        # VLC实例
        self.instance = vlc.Instance('--no-video')
        self.player = self.instance.media_player_new()
        
        # 播放状态变量
        self.is_playing = False  # 是否正在播放
        self.award_mode = False  # 是否在颁奖模式
        self.current_song = None  # 当前播放的歌曲信息
        self.player_thread = None  # 播放线程
        self.award_thread = None  # 颁奖播放线程
        self.playback_position = 0  # 保存被中断的歌曲播放位置
        
        self.create_widgets()
        
        # 启动主循环线程
        self.should_run = True
        self.player_thread = threading.Thread(target=self.main_loop)
        self.player_thread.daemon = True
        self.player_thread.start()
        
        # 检查颁奖音乐文件是否存在
        if not os.path.exists(AWARD_MUSIC_PATH):
            messagebox.showwarning("文件缺失", f"颁奖音乐文件不存在: {AWARD_MUSIC_PATH}\n请确保award.mp3文件在程序目录下。")
    
    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题标签
        title_label = ttk.Label(main_frame, text="校园点歌系统播放器", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # 当前播放信息
        self.now_playing_var = tk.StringVar(value="等待播放...")
        now_playing_label = ttk.Label(main_frame, textvariable=self.now_playing_var, font=("Arial", 12))
        now_playing_label.pack(pady=5)
        
        # 状态信息
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, font=("Arial", 10))
        status_label.pack(pady=5)
        
        # 控制按钮框架
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(pady=20)
        
        # 颁奖模式按钮
        self.award_button = ttk.Button(
            control_frame, 
            text="开始颁奖模式", 
            command=self.toggle_award_mode,
            width=20
        )
        self.award_button.grid(row=0, column=0, padx=10, pady=10)
        
        # 刷新队列按钮
        refresh_button = ttk.Button(
            control_frame, 
            text="刷新歌曲队列", 
            command=self.refresh_queue,
            width=20
        )
        refresh_button.grid(row=0, column=1, padx=10, pady=10)
        
        # 播放控制按钮框架
        playback_frame = ttk.Frame(main_frame)
        playback_frame.pack(pady=10)
        
        # 暂停/播放按钮
        self.play_pause_button = ttk.Button(
            playback_frame, 
            text="暂停", 
            command=self.toggle_play_pause,
            width=15
        )
        self.play_pause_button.grid(row=0, column=0, padx=5)
        
        # 跳过当前歌曲按钮
        skip_button = ttk.Button(
            playback_frame, 
            text="跳过当前歌曲", 
            command=self.skip_current,
            width=15
        )
        skip_button.grid(row=0, column=1, padx=5)
        
        # 进度条（模拟，不实际控制播放）
        self.progress_var = tk.DoubleVar(value=0.0)
        progress_bar = ttk.Progressbar(
            main_frame, 
            orient="horizontal", 
            length=400, 
            mode="determinate",
            variable=self.progress_var
        )
        progress_bar.pack(pady=10, fill=tk.X, padx=20)
        
        # 创建状态栏
        status_bar = ttk.Frame(self.root, relief=tk.SUNKEN, padding=(2, 2))
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 服务器连接状态
        self.server_status_var = tk.StringVar(value="服务器: 未连接")
        server_status = ttk.Label(status_bar, textvariable=self.server_status_var, font=("Arial", 9))
        server_status.pack(side=tk.LEFT)
        
        # 更新服务器状态
        self.check_server_connection()
    
    def check_server_connection(self):
        """检查服务器连接状态"""
        try:
            response = requests.get(f"{API_BASE}/api/player/queue", timeout=3)
            if response.status_code == 200:
                self.server_status_var.set("服务器: 已连接")
            else:
                self.server_status_var.set("服务器: 连接错误")
        except:
            self.server_status_var.set("服务器: 无法连接")
        
        # 每30秒检查一次
        self.root.after(30000, self.check_server_connection)
    
    def toggle_award_mode(self):
        """切换颁奖模式"""
        if not self.award_mode:
            # 启动颁奖模式
            self.start_award_mode()
        else:
            # 结束颁奖模式
            self.stop_award_mode()
    
    def start_award_mode(self):
        """开始颁奖模式"""
        if not os.path.exists(AWARD_MUSIC_PATH):
            messagebox.showerror("错误", "颁奖音乐文件(award.mp3)不存在！")
            return
        
        self.award_mode = True
        self.award_button.config(text="结束颁奖模式")
        self.status_var.set("颁奖模式中")
        
        # 保存当前播放状态和位置
        if self.is_playing:
            self.playback_position = self.player.get_time()
            self.player.pause()  # 暂停当前播放
        
        # 播放颁奖音乐
        self.now_playing_var.set("正在播放: 颁奖音乐")
        
        # 创建新的播放器实例用于颁奖音乐
        self.award_player = self.instance.media_player_new()
        media = self.instance.media_new(AWARD_MUSIC_PATH)
        self.award_player.set_media(media)
        
        # 启动颁奖音乐播放线程
        self.award_thread = threading.Thread(target=self.play_award_music)
        self.award_thread.daemon = True
        self.award_thread.start()
    
    def play_award_music(self):
        """播放颁奖音乐（循环）"""
        self.award_player.play()
        
        while self.award_mode and self.should_run:
            # 检查播放状态
            state = self.award_player.get_state()
            
            # 如果播放结束，重新开始
            if state == vlc.State.Ended:
                self.award_player.stop()
                self.award_player.play()
            
            # 更新进度条
            if self.award_player.get_length() > 0:
                position = self.award_player.get_time() / self.award_player.get_length()
                self.progress_var.set(position * 100)
            
            time.sleep(0.1)
    
    def stop_award_mode(self):
        """结束颁奖模式"""
        self.award_mode = False
        self.award_button.config(text="开始颁奖模式")
        
        # 停止颁奖音乐
        if hasattr(self, 'award_player'):
            self.award_player.stop()
        
        # 恢复之前的播放
        if self.current_song:
            self.status_var.set("恢复正常播放")
            
            # 如果之前正在播放，恢复播放
            if self.playback_position > 0:
                self.player.set_time(self.playback_position)
                self.player.play()
                self.is_playing = True
            
            # 更新播放按钮状态
            self.play_pause_button.config(text="暂停" if self.is_playing else "播放")
    
    def toggle_play_pause(self):
        """切换播放/暂停状态"""
        if self.award_mode:
            # 颁奖模式下不允许改变主播放器状态
            return
        
        if self.is_playing:
            self.player.pause()
            self.is_playing = False
            self.should_run = False
            self.play_pause_button.config(text="播放")
            self.status_var.set("已暂停")
        else:
            self.player.play()
            self.is_playing = True
            self.should_run = True
            self.play_pause_button.config(text="暂停")
            self.status_var.set("正在播放")
    
    def skip_current(self):
        """跳过当前歌曲"""
        if self.award_mode:
            messagebox.showinfo("提示", "请先结束颁奖模式再操作")
            return
        
        if self.current_song:
            self.status_var.set("跳过当前歌曲")
            self.player.stop()
            
            # 标记为已播放
            if self.current_song.get("request_id"):
                threading.Thread(
                    target=mark_played,
                    args=(self.current_song["request_id"],)
                ).start()
            
            self.current_song = None
    
    def refresh_queue(self):
        """手动刷新歌曲队列"""
        self.status_var.set("正在刷新歌曲队列...")
        threading.Thread(target=self._refresh_queue).start()
    
    def _refresh_queue(self):
        """后台刷新队列"""
        queue = fetch_queue()
        self.root.after(0, lambda: self.status_var.set(
            f"队列刷新完成，有 {len(queue)} 首歌曲待播放" if queue else "队列为空"
        ))
    
    def update_progress(self):
        """更新进度条"""
        if self.is_playing and not self.award_mode and self.player.get_length() > 0:
            position = self.player.get_time() / self.player.get_length()
            self.progress_var.set(position * 100)
        
        # 每秒更新一次
        self.root.after(1000, self.update_progress)
    
    def main_loop(self):
        """主播放循环"""
        while self.should_run:
            # 如果处于颁奖模式，暂停主循环
            if self.award_mode:
                time.sleep(1)
                continue
            
            # 如果已有歌曲在播放，检查其状态
            if self.current_song and self.is_playing:
                state = self.player.get_state()
                
                # 如果播放结束，移除当前歌曲并继续
                if state in [vlc.State.Ended, vlc.State.Stopped, vlc.State.Error]:
                    if self.current_song.get("request_id"):
                        mark_played(self.current_song["request_id"])
                    
                    self.current_song = None
                    self.root.after(0, lambda: self.now_playing_var.set("等待下一首..."))
                    time.sleep(1)
                else:
                    # 歌曲仍在播放中
                    time.sleep(0.5)
                    continue
            
            # 获取播放队列
            queue = fetch_queue()
            
            if not queue:
                # 队列为空，等待10秒后重试
                self.root.after(0, lambda: self.status_var.set("队列为空，等待中..."))
                time.sleep(10)
                continue
            
            # 获取下一首歌
            song = queue[0]
            self.root.after(0, lambda: self.status_var.set(f"正在加载歌曲 ID: {song['song_id']}"))
            
            # 获取播放地址
            url = fetch_url(song["song_id"])
            
            if not url:
                # 无法获取播放地址，标记已播放并跳过
                self.root.after(0, lambda: self.status_var.set("无法获取播放地址，跳过"))
                mark_played(song["request_id"])
                time.sleep(2)
                continue
            
            # 播放歌曲
            self.current_song = song
            self.playback_position = 0
            
            # 创建播放媒体
            media = self.instance.media_new(url)
            self.player.set_media(media)
            self.player.play()
            self.is_playing = True
            self.root.after(0, lambda: self.play_pause_button.config(text="暂停"))
            
            # 等待媒体加载并获取元数据
            time.sleep(1.5)
            
            media_title = media.get_meta(vlc.Meta.Title) or f"歌曲 #{song['song_id']}"
            self.root.after(0, lambda: self.now_playing_var.set(f"正在播放: {media_title}"))
            self.root.after(0, lambda: self.status_var.set("播放中"))
            
            # 短暂等待，避免CPU过度使用
            time.sleep(0.5)
    
    def on_closing(self):
        """窗口关闭时的处理"""
        if messagebox.askokcancel("退出", "确定要退出播放器吗？"):
            self.should_run = False
            
            # 停止所有播放
            self.player.stop()
            if hasattr(self, 'award_player'):
                self.award_player.stop()
            
            self.root.destroy()
            sys.exit(0)

def fetch_queue():
    """获取待播放队列"""
    try:
        res = requests.get(f"{API_BASE}/api/player/queue", timeout=8)
        return res.json().get("queue", [])
    except Exception as e:
        print("获取队列失败：", e)
        return []

def fetch_url(song_id):
    """获取歌曲播放链接"""
    try:
        res = requests.get(f"{API_BASE}/api/geturl?id={song_id}", timeout=8)
        data = res.json().get("data", {})
        return data.get("url")
    except Exception as e:
        print("获取播放链接失败：", e)
        return None

def mark_played(request_id):
    """标记歌曲为已播放"""
    try:
        res = requests.post(f"{API_BASE}/api/player/played", json={"request_id": request_id}, timeout=8)
        return res.json().get("success", False)
    except Exception as e:
        print("标记已播放失败：", e)
        return False

if __name__ == "__main__":
    root = tk.Tk()
    app = MusicPlayer(root)
    
    # 开始定时更新进度条
    app.update_progress()
    
    # 设置窗口关闭事件
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # 启动主循环
    root.mainloop()