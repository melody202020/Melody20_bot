import os
import json
import subprocess
import glob
import re
import time
import requests
from config import DOWNLOAD_PATH


class MusicService:
    def __init__(self):
        os.makedirs(DOWNLOAD_PATH, exist_ok=True)

    def search(self, query: str, limit: int = 8) -> list[dict]:
        print(f"[SEARCH] Query: {query}")

        yt_tracks = self._search_youtube(query, limit)
        if yt_tracks:
            print(f"[SEARCH] YouTube: {len(yt_tracks)} results")
            return yt_tracks

        print("[SEARCH] YouTube failed, trying SoundCloud")
        return self._search_soundcloud(query, limit)

    def _search_soundcloud(self, query: str, limit: int = 8) -> list[dict]:
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--dump-json",
            "--no-warnings",
            "--no-check-certificates",
            "--force-ipv4",
            f"scsearch{limit}:{query}",
        ]

        for attempt in range(2):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0 and result.stdout.strip():
                    tracks = []
                    for line in result.stdout.strip().split("\n"):
                        if line:
                            try:
                                data = json.loads(line)
                                duration = data.get("duration", 0) or 0
                                webpage_url = data.get("webpage_url") or data.get("url", "")
                                tracks.append({
                                    "id": data.get("id"),
                                    "title": data.get("title", "ناشناس"),
                                    "artist": data.get("uploader", "ناشناس"),
                                    "duration": int(duration),
                                    "url": webpage_url,
                                })
                            except:
                                continue
                    if tracks:
                        return tracks
                time.sleep(1)
            except Exception as e:
                print(f"[SC_SEARCH] error: {e}")
                time.sleep(2)
        return []

    def _search_youtube(self, query: str, limit: int = 8) -> list[dict]:
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--dump-json",
            "--no-warnings",
            "--no-check-certificates",
            "--force-ipv4",
            f"ytsearch{limit}:{query}",
        ]

        for attempt in range(2):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0 and result.stdout.strip():
                    tracks = []
                    for line in result.stdout.strip().split("\n"):
                        if line:
                            try:
                                data = json.loads(line)
                                duration = data.get("duration", 0) or 0
                                title = data.get("title", "ناشناس")
                                artist = data.get("uploader", "ناشناس")

                                if any(k in title.lower() for k in query.lower().split()):
                                    priority = 0
                                else:
                                    priority = 1

                                tracks.append({
                                    "id": data.get("id"),
                                    "title": title,
                                    "artist": artist,
                                    "duration": int(duration),
                                    "url": f"https://www.youtube.com/watch?v={data.get('id')}",
                                    "priority": priority,
                                })
                            except:
                                continue
                    if tracks:
                        tracks.sort(key=lambda x: x["priority"])
                        return tracks
                time.sleep(1)
            except Exception as e:
                print(f"[YT_SEARCH] error: {e}")
                time.sleep(2)
        return []

    def download_with_progress(self, url: str, output_name: str, progress_callback=None, track_info=None) -> str | None:
        print(f"[DOWNLOAD] URL: {url}")

        is_soundcloud = "soundcloud.com" in url or "api.soundcloud.com" in url
        is_youtube = "youtube.com" in url or "youtu.be" in url

        if is_soundcloud:
            print("[DOWNLOAD] SoundCloud direct...")
            filepath = self._download_soundcloud(url, output_name, progress_callback)
            if filepath:
                return filepath

        if is_youtube:
            clients = ["mediaconnect", "android", "tv_embedded"]
            for client in clients:
                print(f"[DOWNLOAD] YouTube ({client})...")
                filepath = self._download_youtube(url, output_name, progress_callback, client)
                if filepath:
                    return filepath

        print("[DOWNLOAD] Trying yt-dlp direct...")
        filepath = self._download_yt_dlp(url, output_name, progress_callback)
        if filepath:
            return filepath

        if track_info and is_youtube:
            artist = track_info.get('artist', '').strip()
            title = track_info.get('title', '').strip()
            title = self._clean_title(title)
            search_query = f"{artist} {title}".strip()
            print(f"[DOWNLOAD] YouTube failed, SoundCloud: {search_query}")
            sc_results = self._search_soundcloud(search_query, limit=3)
            if sc_results:
                sc_url = sc_results[0].get('url')
                if sc_url:
                    filepath = self._download_soundcloud(sc_url, output_name, progress_callback)
                    if filepath:
                        return filepath

        print("[DOWNLOAD] ALL FAILED")
        return None

    def _clean_title(self, title):
        import re
        title = re.sub(r'[^\w\s\u0600-\u06FF-]', ' ', title)
        title = re.sub(r'\s+', ' ', title).strip()
        words = title.split()
        clean = []
        skip = {'official', 'video', 'music', 'audio', 'lyric', 'lyrics', 'hd', '4k', 'remaster',
                'clip', 'vevo', 'live', 'cover', 'remix', 'feat', 'ft', 'mp3', 'download',
                'subscribe', 'channel', 'album', 'single', 'premiere', 'official video',
                'official audio', 'mv', 'stereo', 'mono', 'original', 'version'}
        for w in words:
            if w.lower().strip(',.!?:;()[]{}') not in skip:
                clean.append(w)
        return ' '.join(clean).strip()

    def _download_soundcloud(self, url, output_name, progress_callback=None):
        output_path = os.path.join(DOWNLOAD_PATH, output_name)

        cmd = [
            "yt-dlp", "-x",
            "--audio-format", "mp3",
            "--audio-quality", "128K",
            "-o", f"{output_path}.%(ext)s",
            "--no-playlist", "--newline",
            "--no-check-certificates",
            "--force-ipv4",
            url,
        ]

        try:
            if progress_callback:
                progress_callback(5)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            print(f"[SC_DL] code={result.returncode}")

            if result.returncode == 0:
                return self._find_mp3(output_name, progress_callback)
            else:
                print(f"[SC_DL] err: {result.stderr[-150:]}")

        except subprocess.TimeoutExpired:
            print("[SC_DL] TIMEOUT")
        except Exception as e:
            print(f"[SC_DL] error: {e}")
        return None

    def _download_youtube(self, url, output_name, progress_callback=None, client="mediaconnect"):
        output_path = os.path.join(DOWNLOAD_PATH, output_name)

        cmd = [
            "yt-dlp", "-x",
            "--audio-format", "mp3",
            "--audio-quality", "128K",
            "-o", f"{output_path}.%(ext)s",
            "--no-playlist", "--newline",
            "--no-check-certificates",
            "--force-ipv4", "--retries", "3",
            "--user-agent", "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
            "--extractor-args", f"youtube:player_client={client}",
            url,
        ]

        try:
            if progress_callback:
                progress_callback(5)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            print(f"[YT_DL] code={result.returncode}")

            if result.returncode == 0:
                return self._find_mp3(output_name, progress_callback)
            else:
                print(f"[YT_DL] err: {result.stderr[-150:]}")

        except subprocess.TimeoutExpired:
            print("[YT_DL] TIMEOUT")
        except Exception as e:
            print(f"[YT_DL] error: {e}")
        return None

    def _download_yt_dlp(self, url, output_name, progress_callback=None):
        output_path = os.path.join(DOWNLOAD_PATH, output_name)

        cmd = [
            "yt-dlp", "-x",
            "--audio-format", "mp3",
            "--audio-quality", "128K",
            "-o", f"{output_path}.%(ext)s",
            "--no-playlist", "--newline",
            "--no-check-certificates",
            "--force-ipv4", "--retries", "3",
            url,
        ]

        try:
            if progress_callback:
                progress_callback(5)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            print(f"[DL] code={result.returncode}")

            if result.returncode == 0:
                return self._find_mp3(output_name, progress_callback)
            else:
                print(f"[DL] err: {result.stderr[-150:]}")

        except subprocess.TimeoutExpired:
            print("[DL] TIMEOUT")
        except Exception as e:
            print(f"[DL] error: {e}")
        return None

    def _find_mp3(self, output_name, progress_callback=None):
        mp3_files = glob.glob(os.path.join(DOWNLOAD_PATH, f"{output_name}*.mp3"))
        if mp3_files:
            filepath = mp3_files[0]
            size = os.path.getsize(filepath)
            print(f"[FOUND] {filepath} ({size} bytes)")
            if progress_callback:
                progress_callback(100)
            return filepath

        for ext in ['*.webm', '*.m4a', '*.opus']:
            files = glob.glob(os.path.join(DOWNLOAD_PATH, f"{output_name}{ext}"))
            for f in files:
                new_name = f.rsplit('.', 1)[0] + '.mp3'
                try:
                    os.rename(f, new_name)
                    return new_name
                except:
                    pass
        return None

    def compress_file(self, filepath, max_size_mb=50):
        file_size = os.path.getsize(filepath)
        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size <= max_size_bytes:
            return filepath

        compressed_path = filepath.replace('.mp3', '_compressed.mp3')
        bitrate = 64 if file_size > 100*1024*1024 else (96 if file_size > 70*1024*1024 else 128)

        cmd = ["ffmpeg", "-i", filepath, "-codec:a", "libmp3lame", "-b:a", f"{bitrate}k", "-y", compressed_path]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                if os.path.getsize(compressed_path) <= max_size_bytes:
                    os.remove(filepath)
                    return compressed_path
                os.remove(compressed_path)
        except Exception as e:
            print(f"Compress error: {e}")
        return filepath

    def download(self, url, output_name):
        return self.download_with_progress(url, output_name)
