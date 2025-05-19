import requests
import time
import vlc

API_BASE = "http://127.0.0.1:8000"

def fetch_queue():
    try:
        res = requests.get(f"{API_BASE}/api/player/queue", timeout=8)
        return res.json().get("queue", [])
    except Exception as e:
        print("获取队列失败：", e)
        return []

def fetch_url(song_id):
    try:
        res = requests.get(f"{API_BASE}/api/geturl?id={song_id}", timeout=8)
        data = res.json().get("data", {})
        return data.get("url")
    except Exception as e:
        print("获取播放链接失败：", e)
        return None

def mark_played(request_id):
    try:
        res = requests.post(f"{API_BASE}/api/player/played", json={"request_id": request_id}, timeout=8)
        return res.json().get("success", False)
    except Exception as e:
        print("标记已播放失败：", e)
        return False

def play_stream(url):
    print("正在播放:", url)
    instance = vlc.Instance('--no-video')
    player = instance.media_player_new()
    media = instance.media_new(url)
    player.set_media(media)
    player.play()
    # 等待播放开始
    time.sleep(1.5)
    # 获取总时长
    length = player.get_length()
    if length > 0:
        print("歌曲时长:", length // 1000, "秒")
    # 监听播放状态
    while True:
        state = player.get_state()
        if state in [vlc.State.Ended, vlc.State.Stopped, vlc.State.Error]:
            break
        time.sleep(0.5)
    print("播放结束。")

def main_loop():
    print("启动播放器，按 Ctrl+C 退出")
    while True:
        queue = fetch_queue()
        if not queue:
            print("队列为空，等待10秒...")
            time.sleep(10)
            continue
        song = queue[0]
        url = fetch_url(song["song_id"])
        if not url:
            print("无法获取播放地址，标记已播放并跳过")
            mark_played(song["request_id"])
            time.sleep(2)
            continue
        play_stream(url)
        mark_played(song["request_id"])
        time.sleep(2)

if __name__ == "__main__":
    main_loop()