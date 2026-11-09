"""
Pipeline Utama Otomatisasi Cloud (Tanpa Komputer Menyala & Pakai Google Drive 2 TB)
Untuk Channel YouTube: Islamic K1 (https://www.youtube.com/@islamick1832)

Fitur Utama:
1. Menggunakan penyimpanan Google Drive Pro (2 TB) tanpa membebani penyimpanan komputer lokal.
2. Anti-Duplikat 3 Lapis: Mengecek langsung seluruh video di channel YouTube Islamic K1,
   mengecek database riwayat MD5/File ID di Google Drive, dan memindahkan file yang sudah selesai.
3. Mengambil & memproses SATU PER SATU video secara berurutan (bukan sekaligus) hingga tuntas.
4. Mengedit video otomatis:
   - Transkrip/Subtitle dengan font "Mala's Handwriting" ukuran kecil di tengah bawah.
   - Memotong 4 detik terakhir (menghapus logo NotebookLM).
   - Menyambung video "SUBSCRIBE ISLAMIC K1.mp4".
   - Menempelkan "logo.png" ukuran kecil di pojok kanan atas sepanjang video.
   - Membuat Thumbnail YouTube menarik secara otomatis.
5. Mengunggah ke YouTube Islamic K1 lengkap dengan:
   - Judul & Deskripsi Islami (minimal 3 paragraf, diawali & diakhiri salam, audiens keluarga Muslim).
   - Timeline/Chapters (sangat detail untuk >20 menit, standar untuk <=20 menit).
   - Hashtag & Tags sesuai aturan resmi YouTube.
   - Pengaturan Playlist otomatis sesuai Kelas PAI (PAI Kelas 1 s/d 9) atau topik kajian.
   - Terjemahan multi-bahasa dunia (localizations + subtitle CC).
   - Penjadwalan jam tayang terbaik (Prime Time) secara berurutan agar optimal & patuh kebijakan YouTube.
"""

import os
import io
import re
import csv
import time
import json
import socket
import shutil
import hashlib
import zipfile
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple

# Paksa penggunaan IPv4 di server GitHub Actions (mencegah Errno 101 Network is unreachable pada IPv6)
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)


socket.getaddrinfo = _ipv4_only_getaddrinfo

try:
    import pytz
    TZ_WIB = pytz.timezone("Asia/Jakarta")
    TZ_UTC = pytz.UTC
except ImportError:
    TZ_WIB = timezone(timedelta(hours=7))
    TZ_UTC = timezone.utc
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from video_editor import (
    get_video_duration,
    create_ass_subtitle,
    create_srt_subtitle,
    render_final_video,
    generate_youtube_thumbnail,
)
from ai_metadata_generator import analyze_video_with_gemini
from book_cover_helper import (
    parse_textbook_metadata,
    format_uniform_youtube_title,
    get_book_cover_image,
    determine_target_playlist_titles,
)
from motion_explainer_generator import build_complete_explainer_package

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/drive",
]

DRIVE_ROOT_FOLDER = "IslamicK1_Automation"
DRIVE_ASSETS_FOLDER = "00_Assets"
DRIVE_QUEUE_FOLDER = "01_Antrian_NotebookLM"
DRIVE_DONE_FOLDER = "02_Sudah_Diupload_YouTube"
DRIVE_FORM_QUEUE_FOLDER = "03_Antrian_Google_Form_MotionGrafis"
FORM_SHEET_NAME = "Form_Motion_Grafis_IslamicK1"
HISTORY_FILENAME = "upload_history_islamick1.json"

EXPECTED_CHANNEL_ID = "UCFxO6uyHmGJ38kDEF1vDrBg"  # Channel Resmi: Islamic K1 (@islamick1832)

# Peta Playlist Resmi per Kelas PAI di Channel Islamic K1
PAI_CLASS_PLAYLIST_IDS: Dict[int, List[Tuple[str, str]]] = {
    1: [
        ("PAI SD Kelas 1 (K13 & Merdeka)", "PL6yLAt6QbJhU4zw-XcnzMB6CCYX8qJVxY"),
        ("PAI SD Kelas 1", "PL6yLAt6QbJhXaCykdiAKXk6Udd6Mf8int"),
    ],
    2: [
        ("PAI SD Kelas 2 (K13 & Merdeka)", "PL6yLAt6QbJhVGm8V8_tu19d5FodXvpQfb"),
        ("PAI SD Kelas 2", "PL6yLAt6QbJhUhe1sngLWM0UCLev28_pRQ"),
    ],
    3: [
        ("PAI SD Kelas 3 (K13 & Merdeka)", "PL6yLAt6QbJhVP3mdALP_ait1VHMxcUZKF"),
        ("PAI SD Kelas 3", "PL6yLAt6QbJhUE1F2lpaNKiOVQxOoi-sUJ"),
    ],
    4: [
        ("PAI SD Kelas 4 (K13 & Merdeka)", "PL6yLAt6QbJhUwDz3me74f7XR-O30yylh8"),
        ("PAI SD Kelas 4", "PL6yLAt6QbJhWUJKrDWj6CkUsqOzMKO1ZT"),
    ],
    5: [
        ("PAI SD Kelas 5 (K13 & Merdeka)", "PL6yLAt6QbJhXhfxYLYeBdrn5YB6NDXgV3"),
        ("PAI SD Kelas 5", "PL6yLAt6QbJhWmDVwH6T19EBoeGtMqGhG2"),
    ],
    6: [
        ("PAI SD Kelas 6 (K13 & Merdeka)", "PL6yLAt6QbJhX3IVDspDZ6hiQCCzGafKZr"),
        ("PAI SD Kelas 6", "PL6yLAt6QbJhV2D2fqn9lu4CbDniDodJV-"),
    ],
    7: [
        ("PAI SMP Kelas 7 (K13 & Merdeka)", "PL6yLAt6QbJhWIKbm42UvfG48xOSkkWChS"),
        ("PAI SMP Kelas 7", "PL6yLAt6QbJhUdqHrR0RYv__vfqxrgwl5U"),
    ],
    8: [
        ("PAI SMP Kelas 8 (K13 & Merdeka)", "PL6yLAt6QbJhWBy-K6KkwQyL_T9y5paSvn"),
        ("PAI SMP Kelas 8", "PL6yLAt6QbJhVd4HSFARLk91s6NJ5E7VJs"),
    ],
    9: [
        ("PAI SMP Kelas 9 (K13 & Merdeka)", "PL6yLAt6QbJhVU_zLfOZmqycinkcsIuB3G"),
        ("PAI SMP Kelas 9", "PL6yLAt6QbJhU0URYr6NNSsVJ3dtt7bT3Y"),
    ],
}


def _load_creds(
    env_var_name: str,
    local_filename: str,
    fallback_env: str = "GOOGLE_TOKEN_JSON",
    fallback_file: str = "token.json",
) -> Credentials:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_in_script_dir = os.path.join(script_dir, local_filename)
    fallback_in_script_dir = os.path.join(script_dir, fallback_file)

    raw_json = os.environ.get(env_var_name) or os.environ.get(fallback_env)
    if raw_json:
        creds = Credentials.from_authorized_user_info(json.loads(raw_json.lstrip("\ufeff")))
    elif os.path.exists(local_filename):
        with open(local_filename, "r", encoding="utf-8-sig") as f:
            creds = Credentials.from_authorized_user_info(json.load(f))
    elif os.path.exists(local_in_script_dir):
        with open(local_in_script_dir, "r", encoding="utf-8-sig") as f:
            creds = Credentials.from_authorized_user_info(json.load(f))
    elif os.path.exists(fallback_file):
        with open(fallback_file, "r", encoding="utf-8-sig") as f:
            creds = Credentials.from_authorized_user_info(json.load(f))
    elif os.path.exists(fallback_in_script_dir):
        with open(fallback_in_script_dir, "r", encoding="utf-8-sig") as f:
            creds = Credentials.from_authorized_user_info(json.load(f))
    else:
        raise RuntimeError(f"Token otorisasi ({local_filename} / {env_var_name}) tidak ditemukan!")

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def get_google_services():
    """
    Inisialisasi koneksi terpisah untuk:
    - Google Drive 2 TB (Akun utama ary.fahra@gmail.com)
    - Channel YouTube Brand Account Islamic K1 (@islamick1832)
    """
    drive_creds = _load_creds("GOOGLE_DRIVE_TOKEN_JSON", "token_drive.json")
    yt_creds = _load_creds("YOUTUBE_TOKEN_JSON", "token_youtube.json")

    youtube = build("youtube", "v3", credentials=yt_creds)
    drive = build("drive", "v3", credentials=drive_creds)
    return youtube, drive


