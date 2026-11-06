"""
Daemon Pemantau Otomatis Terpadu (Real-time Watcher) untuk:
1. Google Form Motion Grafis 3 Menit (03_Antrian_Google_Form_MotionGrafis)
2. Antrian Video NotebookLM / Buku Pelajaran (01_Antrian_NotebookLM):
   - Tanpa Subtitle
   - Thumbnail Sisi Kanan memakai Gambar Cover Buku Resmi (dari Google Drive buku / internet)
   - Akhiran Judul Seragam (contoh: I PAIBP 5 I Bab 1, I Fikih 5 I Bab 1, I SKI 7 I Bab 1, dst.)
   - Penempatan & Pembuatan Playlist Otomatis sesuai Mapel & Kelas
   - Jadwal Tayang Terpadu (Prime Time 05:00, 12:00, 19:00 WIB) yang tidak pernah bentrok!
"""

import os
import sys
import time
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

from pipeline import (
    run_queue_pipeline,
    TZ_WIB,
)


def run_forever_watcher(poll_seconds: int = 120):
    if not os.environ.get("GEMINI_API_KEY"):
        key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gemini_api_key.txt")
        if os.path.exists(key_file):
            with open(key_file, "r", encoding="utf-8") as kf:
                os.environ["GEMINI_API_KEY"] = kf.read().strip()

    print("=================================================================")
    print("[AUTO WATCHER TERPADU AKTIF] Memantau Google Form Motion Grafis & Antrian Video NotebookLM...")
    print("=================================================================")

    while True:
        try:
            now_str = datetime.now(TZ_WIB).strftime("%Y-%m-%d %H:%M:%S WIB")
            print(f"\n[{now_str}] Mengecek antrian Google Form Motion Grafis & 01_Antrian_NotebookLM...")
            run_queue_pipeline()
        except Exception as e:
            err_msg = str(e)
            print(f"[WATCHER PERINGATAN] {err_msg}")
            if "quotaExceeded" in err_msg or "uploadLimitExceeded" in err_msg:
                print("[INFO KUOTA] Kuota harian YouTube API sedang penuh (reset setiap pukul 15:00 WIB). Menunggu 30 menit...")
                time.sleep(1800)
                continue

        time.sleep(poll_seconds)


if __name__ == "__main__":
    run_forever_watcher()