def ensure_drive_folder(drive, folder_name: str, parent_id: Optional[str] = None) -> str:
    """Mencari atau membuat folder di Google Drive secara otomatis."""
    escaped = folder_name.replace("'", "\\'")
    query = f"name = '{escaped}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    res = drive.files().list(q=query, fields="files(id, name)", pageSize=5).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]

    meta: Dict[str, Any] = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        meta["parents"] = [parent_id]

    folder = drive.files().create(body=meta, fields="id").execute()
    return folder["id"]


def download_drive_file(drive, file_id: str, dest_path: str) -> str:
    """Mengunduh file dari Google Drive ke folder sementara di Cloud Worker."""
    request = drive.files().get_media(fileId=file_id)
    with io.FileIO(dest_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request, chunksize=10 * 1024 * 1024)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    return dest_path


def load_upload_history(drive, root_folder_id: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """Membaca file database riwayat upload dari Google Drive."""
    query = f"name = '{HISTORY_FILENAME}' and '{root_folder_id}' in parents and trashed = false"
    res = drive.files().list(q=query, fields="files(id, name)").execute()
    files = res.get("files", [])
    if not files:
        return {"uploaded_files": {}, "last_scheduled_iso": None, "cached_youtube_videos": []}, None

    file_id = files[0]["id"]
    temp_json = tempfile.mktemp(suffix=".json")
    download_drive_file(drive, file_id, temp_json)
    with open(temp_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    os.remove(temp_json)
    return data, file_id


def save_upload_history(
    drive, root_folder_id: str, history_data: Dict[str, Any], history_file_id: Optional[str]
) -> Optional[str]:
    """Menyimpan pembaruan database riwayat upload kembali ke Google Drive."""
    temp_json = tempfile.mktemp(suffix=".json")
    with open(temp_json, "w", encoding="utf-8") as f:
        json.dump(history_data, f, indent=2, ensure_ascii=False)

    media = MediaFileUpload(temp_json, mimetype="application/json", resumable=False)
    if history_file_id:
        drive.files().update(fileId=history_file_id, media_body=media).execute()
        new_id = history_file_id
    else:
        meta = {"name": HISTORY_FILENAME, "parents": [root_folder_id]}
        created = drive.files().create(body=meta, media_body=media, fields="id").execute()
        new_id = created["id"]
    del media
    try:
        os.remove(temp_json)
    except OSError:
        pass
    return new_id


def normalize_key(text: str) -> str:
    """Normalisasi teks untuk perbandingan anti-duplikat yang akurat."""
    base = os.path.splitext(text)[0].lower()
    return re.sub(r"[^a-z0-9]+", "", base)


def fetch_existing_youtube_videos(youtube, cached_videos: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
    """
    Mengambil daftar seluruh video yang sudah ada di channel YouTube Islamic K1
    agar JANGAN SAMPAI ada video yang terupload ulang.
    Jika kuota harian YouTube API sedang penuh (403 quotaExceeded), otomatis menggunakan cached_videos.
    """
    existing_map = {v["video_id"]: v for v in (cached_videos or []) if "video_id" in v}
    try:
        ch_res = youtube.channels().list(part="contentDetails,snippet", mine=True).execute()
    except HttpError as e:
        if "quotaExceeded" in str(e) or "uploadLimitExceeded" in str(e):
            print("[INFO KUOTA HARIAN] Kuota harian YouTube API (10.000 poin/hari) sudah terpakai maksimal hari ini.")
            raise
        raise

    items = ch_res.get("items", [])
    if not items:
        raise RuntimeError("Channel YouTube tidak ditemukan pada token ini.")

    channel_id = items[0]["id"]
    channel_title = items[0]["snippet"]["title"]
    if channel_id != EXPECTED_CHANNEL_ID:
        raise RuntimeError(
            f"KEAMANAN: Token terhubung ke channel '{channel_title}' ({channel_id}), "
            f"bukan 'Islamic K1' ({EXPECTED_CHANNEL_ID}). Upload dibatalkan!"
        )

    print(f"[INFO] Terverifikasi Channel YouTube: {channel_title} (ID: {channel_id})")
    uploads_playlist_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    full_scan_needed = len(existing_map) < 100

    next_page = None
    pages_fetched = 0
    max_pages = 100 if full_scan_needed else 2

    while pages_fetched < max_pages:
        try:
            pl_res = (
                youtube.playlistItems()
                .list(
                    part="snippet,contentDetails",
                    playlistId=uploads_playlist_id,
                    maxResults=50,
                    pageToken=next_page,
                )
                .execute()
            )
        except HttpError as e:
            if "quotaExceeded" in str(e):
                print("[INFO KUOTA HARIAN] Kuota harian YouTube API sudah penuh saat memindai playlist.")
                raise
            raise
        for item in pl_res.get("items", []):
            title = item["snippet"]["title"]
            desc = item["snippet"].get("description", "")
            vid_id = item["contentDetails"]["videoId"]
            existing_map[vid_id] = {"video_id": vid_id, "title": title, "description": desc}

        pages_fetched += 1
        next_page = pl_res.get("nextPageToken")
        if not next_page:
            break

    all_videos = list(existing_map.values())
    print(f"[INFO] Database Anti-Duplikat memuat {len(all_videos)} video dari channel Islamic K1.")
    return all_videos


def _verify_youtube_video_still_exists(youtube, video_id: str) -> bool:
    """Memastikan video_id benar-benar masih ada di YouTube (tidak dihapus manual oleh pengguna)."""
    if not youtube or not video_id:
        return True
    try:
        res = youtube.videos().list(part="id", id=video_id).execute(num_retries=2)
        return bool(res.get("items"))
    except Exception:
        return True


def is_already_uploaded(
    drive_file: Dict[str, Any],
    history_data: Dict[str, Any],
    existing_yt_videos: List[Dict[str, str]],
    youtube=None,
) -> Tuple[bool, str]:
    """
    Pengecekan Anti-Duplikat 3 Lapis + Verifikasi Eksistensi Nyata di YouTube:
    Jika video tercatat di riwayat/cache namun ternyata sudah dihapus di YouTube,
    maka riwayat lama otomatis dibersihkan agar video dapat diupload kembali!
    """
    file_id = drive_file["id"]
    file_name = drive_file["name"]
    md5_checksum = drive_file.get("md5Checksum", "")
    norm_name = normalize_key(file_name)

    uploaded_map = history_data.get("uploaded_files", {})
    stale_keys = []
    for rec_key, rec_val in uploaded_map.items():
        matched_reason = ""
        if rec_key == file_id:
            matched_reason = f"File ID {file_id} sudah tercatat di riwayat upload."
        elif md5_checksum and rec_val.get("md5Checksum") == md5_checksum:
            matched_reason = f"MD5 Checksum identik dengan video '{rec_val.get('original_name')}' yang sudah diupload."
        elif norm_name and normalize_key(rec_val.get("original_name", "")) == norm_name:
            matched_reason = f"Nama file '{file_name}' sudah pernah diupload sebelumnya."

        if matched_reason:
            vid_id = rec_val.get("youtube_video_id", "")
            if vid_id and not _verify_youtube_video_still_exists(youtube, vid_id):
                print(f"[RE-UPLOAD] Video '{file_name}' ({vid_id}) tercatat di riwayat tapi sudah tidak ada di YouTube. Memproses ulang!")
                stale_keys.append(rec_key)
                continue
            return True, matched_reason

    for sk in stale_keys:
        uploaded_map.pop(sk, None)

    stale_yt_ids = set()
    for yt_vid in existing_yt_videos:
        yt_norm_title = normalize_key(yt_vid["title"])
        matched_yt = False
        reason_yt = ""
        if len(norm_name) >= 6 and (norm_name == yt_norm_title or norm_name in yt_norm_title):
            matched_yt = True
            reason_yt = f"Sudah ada di channel YouTube dengan judul '{yt_vid['title']}' ({yt_vid['video_id']})."
        elif md5_checksum and f"[Ref:{md5_checksum[:10]}]" in yt_vid.get("description", ""):
            matched_yt = True
            reason_yt = f"Checksum referensi ditemukan di video YouTube {yt_vid['video_id']}."

        if matched_yt:
            vid_id = yt_vid.get("video_id", "")
            if vid_id and not _verify_youtube_video_still_exists(youtube, vid_id):
                print(f"[RE-UPLOAD] Cache video '{yt_vid.get('title')}' ({vid_id}) sudah dihapus dari YouTube. Memproses ulang!")
                stale_yt_ids.add(vid_id)
                continue
            return True, reason_yt

    if stale_yt_ids:
        existing_yt_videos[:] = [v for v in existing_yt_videos if v.get("video_id") not in stale_yt_ids]
        history_data["cached_youtube_videos"] = existing_yt_videos

    return False, ""


def move_drive_file(drive, file_id: str, old_folder_id: str, new_folder_id: str):
    """Memindahkan file dari folder Antrian ke folder Sudah_Diupload di Google Drive."""
    drive.files().update(
        fileId=file_id,
        addParents=new_folder_id,
        removeParents=old_folder_id,
        fields="id, parents",
    ).execute()


_CHANNEL_PLAYLIST_CACHE: Dict[str, str] = {}
_PLAYLIST_VIDEOS_CACHE: Dict[str, set] = {}


def _get_or_create_playlist_id(youtube, playlist_title: str) -> Optional[str]:
    """
    Mencari ID Playlist di channel Islamic K1 berdasarkan nama (case-insensitive).
    Jika belum ada (misal 'PAI SMA Kelas 10 (K13 & Merdeka)', 'Fikih Kelas 5 (K13 & Merdeka)',
    atau 'Kajian & Materi Ushul Fiqh'), otomatis membuatkan Playlist baru di YouTube!
    """
    global _CHANNEL_PLAYLIST_CACHE
    norm_title = playlist_title.strip().lower()

    # Cek dulu di kamus tetap PAI Kelas 1-9
    for _, pl_list in PAI_CLASS_PLAYLIST_IDS.items():
        for t, pid in pl_list:
            _CHANNEL_PLAYLIST_CACHE[t.strip().lower()] = pid

    if norm_title in _CHANNEL_PLAYLIST_CACHE:
        return _CHANNEL_PLAYLIST_CACHE[norm_title]

    # Muat daftar playlist yang ada di channel YouTube
    next_page = None
    while True:
        res = youtube.playlists().list(part="snippet", mine=True, maxResults=50, pageToken=next_page).execute(num_retries=3)
        for pl in res.get("items", []):
            t = pl["snippet"]["title"].strip()
            _CHANNEL_PLAYLIST_CACHE[t.lower()] = pl["id"]
        if norm_title in _CHANNEL_PLAYLIST_CACHE or not res.get("nextPageToken"):
            break
        next_page = res.get("nextPageToken")

    if norm_title in _CHANNEL_PLAYLIST_CACHE:
        return _CHANNEL_PLAYLIST_CACHE[norm_title]

    # Jika belum ada di channel, buatkan Playlist baru secara otomatis
    body = {
        "snippet": {
            "title": playlist_title.strip(),
            "description": (
                f"Kumpulan lengkap video pembelajaran dan kajian {playlist_title.strip()} "
                "untuk Pelajar & Keluarga Muslim di channel Islamic K1."
            ),
            "defaultLanguage": "id",
        },
        "status": {"privacyStatus": "public"},
    }
    created = youtube.playlists().insert(part="snippet,status", body=body).execute(num_retries=3)
    new_id = created["id"]
    _CHANNEL_PLAYLIST_CACHE[norm_title] = new_id
    print(f"[PLAYLIST BARU] Berhasil membuat Playlist baru di YouTube: '{playlist_title}' ({new_id})")
    return new_id


def _is_video_in_playlist(youtube, playlist_id: str, video_id: str) -> bool:
    """Mengecek apakah video_id sudah ada di dalam playlist_id agar tidak terduplikasi di playlist."""
    global _PLAYLIST_VIDEOS_CACHE
    if playlist_id not in _PLAYLIST_VIDEOS_CACHE:
        vids = set()
        next_page = None
        while True:
            try:
                res = (
                    youtube.playlistItems()
                    .list(part="contentDetails", playlistId=playlist_id, maxResults=50, pageToken=next_page)
                    .execute(num_retries=3)
                )
                for item in res.get("items", []):
                    vids.add(item["contentDetails"]["videoId"])
                next_page = res.get("nextPageToken")
                if not next_page:
                    break
            except Exception:
                break
        _PLAYLIST_VIDEOS_CACHE[playlist_id] = vids
    return video_id in _PLAYLIST_VIDEOS_CACHE[playlist_id]


def add_video_to_matching_playlists(youtube, video_id: str, original_filename: str, ai_playlist_name: str):
    """
    Memasukkan video ke Playlist yang tepat sesuai Mata Pelajaran & Kelasnya (Kelas 1 s/d 12,
    PAIBP, Fikih, Ushul Fiqh, Akidah Akhlak, Al-Qur'an Hadis, SKI, Bahasa Arab, dll.).
    Jika Playlist belum ada di channel, otomatis dibuatkan.
    """
    target_titles = determine_target_playlist_titles(original_filename, ai_playlist_name)
    for pl_title in target_titles:
        try:
            pl_id = _get_or_create_playlist_id(youtube, pl_title)
            if not pl_id:
                continue
            if _is_video_in_playlist(youtube, pl_id, video_id):
                print(f"[PLAYLIST] Video {video_id} sudah ada di Playlist '{pl_title}' ({pl_id}).")
                continue
            youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": pl_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id},
                    }
                },
            ).execute(num_retries=3)
            _PLAYLIST_VIDEOS_CACHE.setdefault(pl_id, set()).add(video_id)
            print(f"[YOUTUBE] Video dimasukkan ke Playlist: '{pl_title}' ({pl_id})")
        except Exception as e:
            print(f"[PERINGATAN] Gagal menambahkan ke playlist '{pl_title}': {e}")


def compute_next_prime_time_utc(recommended_slot: str, last_scheduled_iso: Optional[str]) -> str:
    """
    Menentukan waktu tayang terjadwal (Scheduled Publish) pada jam Prime Time Keluarga Muslim (WIB / UTC+7):
    - SUBUH: 05:00 WIB
    - SIANG: 12:00 WIB
    - MALAM: 19:00 WIB
    Memastikan setiap video terbit berurutan satu per satu dengan jeda waktu yang ideal.
    """
    now_wib = datetime.now(TZ_WIB)

    prime_hours = [5, 12, 19]
    slot_map = {"SUBUH": 5, "SIANG": 12, "MALAM": 19}
    preferred_hour = slot_map.get(recommended_slot.upper(), 19)

    if not last_scheduled_iso:
        candidate = now_wib.replace(hour=preferred_hour, minute=0, second=0, microsecond=0)
        if candidate <= now_wib + timedelta(minutes=30):
            # Cari jam prime time terdekat berikutnya
            next_candidates = []
            for d_offset in [0, 1]:
                for h in prime_hours:
                    c = (now_wib + timedelta(days=d_offset)).replace(hour=h, minute=0, second=0, microsecond=0)
                    if c > now_wib + timedelta(minutes=30):
                        next_candidates.append(c)
            candidate = next_candidates[0]
    else:
        last_dt = datetime.fromisoformat(last_scheduled_iso.replace("Z", "+00:00")).astimezone(TZ_WIB)
        base_dt = max(now_wib + timedelta(minutes=30), last_dt)
        next_candidates = []
        for d_offset in [0, 1, 2]:
            for h in prime_hours:
                c = (base_dt + timedelta(days=d_offset)).replace(hour=h, minute=0, second=0, microsecond=0)
                if c > base_dt + timedelta(hours=3):
                    next_candidates.append(c)
        candidate = next_candidates[0]

    candidate_utc = candidate.astimezone(TZ_UTC)
    return candidate_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def prepare_assets(drive, assets_folder_id: str, work_dir: str) -> Tuple[str, str, str]:
    """
    Menyiapkan 3 file aset wajib (logo.png, SUBSCRIBE ISLAMIC K1.mp4, Mala's Handwriting.otf):
    Mengambil dari folder lokal jika tersedia, atau mengunduh dari folder `00_Assets` di Google Drive.
    Juga menginstal font Mala's Handwriting ke sistem fontconfig agar FFmpeg libass mengenalinya 100%.
    """
    local_logo = r"E:\ISLAMIC K1\logo.png"
    local_outro = r"E:\ISLAMIC K1\SUBSCRIBE ISLAMIC K1.mp4"
    local_font = os.path.expanduser(r"~\AppData\Local\Microsoft\Windows\Fonts\Mala's Handwriting.otf")

    bundled_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    logo_dest = os.path.join(work_dir, "logo.png")
    outro_dest = os.path.join(work_dir, "SUBSCRIBE ISLAMIC K1.mp4")
    font_dest = os.path.join(work_dir, "MalaHandwriting.otf")

    for src, dst, drive_name in [
        (local_logo, logo_dest, "logo.png"),
        (local_outro, outro_dest, "SUBSCRIBE ISLAMIC K1.mp4"),
        (local_font, font_dest, "Mala's Handwriting.otf"),
    ]:
        bundled_candidate = os.path.join(bundled_dir, drive_name)
        if os.path.exists(src):
            shutil.copy2(src, dst)
        elif os.path.exists(bundled_candidate):
            shutil.copy2(bundled_candidate, dst)
        else:
            escaped_drive_name = drive_name.replace("'", "\\'")
            q = f"name = '{escaped_drive_name}' and '{assets_folder_id}' in parents and trashed = false"
            res = drive.files().list(q=q, fields="files(id, name)").execute()
            files = res.get("files", [])
            if not files:
                raise FileNotFoundError(
                    f"Aset wajib '{drive_name}' belum ada di folder Google Drive '{DRIVE_ROOT_FOLDER}/{DRIVE_ASSETS_FOLDER}'."
                )
            download_drive_file(drive, files[0]["id"], dst)

    # Pasang font ke direktori font user di Linux agar libass FFmpeg langsung mengenali "Mala's Handwriting"
    try:
        user_fonts_dir = os.path.expanduser("~/.local/share/fonts")
        os.makedirs(user_fonts_dir, exist_ok=True)
        shutil.copy2(font_dest, os.path.join(user_fonts_dir, "MalaHandwriting.otf"))
        subprocess.run(["fc-cache", "-f"], check=False)
    except Exception:
        pass

    return logo_dest, outro_dest, font_dest


def _make_form_request_id(title: str, audience: str) -> Tuple[str, str]:
    """Membuat kunci unik & kode referensi 10 karakter untuk setiap permintaan dari Google Form."""
    norm_key = f"{normalize_key(title)}_{normalize_key(audience or 'keluargamuslim')}"
    ref_hash = hashlib.md5(norm_key.encode("utf-8")).hexdigest()[:10]
    return norm_key, f"GF_{ref_hash}"


def is_form_request_already_uploaded(
    title: str,
    audience: str,
    history_data: Dict[str, Any],
    existing_yt_videos: List[Dict[str, str]],
) -> Tuple[bool, str]:
    """
    Anti-Duplikat 3 Lapis untuk antrian Google Form Motion Grafis:
    1. Cek apakah kombinasi Judul + Audience sudah tercatat di `processed_form_requests` pada database Google Drive.
    2. Cek apakah kode referensi `[Ref:GF_...]` sudah ada di deskripsi video di channel YouTube Islamic K1.
    3. Cek apakah judul yang identik sudah terupload di channel YouTube Islamic K1.
    """
    norm_key, ref_tag = _make_form_request_id(title, audience)
    processed_forms = history_data.get("processed_form_requests", {})
    if norm_key in processed_forms:
        vid_id = processed_forms[norm_key].get("youtube_video_id", "")
        return True, f"Sudah pernah dibuat & diupload dari Google Form (YouTube ID: {vid_id})."

    norm_title = normalize_key(title)
    for yt_vid in existing_yt_videos:
        if f"[Ref:{ref_tag}]" in yt_vid.get("description", ""):
            return True, f"Kode referensi {ref_tag} sudah ada di video YouTube '{yt_vid['title']}' ({yt_vid['video_id']})."
        yt_norm_title = normalize_key(yt_vid["title"])
        if len(norm_title) >= 8 and norm_title == yt_norm_title:
            return True, f"Judul identik sudah ada di channel YouTube: '{yt_vid['title']}' ({yt_vid['video_id']})."

    return False, ""


def _extract_all_rows_from_spreadsheet(drive, sheet_id: str) -> List[List[List[str]]]:
    """
    Mengekstrak seluruh baris dari SEMUA tab/worksheet di dalam Google Spreadsheet
    (termasuk tab 'Jawaban Formulir 1' / 'Form Responses 1' maupun tab lainnya)
    menggunakan export .xlsx dan fallback .csv tanpa memerlukan Google Sheets API terpisah.
    """
    all_tables: List[List[List[str]]] = []

    # 1. Baca seluruh tab worksheet melalui export .xlsx
    try:
        xlsx_bytes = (
            drive.files()
            .export(
                fileId=sheet_id,
                mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            .execute(num_retries=3)
        )
        ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        with zipfile.ZipFile(io.BytesIO(xlsx_bytes)) as z:
            shared_strings: List[str] = []
            if "xl/sharedStrings.xml" in z.namelist():
                ss_root = ET.fromstring(z.read("xl/sharedStrings.xml"))
                for si in ss_root.iter(f"{ns}si"):
                    shared_strings.append("".join(t.text or "" for t in si.iter(f"{ns}t")))

            sheet_files = sorted(
                [name for name in z.namelist() if re.match(r"^xl/worksheets/sheet\d+\.xml$", name)]
            )
            for sf in sheet_files:
                ws_root = ET.fromstring(z.read(sf))
                table_rows: List[List[str]] = []
                for row_el in ws_root.iter(f"{ns}row"):
                    row_cells: Dict[int, str] = {}
                    max_col = -1
                    for c_el in row_el.iter(f"{ns}c"):
                        ref = c_el.attrib.get("r", "")
                        col_letters = "".join(ch for ch in ref if ch.isalpha()).upper()
                        col_idx = 0
                        for ch in col_letters:
                            col_idx = col_idx * 26 + (ord(ch) - ord("A") + 1)
                        col_idx = max(0, col_idx - 1)

                        c_type = c_el.attrib.get("t", "")
                        v_el = c_el.find(f"{ns}v")
                        is_el = c_el.find(f"{ns}is")
                        val = ""
                        if c_type == "s" and v_el is not None and v_el.text is not None:
                            s_i = int(v_el.text)
                            val = shared_strings[s_i] if s_i < len(shared_strings) else ""
                        elif c_type == "inlineStr" and is_el is not None:
                            val = "".join(t.text or "" for t in is_el.iter(f"{ns}t"))
                        elif v_el is not None and v_el.text is not None:
                            val = v_el.text
                        row_cells[col_idx] = val
                        if col_idx > max_col:
                            max_col = col_idx
                    if max_col >= 0:
                        table_rows.append([row_cells.get(i, "") for i in range(max_col + 1)])
                if table_rows:
                    all_tables.append(table_rows)
    except Exception:
        pass

    # 2. Fallback / tambahan dari export CSV tab pertama
    if not all_tables:
        try:
            raw_csv_bytes = drive.files().export(fileId=sheet_id, mimeType="text/csv").execute(num_retries=3)
            csv_text = raw_csv_bytes.decode("utf-8-sig", errors="replace")
            rows = list(csv.reader(io.StringIO(csv_text)))
            if rows:
                all_tables.append(rows)
        except Exception:
            pass

    return all_tables


def fetch_pending_google_form_requests(drive, root_id: str, form_queue_id: str) -> List[Dict[str, Any]]:
    """
    Membaca daftar permintaan pembuatan Video Motion Grafis 3 Menit dari 3 sumber:
    1. Input langsung `workflow_dispatch` GitHub Actions (jika dipicu instan oleh Google Form / Apps Script).
    2. Google Sheets hasil respon Google Form di Google Drive (`Form_Motion_Grafis_IslamicK1` / tab `Jawaban Formulir 1`).
    3. File `.json` yang masuk ke folder `03_Antrian_Google_Form_MotionGrafis` di Google Drive.
    """
    requests_list: List[Dict[str, Any]] = []
    seen_keys = set()

    # 1. Cek apakah ada input langsung dari trigger Google Form (workflow_dispatch environment variables)
    env_title = os.environ.get("FORM_TITLE", "").strip()
    env_audience = os.environ.get("FORM_AUDIENCE", "").strip()
    env_category = os.environ.get("FORM_CATEGORY", "").strip()
    if env_title:
        nk, ref_tag = _make_form_request_id(env_title, env_audience or "Keluarga Muslim")
        seen_keys.add(nk)
        requests_list.append(
            {
                "title": env_title,
                "audience": env_audience or "Keluarga & Pelajar Muslim",
                "category": env_category,
                "source": "workflow_dispatch",
                "drive_file_id": None,
                "norm_key": nk,
                "ref_tag": ref_tag,
            }
        )

    # 2. Cek Google Sheets yang terhubung dengan Google Form di Google Drive (membaca SEMUA tab termasuk 'Jawaban Formulir 1')
    sheet_query = (
        f"mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false and "
        f"(name contains '{FORM_SHEET_NAME}' or name contains 'Motion Grafis' or name contains 'Form_Motion_Grafis' "
        f"or '{root_id}' in parents or '{form_queue_id}' in parents)"
    )
    try:
        sheet_res = drive.files().list(q=sheet_query, fields="files(id, name)", pageSize=20).execute(num_retries=3)
        for sh in sheet_res.get("files", []):
            try:
                all_tables = _extract_all_rows_from_spreadsheet(drive, sh["id"])
                for rows in all_tables:
                    if len(rows) <= 1:
                        continue

                    header = [str(c).strip().lower() for c in rows[0]]
                    # Deteksi indeks kolom Judul Video, Target Audience, Kategori, & Status secara otomatis
                    title_idx = 1 if len(header) > 1 else 0
                    aud_idx = 2 if len(header) > 2 else -1
                    cat_idx = 3 if len(header) > 3 else -1
                    status_idx = -1

                    for i, col_name in enumerate(header):
                        if any(k in col_name for k in ["judul", "topik", "title", "topic", "materi"]):
                            title_idx = i
                        elif any(k in col_name for k in ["audience", "audiens", "target", "penonton", "sasaran", "kelas"]):
                            aud_idx = i
                        elif any(k in col_name for k in ["kategori", "jenis", "category"]):
                            cat_idx = i
                        elif any(k in col_name for k in ["status", "keterangan", "youtube"]):
                            status_idx = i

                    for row in rows[1:]:
                        if not row or len(row) <= title_idx:
                            continue
                        r_title = str(row[title_idx]).strip()
                        if not r_title or r_title.lower() in ("judul", "judul video", "topik"):
                            continue
                        if status_idx >= 0 and len(row) > status_idx:
                            st_val = str(row[status_idx]).strip().upper()
                            if "SUDAH" in st_val or "DONE" in st_val or "youtu.be" in st_val.lower():
                                continue
                        r_aud = (
                            str(row[aud_idx]).strip()
                            if (aud_idx >= 0 and len(row) > aud_idx and str(row[aud_idx]).strip())
                            else "Keluarga & Pelajar Muslim"
                        )
                        r_cat = str(row[cat_idx]).strip() if (cat_idx >= 0 and len(row) > cat_idx) else ""
                        nk, ref_tag = _make_form_request_id(r_title, r_aud)
                        if nk not in seen_keys:
                            seen_keys.add(nk)
                            requests_list.append(
                                {
                                    "title": r_title,
                                    "audience": r_aud,
                                    "category": r_cat,
                                    "source": f"Google Sheet ({sh['name']})",
                                    "drive_file_id": None,
                                    "norm_key": nk,
                                    "ref_tag": ref_tag,
                                }
                            )
            except Exception as sh_err:
                print(f"[PERINGATAN] Gagal membaca Google Sheet '{sh.get('name')}': {sh_err}")
    except Exception as list_err:
        print(f"[PERINGATAN] Gagal mencari Google Sheet antrian Form: {list_err}")

    # 3. Cek file .json di dalam folder 03_Antrian_Google_Form_MotionGrafis
    try:
        json_q = f"'{form_queue_id}' in parents and trashed = false and name contains '.json'"
        json_res = (
            drive.files()
            .list(q=json_q, fields="files(id, name, createdTime)", orderBy="createdTime asc", pageSize=30)
            .execute(num_retries=3)
        )
        for jf in json_res.get("files", []):
            tmp_p = tempfile.mktemp(suffix=".json")
            try:
                download_drive_file(drive, jf["id"], tmp_p)
                with open(tmp_p, "r", encoding="utf-8-sig") as f:
                    jdata = json.load(f)
                r_title = str(jdata.get("title") or jdata.get("judul") or "").strip()
                r_aud = str(jdata.get("audience") or jdata.get("target_audience") or "Keluarga & Pelajar Muslim").strip()
                r_cat = str(jdata.get("category") or jdata.get("kategori") or "").strip()
                if r_title:
                    nk, ref_tag = _make_form_request_id(r_title, r_aud)
                    if nk not in seen_keys:
                        seen_keys.add(nk)
                        requests_list.append(
                            {
                                "title": r_title,
                                "audience": r_aud,
                                "category": r_cat,
                                "source": f"Drive JSON ({jf['name']})",
                                "drive_file_id": jf["id"],
                                "norm_key": nk,
                                "ref_tag": ref_tag,
                            }
                        )
            except Exception as je:
                print(f"[PERINGATAN] Gagal membaca file JSON Form '{jf['name']}': {je}")
            finally:
                if os.path.exists(tmp_p):
                    os.remove(tmp_p)
    except Exception:
        pass

    return requests_list


def process_google_form_explainer_queue(
    gemini_api_key: str,
    root_id: str,
    assets_id: str,
    form_queue_id: str,
    done_id: str,
    history_data: Dict[str, Any],
    history_file_id: Optional[str],
    existing_yt_videos: List[Dict[str, str]],
) -> Tuple[int, Optional[str], bool]:
    """
    Memproses antrian pembuatan Video Motion Grafis Explainer 3 Menit dari Google Form SATU PER SATU,
    menggunakan database riwayat & jadwal tayang yang SAMA dengan pipeline NotebookLM agar 100% ANTI-BENTROK.
    Mengembalikan (jumlah_video_form_diproses, history_file_id_terbaru, kuota_youtube_habis).
    """
    youtube, drive = get_google_services()
    pending_requests = fetch_pending_google_form_requests(drive, root_id, form_queue_id)
    if not pending_requests:
        print("[GOOGLE FORM] Tidak ada antrian baru dari Google Form Motion Grafis.")
        return 0, history_file_id, False

    print(f"[GOOGLE FORM] Ditemukan {len(pending_requests)} entri dari Google Form. Memeriksa status anti-duplikat...")
    processed_form_count = 0

    for req in pending_requests:
        title = req["title"]
        audience = req["audience"]
        category = req["category"]
        norm_key = req["norm_key"]
        ref_tag = req["ref_tag"]
        drive_file_id = req.get("drive_file_id")

        already_done, reason = is_form_request_already_uploaded(title, audience, history_data, existing_yt_videos)
        if already_done:
            print(f"[SKIP GOOGLE FORM] '{title}' ({audience}) dilewati: {reason}")
            if drive_file_id:
                try:
                    move_drive_file(drive, drive_file_id, form_queue_id, done_id)
                except Exception:
                    pass
            continue

        print("=================================================================")
        print(f"[PROSES GOOGLE FORM #{processed_form_count + 1}] Judul: '{title}' | Audience: '{audience}'")
        print("=================================================================")

        try:
            with tempfile.TemporaryDirectory(prefix="islamick1_form_", ignore_cleanup_errors=True) as work_dir:
                logo_path, outro_path, font_path = prepare_assets(drive, assets_id, work_dir)

                pkg = build_complete_explainer_package(
                    topic_title=title,
                    target_audience=audience,
                    gemini_api_key=gemini_api_key,
                    logo_path=logo_path,
                    outro_path=outro_path,
                    font_path=font_path,
                    work_dir=work_dir,
                    category_hint=category,
                )

                # Simpan terlebih dahulu file video hasil render ke folder 03_Antrian_Google_Form_MotionGrafis di Google Drive
                # agar Anda bisa melihat videonya di folder antrian sebelum/saat proses upload ke YouTube!
                safe_t = re.sub(r'[\\/*?:"<>|]+', "", title).strip()[:60]
                safe_a = re.sub(r'[\\/*?:"<>|]+', "", audience).strip()[:30]
                drive_video_filename = f"MotionGrafis - {safe_t} ({safe_a}).mp4"
                escaped_vname = drive_video_filename.replace("'", "\\'")
                youtube, drive = get_google_services()

                q_existing_vid = f"name = '{escaped_vname}' and '{form_queue_id}' in parents and trashed = false"
                existing_vid_files = drive.files().list(q=q_existing_vid, fields="files(id, name)").execute(num_retries=3).get("files", [])
                if existing_vid_files:
                    rendered_drive_vid_id = existing_vid_files[0]["id"]
                    print(f"[DRIVE ANTRIAN] File '{drive_video_filename}' sudah ada di 03_Antrian_Google_Form_MotionGrafis ({rendered_drive_vid_id}).")
                else:
                    print(f"[DRIVE ANTRIAN] Menyimpan video hasil render '{drive_video_filename}' ke folder 03_Antrian_Google_Form_MotionGrafis...")
                    vid_media_drive = MediaFileUpload(pkg["final_video_path"], mimetype="video/mp4", resumable=True)
                    created_vid = drive.files().create(
                        body={"name": drive_video_filename, "parents": [form_queue_id]},
                        media_body=vid_media_drive,
                        fields="id",
                    ).execute(num_retries=5)
                    rendered_drive_vid_id = created_vid["id"]
                    del vid_media_drive
                    print(f"[DRIVE ANTRIAN] Tersimpan di 03_Antrian_Google_Form_MotionGrafis (ID: {rendered_drive_vid_id}).")

                publish_at_iso = compute_next_prime_time_utc(
                    recommended_slot=pkg.get("recommended_publish_slot", "MALAM"),
                    last_scheduled_iso=history_data.get("last_scheduled_iso"),
                )
                full_description = f"{pkg['full_description']}\n\n[Ref:{ref_tag}]"

                localizations_map = pkg.get("localizations", {})
                localizations_map["id"] = {
                    "title": pkg["title"][:100],
                    "description": full_description[:4900],
                }

                video_body = {
                    "snippet": {
                        "title": pkg["title"][:100],
                        "description": full_description[:4900],
                        "tags": pkg.get("tags", ["IslamicK1", "Keluarga Muslim", "Edukasi Islami"])[:15],
                        "categoryId": "27",
                        "defaultLanguage": "id",
                        "defaultAudioLanguage": "id",
                    },
                    "status": {
                        "privacyStatus": "private",
                        "publishAt": publish_at_iso,
                        "selfDeclaredMadeForKids": False,
                        "containsSyntheticMedia": True,
                        "embeddable": True,
                        "publicStatsViewable": True,
                    },
                    "localizations": localizations_map,
                }

                # Segarkan kembali koneksi Google & YouTube tepat sebelum upload
                youtube, drive = get_google_services()
                print(f"[YOUTUBE FORM] Mengunggah video Motion Grafis: '{pkg['title']}' (Jadwal Tayang: {publish_at_iso})...")
                media_video = MediaFileUpload(
                    pkg["final_video_path"], mimetype="video/mp4", chunksize=10 * 1024 * 1024, resumable=True
                )
                insert_req = youtube.videos().insert(
                    part="snippet,status,localizations",
                    body=video_body,
                    media_body=media_video,
                )
                response_yt = None
                while response_yt is None:
                    _, response_yt = insert_req.next_chunk(num_retries=5)
                del insert_req
                del media_video

                uploaded_video_id = response_yt["id"]
                print(f"[YOUTUBE FORM] Berhasil diunggah! Link: https://youtu.be/{uploaded_video_id}")
                print("[YOUTUBE FORM] Sesuai pengaturan: Tidak membuat/mengganti thumbnail otomatis (Thumbnail diatur manual oleh Anda).")

                # Masukkan ke Playlist yang sesuai
                try:
                    add_video_to_matching_playlists(
                        youtube=youtube,
                        video_id=uploaded_video_id,
                        original_filename=title,
                        ai_playlist_name=pkg.get("playlist_name", "Explainer Islami & Edukasi Keluarga Muslim"),
                    )
                except Exception as e:
                    print(f"[PERINGATAN] Gagal menambahkan ke playlist: {e}")

                # Catat ke riwayat upload terpadu (upload_history_islamick1.json) agar jadwal tidak pernah bentrok!
                history_data.setdefault("processed_form_requests", {})[norm_key] = {
                    "form_title": title,
                    "form_audience": audience,
                    "ref_tag": ref_tag,
                    "youtube_video_id": uploaded_video_id,
                    "youtube_title": pkg["title"],
                    "scheduled_publish_at": publish_at_iso,
                    "processed_at": datetime.now(TZ_UTC).isoformat(),
                }
                existing_yt_videos.append(
                    {
                        "video_id": uploaded_video_id,
                        "title": pkg["title"],
                        "description": full_description,
                    }
                )
                history_data["cached_youtube_videos"] = existing_yt_videos
                history_data["last_scheduled_iso"] = publish_at_iso
                history_file_id = save_upload_history(drive, root_id, history_data, history_file_id)

                # Pindahkan video hasil render dari 03_Antrian_Google_Form_MotionGrafis ke 02_Sudah_Diupload_YouTube
                if rendered_drive_vid_id:
                    try:
                        move_drive_file(drive, rendered_drive_vid_id, form_queue_id, done_id)
                        print(f"[DRIVE SELESAI] '{drive_video_filename}' dipindahkan dari '03_Antrian_Google_Form_MotionGrafis' ke '{DRIVE_DONE_FOLDER}'.")
                    except Exception as mv_err:
                        print(f"[PERINGATAN] Gagal memindahkan video ke {DRIVE_DONE_FOLDER}: {mv_err}")

                if drive_file_id:
                    try:
                        move_drive_file(drive, drive_file_id, form_queue_id, done_id)
                    except Exception:
                        pass

                processed_form_count += 1
                print(f"[BERHASIL FORM #{processed_form_count}] Video Motion Grafis '{title}' selesai & terjadwal di YouTube!")
                time.sleep(15)

        except (HttpError, BrokenPipeError, ConnectionError, TimeoutError) as net_err:
            err_str = str(net_err)
            if (
                "quotaExceeded" in err_str
                or "uploadLimitExceeded" in err_str
                or isinstance(net_err, BrokenPipeError)
            ):
                print(
                    f"[INFO SESI SELESAI] Batas kuota upload harian YouTube tercapai saat memproses Google Form ({err_str[:120]}). "
                    "Permintaan Google Form ini tetap aman di antrian dan otomatis dilanjutkan pada jadwal berikutnya!"
                )
                return processed_form_count, history_file_id, True
            print(f"[PERINGATAN] Gangguan jaringan saat memproses Google Form '{title}': {net_err}")
            break
        except Exception as form_err:
            print(f"[PERINGATAN] Gagal memproses permintaan Google Form '{title}': {form_err}")
            continue

    return processed_form_count, history_file_id, False


def run_queue_pipeline():
    """
    Memproses antrian video di Google Drive SATU PER SATU secara berurutan tanpa henti
    hingga antrian habis (atau hingga batas kuota harian resmi YouTube API tercapai,
    yang kemudian otomatis dilanjutkan pada jadwal berikutnya).
    """
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        raise RuntimeError("Environment variable GEMINI_API_KEY belum diatur.")

    youtube, drive = get_google_services()

    # 1. Pastikan struktur folder di Google Drive 2 TB siap
    root_id = ensure_drive_folder(drive, DRIVE_ROOT_FOLDER)
    assets_id = ensure_drive_folder(drive, DRIVE_ASSETS_FOLDER, root_id)
    queue_id = ensure_drive_folder(drive, DRIVE_QUEUE_FOLDER, root_id)
    done_id = ensure_drive_folder(drive, DRIVE_DONE_FOLDER, root_id)
    form_queue_id = ensure_drive_folder(drive, DRIVE_FORM_QUEUE_FOLDER, root_id)

    # 2. Ambil riwayat upload & daftar video eksisting di channel Islamic K1
    history_data, history_file_id = load_upload_history(drive, root_id)
    try:
        existing_yt_videos = fetch_existing_youtube_videos(youtube, history_data.get("cached_youtube_videos"))
    except HttpError as quota_err:
        if "quotaExceeded" in str(quota_err) or "uploadLimitExceeded" in str(quota_err):
            print(
                "[INFO SESI SELESAI] Batas kuota harian gratis YouTube API (10.000 unit/hari) telah terpakai penuh hari ini "
                "setelah mengunggah banyak video. Sistem akan otomatis melanjutkan sisa antrian saat kuota di-reset!"
            )
            return
        raise
    history_data["cached_youtube_videos"] = existing_yt_videos
    history_file_id = save_upload_history(drive, root_id, history_data, history_file_id)

    # 3. PRIORITAS UTAMA #1: Proses antrian Google Form Motion Grafis Explainer 3 Menit (Islami & Umum)
    form_processed, history_file_id, quota_hit = process_google_form_explainer_queue(
        gemini_api_key=gemini_api_key,
        root_id=root_id,
        assets_id=assets_id,
        form_queue_id=form_queue_id,
        done_id=done_id,
        history_data=history_data,
        history_file_id=history_file_id,
        existing_yt_videos=existing_yt_videos,
    )
    if quota_hit:
        print(f"[SELESAI SESI] Kuota harian YouTube tercapai. Total video Google Form diproses: {form_processed}")
        return

    processed_count = form_processed

    # 4. PRIORITAS UTAMA #2: Proses antrian video baru di 01_Antrian_NotebookLM satu per satu
    while True:
        # Perbarui koneksi & token setiap awal iterasi video agar tidak pernah kedaluwarsa setelah >1 jam
        youtube, drive = get_google_services()

        query = (
            f"'{queue_id}' in parents and trashed = false and "
            f"(mimeType contains 'video/' or name contains '.mp4' or name contains '.mov' or name contains '.mkv')"
        )
        res = (
            drive.files()
            .list(
                q=query,
                fields="files(id, name, md5Checksum, size, createdTime)",
                orderBy="createdTime asc",
                pageSize=50,
            )
            .execute(num_retries=5)
        )
        queue_files = res.get("files", [])

        if not queue_files:
            print(f"[SELESAI] Antrian kosong. Total video diproses pada sesi ini: {processed_count}")
            break

        target_file = None
        for candidate in queue_files:
            duplicate, reason = is_already_uploaded(candidate, history_data, existing_yt_videos, youtube=youtube)
            if duplicate:
                print(f"[SKIP DUPLIKAT] '{candidate['name']}' dilewati karena: {reason}")
                move_drive_file(drive, candidate["id"], queue_id, done_id)
                continue
            target_file = candidate
            break

        if not target_file:
            print("[INFO] Semua video di antrian sudah pernah diupload sebelumnya.")
            break

        print("=================================================================")
        print(f"[PROSES VIDEO #{processed_count + 1}] {target_file['name']} (ID: {target_file['id']})")
        print("=================================================================")

        try:
            with tempfile.TemporaryDirectory(prefix="islamick1_", ignore_cleanup_errors=True) as work_dir:
                logo_path, outro_path, font_path = prepare_assets(drive, assets_id, work_dir)

                raw_video_path = os.path.join(work_dir, "input_notebooklm.mp4")
                print(f"[DRIVE] Mengunduh '{target_file['name']}' dari Google Drive 2 TB...")
                download_drive_file(drive, target_file["id"], raw_video_path)

                orig_duration = get_video_duration(raw_video_path)
                trimmed_duration = max(1.0, orig_duration - 4.0)
                print(
                    f"[INFO] Durasi asli: {orig_duration:.2f}s -> Dipotong 4 detik terakhir menjadi: {trimmed_duration:.2f}s"
                )

                print("[AI] Menghasilkan transkripsi, metadata Islami, timeline, & terjemahan 10 bahasa...")
                ai_data = analyze_video_with_gemini(
                    video_path=raw_video_path,
                    trimmed_duration=trimmed_duration,
                    original_filename=target_file["name"],
                    gemini_api_key=gemini_api_key,
                )

                final_video_path = os.path.join(work_dir, "final_islamick1.mp4")
                print(
                    "[FFMPEG] Merender video (potong 4s + TANPA subtitle + logo kanan atas + outro SUBSCRIBE)..."
                )
                final_duration = render_final_video(
                    input_video_path=raw_video_path,
                    outro_video_path=outro_path,
                    logo_path=logo_path,
                    output_video_path=final_video_path,
                    cut_last_seconds=4.0,
                )
                print(f"[FFMPEG] Selesai! Durasi total dengan outro: {final_duration:.2f}s")

                # Seragamkan Judul YouTube ("... I PAIBP 6 I Bab 9", "... I Fikih 5 I Bab 1", dst.)
                uniform_title = format_uniform_youtube_title(ai_data["title"], target_file["name"])
                ai_data["title"] = uniform_title

                publish_at_iso = compute_next_prime_time_utc(
                    recommended_slot=ai_data.get("recommended_publish_slot", "MALAM"),
                    last_scheduled_iso=history_data.get("last_scheduled_iso"),
                )
                md5_ref = (target_file.get("md5Checksum") or target_file["id"])[:10]
                full_description = f"{ai_data['full_description']}\n\n[Ref:{md5_ref}]"

                localizations_map = ai_data.get("localizations", {})
                localizations_map["id"] = {
                    "title": uniform_title[:100],
                    "description": full_description[:4900],
                }

                video_body = {
                    "snippet": {
                        "title": uniform_title[:100],
                        "description": full_description[:4900],
                        "tags": ai_data.get("tags", ["IslamicK1", "Keluarga Muslim", "Kajian Islam"])[:15],
                        "categoryId": "27",
                        "defaultLanguage": "id",
                        "defaultAudioLanguage": "id",
                    },
                    "status": {
                        "privacyStatus": "private",
                        "publishAt": publish_at_iso,
                        "selfDeclaredMadeForKids": False,
                        "containsSyntheticMedia": True,
                        "embeddable": True,
                        "publicStatsViewable": True,
                    },
                    "localizations": localizations_map,
                }

                # Segarkan kembali koneksi & access_token tepat setelah proses FFmpeg selesai
                # agar tidak terjadi BrokenPipeError pada socket yang idle selama rendering
                youtube, drive = get_google_services()

                print(f"[YOUTUBE] Mengunggah 1 video: '{ai_data['title']}' (Jadwal Tayang: {publish_at_iso})...")
                media_video = MediaFileUpload(
                    final_video_path, mimetype="video/mp4", chunksize=10 * 1024 * 1024, resumable=True
                )
                insert_req = youtube.videos().insert(
                    part="snippet,status,localizations",
                    body=video_body,
                    media_body=media_video,
                )
                response_yt = None
                while response_yt is None:
                    _, response_yt = insert_req.next_chunk(num_retries=5)
                del insert_req
                del media_video

                uploaded_video_id = response_yt["id"]
                print(f"[YOUTUBE] Berhasil diunggah! Link: https://youtu.be/{uploaded_video_id}")
                print("[YOUTUBE] Sesuai pengaturan: Video NotebookLM tidak menggunakan pembuatan thumbnail otomatis.")

                # Masukkan ke Playlist sesuai Kelas PAI / topik
                try:
                    add_video_to_matching_playlists(
                        youtube=youtube,
                        video_id=uploaded_video_id,
                        original_filename=target_file["name"],
                        ai_playlist_name=ai_data.get("playlist_name", "Kajian Keluarga Muslim"),
                    )
                except Exception as e:
                    print(f"[PERINGATAN] Gagal menambahkan ke playlist: {e}")

                # Unggah Subtitle Soft Closed Captions (CC) Multi-Bahasa Global (.srt resmi YouTube, TIDAK menempel di layar video)
                try:
                    segments_cc = ai_data.get("transcript_segments", [])
                    if segments_cc:
                        srt_id_path = os.path.join(work_dir, "captions_id.srt")
                        create_srt_subtitle(segments_cc, srt_id_path, trimmed_duration)
                        youtube.captions().insert(
                            part="snippet",
                            body={
                                "snippet": {
                                    "videoId": uploaded_video_id,
                                    "language": "id",
                                    "name": "Bahasa Indonesia",
                                    "isDraft": False,
                                }
                            },
                            media_body=MediaFileUpload(srt_id_path, mimetype="application/x-subrip"),
                        ).execute(num_retries=2)
                        print("[YOUTUBE CC] Subtitle CC Resmi (Bahasa Indonesia + Auto-Translate Global) berhasil dipasang.")
                except Exception as cc_err:
                    print(f"[INFO CC] Subtitle CC dilewati untuk menghemat kuota upload video harian ({str(cc_err)[:80]}).")

                # Catat ke riwayat upload di Google Drive & pindahkan file ke folder Sudah_Diupload
                history_data.setdefault("uploaded_files", {})[target_file["id"]] = {
                    "original_name": target_file["name"],
                    "md5Checksum": target_file.get("md5Checksum", ""),
                    "youtube_video_id": uploaded_video_id,
                    "youtube_title": ai_data["title"],
                    "scheduled_publish_at": publish_at_iso,
                    "processed_at": datetime.now(TZ_UTC).isoformat(),
                    "thumbnail_v2": True,
                    "upgraded_v3_cover_title_playlist": True,
                }
                existing_yt_videos.append(
                    {
                        "video_id": uploaded_video_id,
                        "title": ai_data["title"],
                        "description": full_description,
                    }
                )
                history_data["cached_youtube_videos"] = existing_yt_videos
                history_data["last_scheduled_iso"] = publish_at_iso
                history_file_id = save_upload_history(drive, root_id, history_data, history_file_id)

                move_drive_file(drive, target_file["id"], queue_id, done_id)
                processed_count += 1
                print(
                    f"[BERHASIL #{processed_count}] '{target_file['name']}' selesai & dipindahkan ke '{DRIVE_DONE_FOLDER}'."
                )
                # Jeda 15 detik sebelum memproses video berikutnya satu per satu
                time.sleep(15)

        except (HttpError, BrokenPipeError, ConnectionError, TimeoutError) as net_err:
            err_str = str(net_err)
            if (
                "quotaExceeded" in err_str
                or "uploadLimitExceeded" in err_str
                or isinstance(net_err, BrokenPipeError)
            ):
                print(
                    f"[INFO SESI SELESAI] Batas kuota/sesi upload harian YouTube tercapai ({err_str[:120]}). "
                    "Sisa video di antrian akan otomatis dilanjutkan pada jadwal berikutnya!"
                )
                return
            raise
        except Exception as file_err:
            print(f"[PERINGATAN] Gagal memproses file '{target_file['name']}': {file_err}")
            break

    # 5. Jika antrian video baru sudah selesai (atau masih ada sisa kuota), perbarui bertahap (maks 3 per sesi)
    #    Judul Seragam + Playlist untuk video lama tanpa membuat/mengubah thumbnail!
    uploaded_map = history_data.get("uploaded_files", {})
    needs_v3_upgrade = [
        (fid, info)
        for fid, info in uploaded_map.items()
        if not info.get("upgraded_v3_cover_title_playlist") and info.get("youtube_video_id")
    ]
    if needs_v3_upgrade:
        batch_v3 = needs_v3_upgrade[:3]
        print(
            f"[UPGRADE JUDUL & PLAYLIST BERTAHAP] Memperbarui Judul Seragam & Playlist (tanpa ubah thumbnail) untuk {len(batch_v3)} dari {len(needs_v3_upgrade)} video lama..."
        )
        for fid, info in batch_v3:
            try:
                youtube, drive = get_google_services()
                vid_id = info["youtube_video_id"]
                orig_name = info.get("original_name", "Materi PAI")
                old_yt_title = info.get("youtube_title", orig_name)

                uniform_title = format_uniform_youtube_title(old_yt_title, orig_name)
                vid_res = youtube.videos().list(part="snippet", id=vid_id).execute(num_retries=3)
                vid_items = vid_res.get("items", [])
                if vid_items:
                    snippet = vid_items[0]["snippet"]
                    if snippet.get("title") != uniform_title:
                        snippet["title"] = uniform_title
                        youtube.videos().update(
                            part="snippet",
                            body={"id": vid_id, "snippet": snippet},
                        ).execute(num_retries=3)
                        print(f"[JUDUL SERAGAM] '{old_yt_title}' -> '{uniform_title}'")
                    info["youtube_title"] = uniform_title

                add_video_to_matching_playlists(
                    youtube=youtube,
                    video_id=vid_id,
                    original_filename=orig_name,
                    ai_playlist_name="Kajian Keluarga Muslim",
                )

                info["upgraded_v3_cover_title_playlist"] = True
                history_file_id = save_upload_history(drive, root_id, history_data, history_file_id)
                print(f"[UPGRADE BERHASIL] {orig_name} ({vid_id}) -> {uniform_title}")
            except Exception as e:
                print(f"[PERINGATAN] Gagal memperbarui judul/playlist untuk {fid}: {e}")
                break


if __name__ == "__main__":
    run_queue_pipeline()
