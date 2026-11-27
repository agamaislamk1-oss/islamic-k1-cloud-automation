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

TZ_WIB = timezone(timedelta(hours=7))
TZ_UTC = timezone.utc
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from video_editor import (
    get_video_duration,
    is_portrait_video,
    detect_smart_end_trim_timestamp,
    create_ass_subtitle,
    create_srt_subtitle,
    render_final_video,
    render_image_to_shorts_video,
    render_image_and_audio_to_video,
    generate_youtube_thumbnail,
)
from ai_metadata_generator import (
    analyze_video_with_gemini,
    generate_complete_metadata_from_title_or_image,
    get_islamic_k1_promo_and_donation_block,
)
from book_cover_helper import (
    parse_textbook_metadata,
    format_uniform_youtube_title,
    get_book_cover_image,
    determine_target_playlist_titles,
    determine_kitab_schedule_weekday,
    parse_muawiyah_episode,
    is_already_valid_kitab_title,
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
DRIVE_IMAGE_SHORTS_FOLDER = "05_Antrian_Gambar_Shorts"
DRIVE_IMAGE_AUDIO_FOLDER = "06_Antrian_Gambar_Dan_Audio"
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
    """
    Mencari atau membuat folder di Google Drive secara otomatis.
    Jika ditemukan lebih dari 1 folder dengan nama yang sama (duplikat), otomatis memindahkan
    seluruh isinya ke folder pertama lalu menghapus folder duplikat agar tidak membingungkan!
    """
    escaped = folder_name.replace("'", "\\'")
    query = f"name = '{escaped}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    res = drive.files().list(q=query, fields="files(id, name, createdTime)", orderBy="createdTime asc", pageSize=10).execute()
    files = res.get("files", [])
    if files:
        primary_id = files[0]["id"]
        if len(files) > 1:
            for dup_folder in files[1:]:
                dup_id = dup_folder["id"]
                try:
                    children = drive.files().list(q=f"'{dup_id}' in parents and trashed = false", fields="files(id, name)").execute().get("files", [])
                    for ch in children:
                        drive.files().update(fileId=ch["id"], addParents=primary_id, removeParents=dup_id, fields="id").execute()
                    drive.files().update(fileId=dup_id, body={"trashed": True}).execute()
                    print(f"[BERSIH DUPLIKAT FOLDER] Folder kembar '{folder_name}' ({dup_id}) digabungkan & dihapus!")
                except Exception:
                    pass
        return primary_id

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


def compute_next_prime_time_utc(
    recommended_slot: str,
    last_scheduled_iso: Optional[str],
    history_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Menentukan waktu tayang terjadwal (Scheduled Publish) pada jam Prime Time Keluarga Muslim (WIB / UTC+7):
    - SUBUH: 05:00 WIB (22:00 UTC hari sebelumnya)
    - SIANG: 12:00 WIB (05:00 UTC)
    - MALAM: 19:00 WIB (12:00 UTC)
    PENTING (Sesuai Instruksi Poin 4):
    - Jadwal video selain Seri Kitab TIDAK terpengaruh oleh jadwal Seri Kitab (18.30 WIB).
    - Otomatis mengisi slot 05:00, 12:00, 19:00 WIB yang masih kosong secara berurutan tanpa ada tanggal/jam yang terlewati!
    """
    now_wib = datetime.now(TZ_WIB)
    prime_hours = [5, 12, 19]

    if history_data is not None:
        # Kumpulkan seluruh slot 05:00, 12:00, 19:00 WIB yang sudah terisi oleh video NON-KITAB yang masih aktif
        occupied_wib_slots = set()
        for _, info in history_data.get("uploaded_files", {}).items():
            if not info.get("youtube_video_id"):
                continue
            orig_n = info.get("original_name", "")
            yt_t = info.get("youtube_title", "")
            if determine_kitab_schedule_weekday(orig_n, yt_t) is not None:
                continue  # Abaikan jadwal Seri Kitab (18.30 WIB) agar tidak menggeser video non-kitab
            if parse_muawiyah_episode(orig_n, yt_t) is not None:
                continue  # Abaikan jadwal Seri Ramadhan Muawiyah Ibn Abi Sufyan (05.30 WIB) agar tidak menggeser video lain
            sched_iso = info.get("scheduled_publish_at")
            if sched_iso:
                try:
                    dt_w = datetime.fromisoformat(sched_iso.replace("Z", "+00:00")).astimezone(TZ_WIB)
                    if dt_w > now_wib:
                        occupied_wib_slots.add(dt_w.strftime("%Y-%m-%d %H:%M"))
                except Exception:
                    pass

        for _, finfo in history_data.get("processed_form_requests", {}).items():
            if not finfo.get("youtube_video_id"):
                continue
            sched_iso = finfo.get("scheduled_publish_at")
            if sched_iso:
                try:
                    dt_w = datetime.fromisoformat(sched_iso.replace("Z", "+00:00")).astimezone(TZ_WIB)
                    if dt_w > now_wib:
                        occupied_wib_slots.add(dt_w.strftime("%Y-%m-%d %H:%M"))
                except Exception:
                    pass

        # Cari tanggal terakhir dari video non-kitab yang sudah terjadwal, namun mulai dari slot kosong pertama jika ada celah
        start_day = now_wib.replace(hour=0, minute=0, second=0, microsecond=0)
        if occupied_wib_slots:
            latest_str = max(occupied_wib_slots)
            latest_dt = datetime.strptime(latest_str, "%Y-%m-%d %H:%M").replace(tzinfo=TZ_WIB)
            # Mulai pengecekan dari tanggal video non-kitab terakhir agar berurutan rapi (05:00 -> 12:00 -> 19:00)
            start_day = max(start_day, latest_dt.replace(hour=0, minute=0, second=0, microsecond=0))

        for d_offset in range(0, 400):
            day_dt = start_day + timedelta(days=d_offset)
            for h in prime_hours:
                cand_wib = day_dt.replace(hour=h, minute=0, second=0, microsecond=0)
                if cand_wib <= now_wib + timedelta(minutes=30):
                    continue
                slot_key = cand_wib.strftime("%Y-%m-%d %H:%M")
                if slot_key not in occupied_wib_slots:
                    return cand_wib.astimezone(TZ_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    slot_map = {"SUBUH": 5, "SIANG": 12, "MALAM": 19}
    preferred_hour = slot_map.get(recommended_slot.upper(), 19)

    if not last_scheduled_iso:
        candidate = now_wib.replace(hour=preferred_hour, minute=0, second=0, microsecond=0)
        if candidate <= now_wib + timedelta(minutes=30):
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


def compute_muawiyah_ramadhan_publish_time_utc(filename: str, raw_title: str = "") -> Optional[str]:
    """
    Jadwal Khusus Bulan Ramadhan 1448 H (2027) untuk Seri 'Muawiyah Ibn Abi Sufyan':
    - Ditayangkan berurutan dari awal Ramadhan (1 Ramadhan 1448 H = Senin, 8 Februari 2027)
      sampai akhir Ramadhan (30 Ramadhan 1448 H = Selasa, 9 Maret 2027),
      SETIAP HARI pukul 05.30 WIB (22:30:00Z UTC hari sebelumnya).
    - Episode / Bagian ke-N otomatis dipetakan ke Hari ke-N Ramadhan pukul 05.30 WIB:
      * Episode 1  -> 1 Ramadhan 1448 H (8 Februari 2027 pukul 05.30 WIB = 2027-02-07T22:30:00Z)
      * Episode 2  -> 2 Ramadhan 1448 H (9 Februari 2027 pukul 05.30 WIB = 2027-02-08T22:30:00Z)
      * ...
      * Episode 30 -> 30 Ramadhan 1448 H (9 Maret 2027 pukul 05.30 WIB = 2027-03-08T22:30:00Z)
    """
    ep_num = parse_muawiyah_episode(filename, raw_title)
    if ep_num is None:
        return None
    ramadhan_day_1_wib = datetime(2027, 2, 8, 5, 30, 0, tzinfo=TZ_WIB)
    target_wib = ramadhan_day_1_wib + timedelta(days=max(0, ep_num - 1))
    return target_wib.astimezone(TZ_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_kitab_weekly_publish_time_utc(
    filename: str,
    raw_title: str,
    history_data: Dict[str, Any],
    is_shorts: bool = False,
) -> Optional[str]:
    """
    Menghitung jadwal tayang khusus untuk:
    1. Seri Muawiyah Ibn Abi Sufyan -> Setiap hari selama Bulan Ramadhan pukul 05.30 WIB berurutan (1 s/d 30 Ramadhan)
    2. Seri Kajian Kitab (Setiap pekan pukul 18.30 WIB = 11:30 UTC) mulai Senin, 23 November 2026 pukul 18.30 WIB:
       - Senin  (weekday=0) jam 18.30 WIB : Kitab Bidayatul Hidayah / Tasawuf / Akhlak / Adab
       - Selasa (weekday=1) jam 18.30 WIB : Kitab Fathul Qarib / Ahkamith Thaharah / Fikih
       - Rabu   (weekday=2) jam 18.30 WIB : Kitab Tafsir al-Munir / Al-Qur'an
       - Kamis  (weekday=3) jam 18.30 WIB : Kitab Mawlid al-Barzanji / Sirah / Sejarah
       - Jum'at (weekday=4) jam 18.30 WIB : Kitab Jauharatut Tauhid / Tauhid / Aqidah
    """
    muawiyah_iso = compute_muawiyah_ramadhan_publish_time_utc(filename, raw_title)
    if muawiyah_iso:
        return muawiyah_iso

    sched_info = determine_kitab_schedule_weekday(filename, raw_title)
    if not sched_info:
        return None

    target_weekday, slot_key, bagian_num = sched_info
    now_wib = datetime.now(TZ_WIB)

    # Titik awal "Minggu Depan": Senin, 23 November 2026 pukul 18:30 WIB (atau hari yang sesuai setelah now_wib)
    base_monday_wib = datetime(2026, 11, 23, 18, 30, 0, tzinfo=TZ_WIB)
    first_slot_wib = base_monday_wib + timedelta(days=target_weekday)
    while first_slot_wib <= now_wib + timedelta(hours=1):
        first_slot_wib += timedelta(days=7)

    map_key = f"{slot_key}_SHORTS" if is_shorts else slot_key
    kitab_sched_map = history_data.setdefault("kitab_weekly_schedule_map", {})
    last_slot_iso = kitab_sched_map.get(map_key)

    if not last_slot_iso:
        candidate_wib = first_slot_wib
    else:
        last_dt_wib = datetime.fromisoformat(last_slot_iso.replace("Z", "+00:00")).astimezone(TZ_WIB)
        candidate_wib = last_dt_wib + timedelta(days=7)
        while candidate_wib <= now_wib + timedelta(hours=1):
            candidate_wib += timedelta(days=7)
        candidate_wib = candidate_wib.replace(hour=18, minute=30, second=0, microsecond=0)

    iso_utc = candidate_wib.astimezone(TZ_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    kitab_sched_map[map_key] = iso_utc
    return iso_utc


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

    # Unduh otomatis Gambar Sampul Buku Catatan & Aktivitas Mengaji jika ditaruh pengguna di folder `00_Assets`
    covers_dir = os.path.join(work_dir, "book_covers")
    os.makedirs(covers_dir, exist_ok=True)
    try:
        q_cov = (
            f"'{assets_folder_id}' in parents and trashed = false and "
            f"(name contains 'Buku Catatan' or name contains 'Mengaji' or name contains 'Jilid')"
        )
        cov_files = (
            drive.files()
            .list(q=q_cov, fields="files(id, name)", orderBy="name asc", pageSize=6)
            .execute(num_retries=3)
            .get("files", [])
        )
        for idx_c, cf in enumerate(cov_files[:3]):
            c_dst = os.path.join(covers_dir, f"book_cover_{idx_c:02d}_{cf['name']}")
            download_drive_file(drive, cf["id"], c_dst)
            print(f"[ASET SAMPUL BUKU] Berhasil memuat sampul buku dari 00_Assets: {cf['name']}")
    except Exception as cov_err:
        print(f"[INFO SAMPUL BUKU] Menggunakan sampul buku default ({cov_err})")
    os.environ["ISLAMICK1_BOOK_COVERS_DIR"] = covers_dir

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
    youtube=None,
) -> Tuple[bool, str]:
    """
    Anti-Duplikat Permanen untuk antrian Google Form Motion Grafis (Sesuai Instruksi Poin 2):
    Jika sebuah materi dari Google Form SUDAH PERNAH dibuat & diupload ke YouTube (meskipun videonya masih terjadwal/private
    ataupun kemudian dihapus oleh pengguna di YouTube), sistem TIDAK AKAN PERNAH membuat ulang materi tersebut lagi!
    """
    norm_key, ref_tag = _make_form_request_id(title, audience)
    processed_forms = history_data.get("processed_form_requests", {})
    if norm_key in processed_forms:
        vid_id = processed_forms[norm_key].get("youtube_video_id", "")
        return (
            True,
            f"Sudah pernah dibuat & diupload dari Google Form (YouTube ID: {vid_id}) — dikunci permanen agar tidak dibuat ulang.",
        )

    norm_title = normalize_key(title)
    for p_k, p_v in processed_forms.items():
        if normalize_key(p_v.get("form_title", "")) == norm_title and len(norm_title) >= 4:
            vid_id = p_v.get("youtube_video_id", "")
            return (
                True,
                f"Judul Form sudah pernah dibuat & diupload sebelumnya (YouTube ID: {vid_id}) — dikunci permanen agar tidak dibuat ulang.",
            )

    for yt_vid in existing_yt_videos:
        if f"[Ref:{ref_tag}]" in yt_vid.get("description", ""):
            return True, f"Kode referensi {ref_tag} sudah ada di video YouTube '{yt_vid['title']}' ({yt_vid['video_id']})."
        yt_norm_title = normalize_key(yt_vid["title"])
        if len(norm_title) >= 8 and norm_title == yt_norm_title:
            return True, f"Judul identik sudah ada di channel YouTube: '{yt_vid['title']}' ({yt_vid['video_id']})."

    return False, ""


def sync_google_form_status_to_sheet(drive, root_id: str, form_queue_id: str, history_data: Dict[str, Any]) -> None:
    """
    Menuliskan keterangan status 'SUDAH DIUPLOAD: https://youtu.be/<ID>' langsung ke dalam file Google Sheet
    (`Form_Motion_Grafis_IslamicK1`) menggunakan modul CSV bawaan Python (tanpa ketergantungan openpyxl),
    sehingga meskipun video masih Private/Terjadwal atau sudah dihapus di YouTube, baris tersebut tetap bertanda SUDAH DIUPLOAD.
    """
    from googleapiclient.http import MediaIoBaseUpload

    processed_forms = history_data.get("processed_form_requests", {})
    if not processed_forms:
        return
    sheet_query = (
        f"mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false and "
        f"(name contains '{FORM_SHEET_NAME}' or name contains 'Motion Grafis' or name contains 'Form_Motion_Grafis' "
        f"or '{root_id}' in parents or '{form_queue_id}' in parents)"
    )
    try:
        sheet_res = drive.files().list(q=sheet_query, fields="files(id, name)", pageSize=10).execute(num_retries=3)
        for sh in sheet_res.get("files", []):
            try:
                csv_bytes = drive.files().export(fileId=sh["id"], mimeType="text/csv").execute(num_retries=3)
                text_csv = csv_bytes.decode("utf-8-sig", errors="replace")
                rows = [r for r in csv.reader(io.StringIO(text_csv)) if any(str(c).strip() for c in r)]
                if len(rows) <= 1:
                    continue
                headers = [str(c).strip().lower() for c in rows[0]]
                title_idx = 1 if len(headers) > 1 else 0
                aud_idx = 2 if len(headers) > 2 else -1
                status_idx = -1
                for i, col_name in enumerate(headers):
                    if any(k in col_name for k in ["judul", "topik", "title", "topic", "materi"]):
                        title_idx = i
                    elif any(k in col_name for k in ["audience", "audiens", "target", "penonton", "sasaran", "kelas"]):
                        aud_idx = i
                    elif any(k in col_name for k in ["status", "keterangan", "youtube"]):
                        status_idx = i

                modified = False
                if status_idx == -1:
                    status_idx = len(rows[0])
                    rows[0].append("Status YouTube (Otomatis)")
                    modified = True

                for r_i in range(1, len(rows)):
                    row = rows[r_i]
                    while len(row) <= status_idx:
                        row.append("")
                    r_title = str(row[title_idx]).strip() if len(row) > title_idx else ""
                    if not r_title:
                        continue
                    r_aud = (
                        str(row[aud_idx]).strip()
                        if (aud_idx >= 0 and len(row) > aud_idx and str(row[aud_idx]).strip())
                        else "Keluarga & Pelajar Muslim"
                    )
                    nk, _ = _make_form_request_id(r_title, r_aud)
                    rec = processed_forms.get(nk)
                    if not rec:
                        for p_k, p_v in processed_forms.items():
                            if normalize_key(p_v.get("form_title", "")) == normalize_key(r_title):
                                rec = p_v
                                break
                    if rec:
                        vid_id = rec.get("youtube_video_id", "")
                        cur_st = str(row[status_idx]).strip()
                        expected_st = f"SUDAH DIUPLOAD: https://youtu.be/{vid_id}"
                        if "SUDAH" not in cur_st.upper():
                            row[status_idx] = expected_st
                            modified = True

                if modified:
                    out_buf = io.StringIO()
                    writer = csv.writer(out_buf)
                    writer.writerows(rows)
                    media = MediaIoBaseUpload(
                        io.BytesIO(out_buf.getvalue().encode("utf-8")),
                        mimetype="text/csv",
                        resumable=False,
                    )
                    drive.files().update(fileId=sh["id"], media_body=media).execute(num_retries=3)
                    print(f"[GOOGLE SHEET STATUS] Kolom 'Status YouTube' di '{sh['name']}' berhasil diperbarui otomatis!")
            except Exception:
                pass
    except Exception:
        pass


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
    [DINONAKTIFKAN PERMANEN SESUAI INSTRUKSI PENGGUNA]
    Pembuatan dan pengunggahan video dari Google Form Motion Grafis telah dihentikan sepenuhnya.
    """
    print("[GOOGLE FORM] Pembuatan & upload video dari Google Form telah DIHENTIKAN PERMANEN.")
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

        already_done, reason = is_form_request_already_uploaded(title, audience, history_data, existing_yt_videos, youtube=youtube)
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

                kitab_pub_iso = compute_kitab_weekly_publish_time_utc(
                    filename=title,
                    raw_title=pkg["title"],
                    history_data=history_data,
                    is_shorts=False,
                )
                if kitab_pub_iso:
                    publish_at_iso = kitab_pub_iso
                else:
                    publish_at_iso = compute_next_prime_time_utc(
                        recommended_slot=pkg.get("recommended_publish_slot", "MALAM"),
                        last_scheduled_iso=history_data.get("last_scheduled_iso"),
                        history_data=history_data,
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
                post_official_promo_comment_if_needed(youtube, uploaded_video_id)

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
                if not kitab_pub_iso:
                    history_data["last_scheduled_iso"] = publish_at_iso
                history_file_id = save_upload_history(drive, root_id, history_data, history_file_id)
                sync_google_form_status_to_sheet(drive, root_id, form_queue_id, history_data)

                # Pindahkan video hasil render dari 03_Antrian_Google_Form_MotionGrafis ke 02_Sudah_Diupload_YouTube
                if rendered_drive_vid_id:
                    try:
                        move_drive_file(drive, rendered_drive_vid_id, form_queue_id, done_id)
                        print(f"[DRIVE SELESAI] '{drive_video_filename}' dipindahkan dari '03_Antrian_Google_Form_MotionGrafis' ke '{DRIVE_DONE_FOLDER}'.")
                    except Exception as mv_err:
                        print(f"[PERINGATAN] Gagal memindahkan video ke {DRIVE_DONE_FOLDER}: {mv_err}")

                # Unggah Otomatis Versi Vertikal 9:16 (YouTube Shorts <= 60 Detik) jika tersedia!
                shorts_path = pkg.get("shorts_video_path", "")
                if shorts_path and os.path.exists(shorts_path):
                    try:
                        youtube, drive = get_google_services()
                        shorts_drive_name = f"Shorts 9x16 - {safe_t} ({safe_a}).mp4"
                        sh_media_drive = MediaFileUpload(shorts_path, mimetype="video/mp4", resumable=True)
                        drive.files().create(
                            body={"name": shorts_drive_name, "parents": [done_id]},
                            media_body=sh_media_drive,
                            fields="id",
                        ).execute(num_retries=3)
                        del sh_media_drive

                        shorts_pub_iso = compute_next_prime_time_utc(
                            recommended_slot="SIANG",
                            last_scheduled_iso=history_data.get("last_scheduled_iso"),
                        )
                        shorts_title = pkg.get("shorts_title", f"{title[:68]} #Shorts | Islamic K1")[:100]
                        shorts_desc = f"{pkg.get('shorts_description', full_description)}\n\n[Ref:{ref_tag}_SHORTS]"[:4900]
                        shorts_body = {
                            "snippet": {
                                "title": shorts_title,
                                "description": shorts_desc,
                                "tags": (pkg.get("tags", ["IslamicK1", "Shorts"])[:12] + ["Shorts", "YouTubeShorts", "IslamicK1"]),
                                "categoryId": "27",
                                "defaultLanguage": "id",
                                "defaultAudioLanguage": "id",
                            },
                            "status": {
                                "privacyStatus": "private",
                                "publishAt": shorts_pub_iso,
                                "selfDeclaredMadeForKids": False,
                                "containsSyntheticMedia": True,
                                "embeddable": True,
                                "publicStatsViewable": True,
                            },
                        }
                        print(f"[YOUTUBE SHORTS 9:16] Mengunggah versi Shorts: '{shorts_title}' (Jadwal: {shorts_pub_iso})...")
                        sh_media_yt = MediaFileUpload(shorts_path, mimetype="video/mp4", chunksize=10 * 1024 * 1024, resumable=True)
                        sh_req = youtube.videos().insert(part="snippet,status", body=shorts_body, media_body=sh_media_yt)
                        sh_resp = None
                        while sh_resp is None:
                            _, sh_resp = sh_req.next_chunk(num_retries=5)
                        del sh_req
                        del sh_media_yt
                        sh_vid_id = sh_resp["id"]
                        print(f"[YOUTUBE SHORTS 9:16] Berhasil diunggah! Link Shorts: https://youtube.com/shorts/{sh_vid_id}")
                        post_official_promo_comment_if_needed(youtube, sh_vid_id)
                        history_data["last_scheduled_iso"] = shorts_pub_iso
                        history_data[" processed_form_requests" if False else "processed_form_requests"][norm_key]["shorts_video_id"] = sh_vid_id
                        history_file_id = save_upload_history(drive, root_id, history_data, history_file_id)
                    except Exception as sh_up_err:
                        print(f"[PERINGATAN SHORTS] Upload YouTube Shorts dilewati sementara ({str(sh_up_err)[:100]}).")

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


def process_image_shorts_queue(
    gemini_api_key: str,
    root_id: str,
    assets_id: str,
    image_queue_id: str,
    done_id: str,
    history_data: Dict[str, Any],
    history_file_id: Optional[str],
    existing_yt_videos: List[Dict[str, str]],
) -> Tuple[int, Optional[str], bool]:
    """
    Memproses semua gambar (.jpg, .jpeg, .png, .webp) di folder `05_Antrian_Gambar_Shorts`:
    1. Mengubah gambar (Potret maupun Landscape) menjadi Video YouTube Shorts 9:16 (1080x1920)
       dengan instrumen bebas copyright tanpa vokal bernuansa Arab/Islami (Maqam Hijaz).
    2. Menyusun Judul (#Shorts), Deskripsi 3 Paragraf Islami + Buku Mengaji Jilid 1-3 & Donasi,
       Tag, Timeline, Playlist, dan Terjemahan 10 Bahasa.
    3. Mengunggah ke YouTube Islamic K1 dan memindahkan gambar ke `02_Sudah_Diupload_YouTube`.
    """
    youtube, drive = get_google_services()
    q_img = (
        f"'{image_queue_id}' in parents and trashed = false and "
        f"(mimeType contains 'image/' or name contains '.jpg' or name contains '.jpeg' or name contains '.png' or name contains '.webp')"
    )
    img_files = (
        drive.files()
        .list(q=q_img, fields="files(id, name, md5Checksum, createdTime)", orderBy="createdTime asc", pageSize=25)
        .execute(num_retries=4)
        .get("files", [])
    )
    if not img_files:
        return 0, history_file_id, False

    print(f"[GAMBAR SHORTS] Ditemukan {len(img_files)} gambar di '{DRIVE_IMAGE_SHORTS_FOLDER}'. Memproses menjadi YouTube Shorts...")
    processed_img_count = 0

    for img_f in img_files:
        dup, reason = is_already_uploaded(img_f, history_data, existing_yt_videos, youtube=youtube)
        if dup:
            print(f"[SKIP GAMBAR SHORTS] '{img_f['name']}' sudah pernah diupload ({reason}).")
            move_drive_file(drive, img_f["id"], image_queue_id, done_id)
            continue

        print("=================================================================")
        print(f"[PROSES GAMBAR SHORTS #{processed_img_count + 1}] {img_f['name']} (ID: {img_f['id']})")
        print("=================================================================")

        try:
            with tempfile.TemporaryDirectory(prefix="islamick1_imgshort_", ignore_cleanup_errors=True) as work_dir:
                logo_path, outro_path, font_path = prepare_assets(drive, assets_id, work_dir)
                ext = os.path.splitext(img_f["name"])[1].lower() or ".jpg"
                raw_img_path = os.path.join(work_dir, f"input_image{ext}")
                download_drive_file(drive, img_f["id"], raw_img_path)

                short_mp4 = os.path.join(work_dir, "final_image_short.mp4")
                print("[FFMPEG GAMBAR SHORTS] Mengubah gambar menjadi Video Shorts 9:16 + Instrumen Arab/Islami Tanpa Vokal...")
                final_dur = render_image_to_shorts_video(
                    image_path=raw_img_path,
                    logo_path=logo_path,
                    font_path=font_path,
                    output_video_path=short_mp4,
                    duration_sec=20.0,
                )

                print("[AI GAMBAR SHORTS] Menyusun Judul, Deskripsi + Buku Mengaji, Timeline, Tag, & Terjemahan 10 Bahasa...")
                ai_data = generate_complete_metadata_from_title_or_image(
                    title_or_filename=img_f["name"],
                    duration=final_dur,
                    gemini_api_key=gemini_api_key,
                    image_path=raw_img_path,
                    is_shorts=True,
                )

                kitab_pub_iso = compute_kitab_weekly_publish_time_utc(
                    filename=img_f["name"],
                    raw_title=ai_data["title"],
                    history_data=history_data,
                    is_shorts=True,
                )
                if kitab_pub_iso:
                    publish_at_iso = kitab_pub_iso
                else:
                    publish_at_iso = compute_next_prime_time_utc(
                        recommended_slot="SIANG",
                        last_scheduled_iso=history_data.get("last_scheduled_iso"),
                        history_data=history_data,
                    )
                md5_ref = (img_f.get("md5Checksum") or img_f["id"])[:10]
                full_description = f"{ai_data['full_description']}\n\n[Ref:IMG_{md5_ref}]"

                locs = ai_data.get("localizations", {})
                locs["id"] = {"title": ai_data["title"][:100], "description": full_description[:4900]}

                video_body = {
                    "snippet": {
                        "title": ai_data["title"][:100],
                        "description": full_description[:4900],
                        "tags": (ai_data.get("tags", ["IslamicK1", "Shorts", "BelajarMengaji"])[:12] + ["Shorts", "YouTubeShorts", "IslamicK1"]),
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
                    "localizations": locs,
                }

                youtube, drive = get_google_services()
                print(f"[YOUTUBE GAMBAR SHORTS] Mengunggah Shorts: '{ai_data['title']}' (Jadwal: {publish_at_iso})...")
                media_v = MediaFileUpload(short_mp4, mimetype="video/mp4", chunksize=10 * 1024 * 1024, resumable=True)
                ins_req = youtube.videos().insert(part="snippet,status,localizations", body=video_body, media_body=media_v)
                resp_yt = None
                while resp_yt is None:
                    _, resp_yt = ins_req.next_chunk(num_retries=5)
                del ins_req
                del media_v

                vid_id = resp_yt["id"]
                print(f"[YOUTUBE GAMBAR SHORTS] Berhasil diunggah! Link: https://youtube.com/shorts/{vid_id}")
                post_official_promo_comment_if_needed(youtube, vid_id)

                try:
                    add_video_to_matching_playlists(
                        youtube=youtube,
                        video_id=vid_id,
                        original_filename=img_f["name"],
                        ai_playlist_name=ai_data.get("playlist_name", "Kajian Keluarga Muslim"),
                    )
                except Exception:
                    pass

                history_data.setdefault("uploaded_files", {})[img_f["id"]] = {
                    "original_name": img_f["name"],
                    "md5Checksum": img_f.get("md5Checksum", ""),
                    "youtube_video_id": vid_id,
                    "youtube_title": ai_data["title"],
                    "scheduled_publish_at": publish_at_iso,
                    "processed_at": datetime.now(TZ_UTC).isoformat(),
                    "upgraded_v3_cover_title_playlist": True,
                    "upgraded_v4_full_promo_desc": True,
                }
                existing_yt_videos.append({"video_id": vid_id, "title": ai_data["title"], "description": full_description})
                history_data["cached_youtube_videos"] = existing_yt_videos
                if not kitab_pub_iso:
                    history_data["last_scheduled_iso"] = publish_at_iso
                history_file_id = save_upload_history(drive, root_id, history_data, history_file_id)

                move_drive_file(drive, img_f["id"], image_queue_id, done_id)
                processed_img_count += 1
                time.sleep(10)

        except (HttpError, BrokenPipeError, ConnectionError, TimeoutError) as net_err:
            err_str = str(net_err)
            if "quotaExceeded" in err_str or "uploadLimitExceeded" in err_str or isinstance(net_err, BrokenPipeError):
                return processed_img_count, history_file_id, True
            break
        except Exception as e:
            print(f"[PERINGATAN] Gagal memproses gambar Shorts '{img_f['name']}': {e}")
            continue

    return processed_img_count, history_file_id, False


def upgrade_legacy_channel_videos_metadata(
    youtube,
    drive,
    root_id: str,
    history_data: Dict[str, Any],
    history_file_id: Optional[str],
    existing_yt_videos: List[Dict[str, str]],
    gemini_api_key: str,
    max_per_run: int = 8,
) -> Optional[str]:
    """
    Memeriksa seluruh video di channel Islamic K1 yang:
    - Belum memiliki deskripsi lengkap (kosong, pendek, atau hanya berisi deskripsi standar lama tanpa 3 paragraf/timeline), ATAU
    - Belum memiliki blok promosi 'Islamic Studies - Buku Catatan Materi & Aktivitas Perkembangan Mengaji' (Jilid 1, 2, 3).
    Secara otomatis melengkapi: Deskripsi 3 Paragraf Islami + Salam + Timeline + Link Buku Mengaji Jilid 1-3 & Donasi
    + Tags + Terjemahan 10 Bahasa + Playlist (bertahap setiap siklus agar aman & hemat kuota API!).
    """
    upgraded_set = set(history_data.get("upgraded_full_desc_video_ids", []))
    candidates: List[Dict[str, str]] = []

    for v in existing_yt_videos:
        vid_id = v.get("video_id", "")
        if not vid_id or vid_id in upgraded_set:
            continue
        desc = v.get("description", "") or ""
        has_book_links = "id.shp.ee/oQa2tEh" in desc and "id.shp.ee/Cpwj7ZA" in desc and "id.shp.ee/xgWDkq5" in desc
        has_timeline = "00:00" in desc or "0:00" in desc
        has_salam = "assalamu" in desc.lower() and len(desc.strip()) >= 420
        if not (has_book_links and has_timeline and has_salam):
            candidates.append(v)

    if not candidates:
        return history_file_id

    batch = candidates[:max_per_run]
    print(f"[UPGRADE DESKRIPSI & BUKU MENGAJI] Memperbarui {len(batch)} dari {len(candidates)} video channel yang belum punya deskripsi lengkap / link Buku Mengaji...")

    for item in batch:
        vid_id = item["video_id"]
        try:
            youtube, drive = get_google_services()
            v_res = youtube.videos().list(part="snippet,contentDetails,localizations", id=vid_id).execute(num_retries=3)
            v_items = v_res.get("items", [])
            if not v_items:
                upgraded_set.add(vid_id)
                continue

            v_obj = v_items[0]
            snippet = v_obj["snippet"]
            cur_title = snippet.get("title", "Kajian Islami Islamic K1")
            cur_desc = snippet.get("description", "") or ""

            # Estimasi durasi dari ISO 8601 duration (misal PT4M15S)
            iso_dur = v_obj.get("contentDetails", {}).get("duration", "PT3M0S")
            m_min = re.search(r"(\d+)M", iso_dur)
            m_sec = re.search(r"(\d+)S", iso_dur)
            est_dur = (int(m_min.group(1)) * 60 if m_min else 0) + (int(m_sec.group(1)) if m_sec else 0)
            if est_dur <= 0:
                est_dur = 180.0

            is_short_vid = est_dur <= 62 or "#shorts" in cur_title.lower()
            ai_meta = generate_complete_metadata_from_title_or_image(
                title_or_filename=cur_title,
                duration=float(est_dur),
                gemini_api_key=gemini_api_key,
                is_shorts=is_short_vid,
            )

            # Pertahankan kode [Ref:...] lama jika ada
            ref_match = re.search(r"\[Ref:[^\]]+\]", cur_desc)
            new_desc = ai_meta["full_description"]
            if ref_match and ref_match.group(0) not in new_desc:
                new_desc = f"{new_desc}\n\n{ref_match.group(0)}"

            snippet["description"] = new_desc[:4900]
            if not snippet.get("tags") or len(snippet.get("tags", [])) < 5:
                snippet["tags"] = ai_meta.get("tags", ["IslamicK1", "BelajarMengaji", "KeluargaMuslim", "EdukasiIslami"])[:15]
            snippet["defaultLanguage"] = "id"
            snippet["defaultAudioLanguage"] = "id"

            locs = v_obj.get("localizations") or {}
            for lg, lval in (ai_meta.get("localizations") or {}).items():
                locs[lg] = lval
            locs["id"] = {"title": snippet["title"][:100], "description": snippet["description"][:4900]}

            youtube.videos().update(
                part="snippet,localizations",
                body={"id": vid_id, "snippet": snippet, "localizations": locs},
            ).execute(num_retries=3)

            try:
                add_video_to_matching_playlists(
                    youtube=youtube,
                    video_id=vid_id,
                    original_filename=cur_title,
                    ai_playlist_name=ai_meta.get("playlist_name", "Kajian Keluarga Muslim"),
                )
            except Exception:
                pass

            post_official_promo_comment_if_needed(youtube, vid_id)

            item["description"] = snippet["description"]
            upgraded_set.add(vid_id)
            history_data["upgraded_full_desc_video_ids"] = list(upgraded_set)
            history_file_id = save_upload_history(drive, root_id, history_data, history_file_id)
            print(f"  [OK UPGRADE CHANNEL] '{cur_title}' ({vid_id}) -> Deskripsi 3 Paragraf + Buku Mengaji Jilid 1-3 + Komentar Resmi + 10 Bahasa + Playlist!")
        except HttpError as he:
            if "quotaExceeded" in str(he):
                print("[INFO KUOTA] Kuota harian YouTube tercapai saat upgrade deskripsi video lama, akan dilanjutkan otomatis besok.")
                break
            print(f"  [LEWATI] Gagal update {vid_id}: {he}")
        except Exception as e:
            print(f"  [LEWATI] Gagal update {vid_id}: {e}")

    return history_file_id


_BAD_OR_PROFANE_WORDS = (
    # Kata kasar / umpatan bahasa Indonesia & daerah
    "anjing", "anjir", "anjay", "babi", "monyet", "bangsat", "brengsek", "bajingan", "keparat",
    "tolol", "goblok", "idiot", "bego", "bodoh banget", "sinting", "edan", "kampret", "sialan",
    "tai", "tahi", "kontol", "memek", "jembut", "ngentot", "peju", "pelacur", "lonte", "jablay",
    "asu", "jancok", "jancuk", "cuk", "cok", "matamu", "ndasmu", "perek", "bencong", "banci",
    # Kata kasar bahasa Inggris
    "fuck", "shit", "bitch", "asshole", "bastard", "dick", "pussy", "whore", "slut", "stfu",
    # Judi online / spam / pornografi / ujaran kebencian
    "slot gacor", "gacor", "maxwin", "judol", "togel", "poker online", "zeus slot", "situs slot",
    "bokep", "porno", "xnxx", "xvideos", "open bo", "sesat lo", "kafir lo", "munafik lo",
)


def _is_bad_or_profane_comment(text: str) -> bool:
    """Mendeteksi apakah komentar mengandung kata kasar, hinaan, ujaran kebencian, atau promosi judi/spam."""
    low = re.sub(r"[^a-zA-Z0-9\s]", " ", (text or "").lower())
    low_compact = re.sub(r"\s+", " ", low).strip()
    for bad in _BAD_OR_PROFANE_WORDS:
        if " " in bad:
            if bad in low_compact:
                return True
        else:
            if re.search(rf"\b{re.escape(bad)}\b", low_compact):
                return True
    return False


def _generate_polite_islamic_comment_reply(author_name: str, comment_text: str, gemini_api_key: str) -> str:
    """
    Menyusun balasan komentar yang sangat sopan, hangat, mengapresiasi, dan bernuansa Islami,
    serta mengingatkan dengan santun tentang Buku Catatan & Aktivitas Perkembangan Mengaji.
    """
    clean_author = re.sub(r"^@", "", (author_name or "Sahabat Muslim").strip())[:32]
    low_c = (comment_text or "").lower()
    starts_with_salam = any(k in low_c for k in ("assalamu", "asalamu", "salam"))

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=gemini_api_key,
            http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)),
        )
        prompt = (
            f"Anda adalah admin resmi channel dakwah & edukasi keluarga Muslim 'Islamic K1'.\n"
            f"Penonton bernama '{clean_author}' menulis komentar: \"{comment_text}\"\n"
            f"Tuliskan balasan komentar singkat (2-3 kalimat) yang sangat sopan, mengapresiasi, hangat, dan Islami "
            f"(awali dengan Wa'alaikumussalam Warahmatullahi Wabarakatuh jika mereka memberi salam, atau Alhamdulillah/Jazakumullahu Khairan jika tidak). "
            f"Di kalimat terakhir, ajak dengan ramah untuk melihat Buku Catatan Materi & Aktivitas Perkembangan Mengaji Jilid 1-3 di deskripsi video."
        )
        resp = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.35),
        )
        reply = (resp.text or "").strip().strip('"')
        if len(reply) >= 25:
            return reply[:480]
    except Exception:
        pass

    greeting = (
        f"Wa'alaikumussalam Warahmatullahi Wabarakatuh Kak {clean_author}. "
        if starts_with_salam
        else f"Alhamdulillah, Jazakumullahu Khairan Kak {clean_author} atas komentar dan kehadirannya di channel Islamic K1. "
    )
    return (
        f"{greeting}Semoga materi pada video ini membawa manfaat dan keberkahan bagi keluarga tercinta. "
        f"Jangan lupa cek juga Buku Catatan Materi & Aktivitas Perkembangan Mengaji (Jilid 1, 2, & 3) di deskripsi video ya. Barakallahu fiikum 🙏✨"
    )


def post_official_promo_comment_if_needed(youtube, video_id: str) -> None:
    """
    Usulan 1: Menuliskan Komentar Pertama Resmi di bawah video (agar penonton HP yang membuka komentar
    langsung bisa mengklik link Shopee Buku Catatan Materi & Aktivitas Perkembangan Mengaji Jilid 1-3).
    """
    if not youtube or not video_id:
        return
    try:
        res = (
            youtube.commentThreads()
            .list(part="snippet", videoId=video_id, maxResults=20, textFormat="plainText")
            .execute(num_retries=2)
        )
        for item in res.get("items", []):
            top_snip = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            author_ch = top_snip.get("authorChannelId", {}).get("value", "")
            txt = top_snip.get("textDisplay", "")
            if author_ch == EXPECTED_CHANNEL_ID and "id.shp.ee/oQa2tEh" in txt:
                return  # Komentar resmi buku mengaji sudah ada di video ini

        comment_text = (
            "Assalamu'alaikum Warahmatullahi Wabarakatuh 🌟\n"
            "Terima kasih telah menyimak video edukasi di channel resmi Islamic K1!\n\n"
            "📖 MILIKI BUKU CATATAN MATERI & AKTIVITAS PERKEMBANGAN MENGAJI:\n"
            "Islamic Studies - Buku Catatan Materi & Aktivitas Perkembangan Mengaji\n"
            "Dampingi buah hati & santri belajar mengaji lebih terarah, rapi, dan bersemangat setiap hari:\n"
            "📗 Jilid 1 : https://id.shp.ee/oQa2tEh\n"
            "📘 Jilid 2 : https://id.shp.ee/Cpwj7ZA\n"
            "📙 Jilid 3 : https://id.shp.ee/xgWDkq5\n\n"
            "🤝 Dukung Dakwah Yayasan Bekal Kebaikan Anak Bangsa:\n"
            "👉 https://linktr.ee/bekalkebaikan\n"
            "Jazakumullahu Khairan. Wassalamu'alaikum Warahmatullahi Wabarakatuh 🙏✨"
        )
        youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {"snippet": {"textOriginal": comment_text}},
                }
            },
        ).execute(num_retries=2)
        print(f"[AUTO-COMMENT BUKU] Komentar promosi resmi Buku Mengaji Jilid 1-3 dipasang di video {video_id}!")
    except Exception as e:
        print(f"[INFO AUTO-COMMENT] Dilewati pada video {video_id} ({str(e)[:80]})")


def moderate_and_reply_channel_comments(
    youtube,
    drive,
    root_id: str,
    history_data: Dict[str, Any],
    history_file_id: Optional[str],
    gemini_api_key: str,
    max_replies_per_run: int = 12,
) -> Optional[str]:
    """
    Memeriksa seluruh komentar yang masuk di semua video channel Islamic K1 (baik komentar lama maupun baru):
    1. Menghapus/menolak otomatis semua komentar buruk, kata kasar, hinaan, ujaran kebencian, atau spam judi.
    2. Menjawab otomatis semua komentar baik dari penonton dengan kalimat yang sopan, mengapresiasi, dan Islami.
    """
    replied_ids = set(history_data.get("replied_comment_ids", []))
    moderated_bad_ids = set(history_data.get("moderated_bad_comment_ids", []))
    changed = False
    replies_sent = 0

    try:
        res = (
            youtube.commentThreads()
            .list(
                part="snippet,replies",
                allThreadsRelatedToChannelId=EXPECTED_CHANNEL_ID,
                maxResults=50,
                textFormat="plainText",
            )
            .execute(num_retries=3)
        )
    except Exception as e:
        print(f"[INFO MODERASI KOMENTAR] Tidak dapat memuat daftar komentar saat ini ({str(e)[:80]}).")
        return history_file_id

    for thread in res.get("items", []):
        top_obj = thread.get("snippet", {}).get("topLevelComment", {})
        top_id = top_obj.get("id", "")
        top_snip = top_obj.get("snippet", {})
        author_ch = top_snip.get("authorChannelId", {}).get("value", "")
        author_name = top_snip.get("authorDisplayName", "Sahabat Muslim")
        text_orig = top_snip.get("textDisplay", "") or top_snip.get("textOriginal", "")

        if not top_id:
            continue

        # 1. Cek apakah komentar utama mengandung kata kasar / buruk / spam judi -> Hapus!
        if author_ch != EXPECTED_CHANNEL_ID and _is_bad_or_profane_comment(text_orig):
            if top_id not in moderated_bad_ids:
                try:
                    youtube.comments().setModerationStatus(id=top_id, moderationStatus="rejected").execute(num_retries=2)
                    print(f"[HAPUS KOMENTAR BURUK] Komentar tidak pantas dari '{author_name}' berhasil dihapus/ditolak!")
                except Exception:
                    try:
                        youtube.comments().delete(id=top_id).execute(num_retries=2)
                    except Exception:
                        pass
                moderated_bad_ids.add(top_id)
                changed = True
            continue

        # Cek juga sub-komentar (replies) jika ada komentar kasar di dalam balasan
        existing_replies = thread.get("replies", {}).get("comments", [])
        already_replied_by_owner = False
        for rep in existing_replies:
            rep_id = rep.get("id", "")
            rep_snip = rep.get("snippet", {})
            rep_ch = rep_snip.get("authorChannelId", {}).get("value", "")
            rep_txt = rep_snip.get("textDisplay", "")
            if rep_ch == EXPECTED_CHANNEL_ID:
                already_replied_by_owner = True
            elif _is_bad_or_profane_comment(rep_txt) and rep_id not in moderated_bad_ids:
                try:
                    youtube.comments().setModerationStatus(id=rep_id, moderationStatus="rejected").execute(num_retries=2)
                    print(f"[HAPUS BALASAN BURUK] Balasan tidak pantas ({rep_id}) berhasil dihapus!")
                except Exception:
                    pass
                moderated_bad_ids.add(rep_id)
                changed = True

        # 2. Balas otomatis komentar baik dari penonton yang belum dijawab
        if author_ch == EXPECTED_CHANNEL_ID or already_replied_by_owner or top_id in replied_ids:
            if already_replied_by_owner and top_id not in replied_ids:
                replied_ids.add(top_id)
                changed = True
            continue

        if replies_sent < max_replies_per_run:
            try:
                reply_msg = _generate_polite_islamic_comment_reply(author_name, text_orig, gemini_api_key)
                youtube.comments().insert(
                    part="snippet",
                    body={"snippet": {"parentId": top_id, "textOriginal": reply_msg}},
                ).execute(num_retries=2)
                replied_ids.add(top_id)
                replies_sent += 1
                changed = True
                print(f"[BALAS KOMENTAR ISLAMI] Menjawab komentar '{author_name}': \"{reply_msg[:75]}...\"")
            except HttpError as he:
                if "quotaExceeded" in str(he):
                    break
            except Exception as rep_err:
                print(f"[INFO BALAS KOMENTAR] Lewati {top_id} ({str(rep_err)[:70]})")

    if changed:
        history_data["replied_comment_ids"] = list(replied_ids)
        history_data["moderated_bad_comment_ids"] = list(moderated_bad_ids)
        history_file_id = save_upload_history(drive, root_id, history_data, history_file_id)

    return history_file_id


def process_image_and_audio_queue(
    gemini_api_key: str,
    root_id: str,
    assets_id: str,
    img_audio_queue_id: str,
    done_id: str,
    history_data: Dict[str, Any],
    history_file_id: Optional[str],
    existing_yt_videos: List[Dict[str, str]],
) -> Tuple[int, Optional[str], bool]:
    """
    Memproses pasangan Gambar (.jpg/.png/.webp) + Audio (.m4a/.mp3/.wav/.aac) di folder `06_Antrian_Gambar_Dan_Audio`:
    1. Mencocokkan file audio `.m4a` dengan file gambar di dalam folder (baik bernama sama maupun berpasangan langsung).
    2. Mentranskripsikan isi audio `.m4a` & menyusun Judul, Deskripsi 3 Paragraf Islami + Buku Mengaji Jilid 1-3 & Donasi,
       Timeline/Chapters, Tag, Playlist, serta Terjemahan 10 Bahasa Dunia + Subtitle Resmi CC.
    3. Menggabungkan Gambar + Audio `.m4a` + Iklan Buku Mengaji + Outro `SUBSCRIBE ISLAMIC K1.mp4` + Logo Kanan Atas.
    4. Mengunggah ke YouTube Islamic K1 dan memindahkan file gambar & audio ke `02_Sudah_Diupload_YouTube`.
    """
    youtube, drive = get_google_services()
    q_all = f"'{img_audio_queue_id}' in parents and trashed = false"
    all_files = (
        drive.files()
        .list(q=q_all, fields="files(id, name, mimeType, md5Checksum, createdTime)", orderBy="createdTime asc", pageSize=50)
        .execute(num_retries=4)
        .get("files", [])
    )
    if not all_files:
        return 0, history_file_id, False

    audio_exts = (".m4a", ".mp3", ".wav", ".aac", ".ogg", ".flac")
    image_exts = (".jpg", ".jpeg", ".png", ".webp", ".bmp")

    audio_files = [
        f for f in all_files
        if f["name"].lower().endswith(audio_exts) or "audio/" in str(f.get("mimeType", "")).lower()
    ]
    image_files = [
        f for f in all_files
        if f["name"].lower().endswith(image_exts) or "image/" in str(f.get("mimeType", "")).lower()
    ]

    if not audio_files or not image_files:
        return 0, history_file_id, False

    print(
        f"[GAMBAR + AUDIO .M4A] Ditemukan {len(audio_files)} audio & {len(image_files)} gambar di '{DRIVE_IMAGE_AUDIO_FOLDER}'."
    )
    processed_pairs = 0
    used_img_ids = set()

    for aud_f in audio_files:
        dup, reason = is_already_uploaded(aud_f, history_data, existing_yt_videos, youtube=youtube)
        if dup:
            print(f"[SKIP GAMBAR+AUDIO] Audio '{aud_f['name']}' sudah pernah diupload ({reason}).")
            move_drive_file(drive, aud_f["id"], img_audio_queue_id, done_id)
            continue

        # Cari gambar pasangan: abaikan akhiran (1), (2), copy agar Bagian_3 (1).m4a selalu berpasangan tepat dengan Bagian_3 (2).png!
        def _clean_pair_stem(fname: str) -> str:
            stem = os.path.splitext(fname)[0].lower()
            stem = re.sub(r"\(\d+\)\s*$", "", stem).strip()
            return re.sub(r"[^a-z0-9]+", "", stem)

        aud_norm = _clean_pair_stem(aud_f["name"])
        matched_img = None
        for im_f in image_files:
            if im_f["id"] in used_img_ids:
                continue
            im_norm = _clean_pair_stem(im_f["name"])
            if aud_norm and im_norm and (aud_norm == im_norm or aud_norm in im_norm or im_norm in aud_norm):
                matched_img = im_f
                break
        if not matched_img:
            for im_f in image_files:
                if im_f["id"] not in used_img_ids:
                    matched_img = im_f
                    break
        if not matched_img:
            matched_img = image_files[0]

        print("=================================================================")
        print(f"[PROSES GAMBAR + AUDIO #{processed_pairs + 1}] Audio: '{aud_f['name']}' + Gambar: '{matched_img['name']}'")
        print("=================================================================")

        try:
            with tempfile.TemporaryDirectory(prefix="islamick1_imgaud_", ignore_cleanup_errors=True) as work_dir:
                logo_path, outro_path, font_path = prepare_assets(drive, assets_id, work_dir)
                aud_ext = os.path.splitext(aud_f["name"])[1].lower() or ".m4a"
                img_ext = os.path.splitext(matched_img["name"])[1].lower() or ".jpg"
                local_aud = os.path.join(work_dir, f"input_audio{aud_ext}")
                local_img = os.path.join(work_dir, f"input_image{img_ext}")

                download_drive_file(drive, aud_f["id"], local_aud)
                download_drive_file(drive, matched_img["id"], local_img)

                orig_aud_dur = get_video_duration(local_aud)
                print(f"[AI GAMBAR+AUDIO] Mentranskripsi audio '{aud_f['name']}' ({orig_aud_dur:.1f}s) & menyusun metadata 10 bahasa...")
                ai_data = analyze_video_with_gemini(
                    video_path=local_aud,
                    trimmed_duration=orig_aud_dur,
                    original_filename=aud_f["name"],
                    gemini_api_key=gemini_api_key,
                )

                trimmed_dur, smart_cut = detect_smart_end_trim_timestamp(
                    video_path=local_aud,
                    orig_duration=orig_aud_dur,
                    transcript_segments=ai_data.get("transcript_segments"),
                )
                # Untuk file rekaman audio .m4a murni tanpa kartu watermark visual di ujung, jangan potong jika tidak ada hening panjang
                if smart_cut >= 3.8:
                    smart_cut = 0.0
                    trimmed_dur = orig_aud_dur

                final_mp4 = os.path.join(work_dir, "final_img_audio_islamick1.mp4")
                print("[FFMPEG GAMBAR+AUDIO] Menggabungkan Gambar + Audio .m4a + Iklan Buku Mengaji + Outro Subscribe...")
                final_dur, is_vert_short = render_image_and_audio_to_video(
                    image_path=local_img,
                    audio_path=local_aud,
                    outro_video_path=outro_path,
                    logo_path=logo_path,
                    font_path=font_path,
                    output_video_path=final_mp4,
                    cut_last_seconds=smart_cut,
                )

                uniform_title = format_uniform_youtube_title(ai_data["title"], aud_f["name"])
                if is_vert_short and "#shorts" not in uniform_title.lower():
                    uniform_title = f"{uniform_title[:88]} #Shorts"
                ai_data["title"] = uniform_title

                kitab_pub_iso = compute_kitab_weekly_publish_time_utc(
                    filename=aud_f["name"],
                    raw_title=uniform_title,
                    history_data=history_data,
                    is_shorts=is_vert_short,
                )
                if kitab_pub_iso:
                    publish_at_iso = kitab_pub_iso
                else:
                    publish_at_iso = compute_next_prime_time_utc(
                        recommended_slot=ai_data.get("recommended_publish_slot", "MALAM"),
                        last_scheduled_iso=history_data.get("last_scheduled_iso"),
                        history_data=history_data,
                    )
                md5_ref = (aud_f.get("md5Checksum") or aud_f["id"])[:10]
                full_description = f"{ai_data['full_description']}\n\n[Ref:M4A_{md5_ref}]"

                locs = ai_data.get("localizations", {})
                locs["id"] = {"title": uniform_title[:100], "description": full_description[:4900]}
                tags_list = ai_data.get("tags", ["IslamicK1", "Keluarga Muslim", "Kajian Islam"])[:13]
                if is_vert_short and "Shorts" not in tags_list:
                    tags_list.extend(["Shorts", "YouTubeShorts"])

                video_body = {
                    "snippet": {
                        "title": uniform_title[:100],
                        "description": full_description[:4900],
                        "tags": tags_list[:15],
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
                    "localizations": locs,
                }

                youtube, drive = get_google_services()
                print(f"[YOUTUBE GAMBAR+AUDIO] Mengunggah video: '{uniform_title}' (Jadwal: {publish_at_iso})...")
                media_v = MediaFileUpload(final_mp4, mimetype="video/mp4", chunksize=10 * 1024 * 1024, resumable=True)
                ins_req = youtube.videos().insert(part="snippet,status,localizations", body=video_body, media_body=media_v)
                resp_yt = None
                while resp_yt is None:
                    _, resp_yt = ins_req.next_chunk(num_retries=5)
                del ins_req
                del media_v

                vid_id = resp_yt["id"]
                print(f"[YOUTUBE GAMBAR+AUDIO] Berhasil diunggah! Link: https://youtu.be/{vid_id}")
                post_official_promo_comment_if_needed(youtube, vid_id)

                try:
                    add_video_to_matching_playlists(
                        youtube=youtube,
                        video_id=vid_id,
                        original_filename=aud_f["name"],
                        ai_playlist_name=ai_data.get("playlist_name", "Kajian Keluarga Muslim"),
                    )
                except Exception:
                    pass

                try:
                    segments_cc = ai_data.get("transcript_segments", [])
                    if segments_cc:
                        srt_path = os.path.join(work_dir, "captions_id.srt")
                        create_srt_subtitle(segments_cc, srt_path, trimmed_dur)
                        youtube.captions().insert(
                            part="snippet",
                            body={"snippet": {"videoId": vid_id, "language": "id", "name": "Bahasa Indonesia", "isDraft": False}},
                            media_body=MediaFileUpload(srt_path, mimetype="application/x-subrip"),
                        ).execute(num_retries=2)
                except Exception:
                    pass

                history_data.setdefault("uploaded_files", {})[aud_f["id"]] = {
                    "original_name": aud_f["name"],
                    "paired_image_name": matched_img["name"],
                    "md5Checksum": aud_f.get("md5Checksum", ""),
                    "youtube_video_id": vid_id,
                    "youtube_title": uniform_title,
                    "scheduled_publish_at": publish_at_iso,
                    "processed_at": datetime.now(TZ_UTC).isoformat(),
                    "upgraded_v3_cover_title_playlist": True,
                }
                existing_yt_videos.append({"video_id": vid_id, "title": uniform_title, "description": full_description})
                history_data["cached_youtube_videos"] = existing_yt_videos
                if not kitab_pub_iso:
                    history_data["last_scheduled_iso"] = publish_at_iso
                history_file_id = save_upload_history(drive, root_id, history_data, history_file_id)

                move_drive_file(drive, aud_f["id"], img_audio_queue_id, done_id)
                if len(audio_files) == 1 or len(image_files) > 1:
                    move_drive_file(drive, matched_img["id"], img_audio_queue_id, done_id)
                    used_img_ids.add(matched_img["id"])

                processed_pairs += 1
                time.sleep(12)

        except (HttpError, BrokenPipeError, ConnectionError, TimeoutError) as net_err:
            err_str = str(net_err)
            if "quotaExceeded" in err_str or "uploadLimitExceeded" in err_str or isinstance(net_err, BrokenPipeError):
                return processed_pairs, history_file_id, True
            break
        except Exception as e:
            print(f"[PERINGATAN] Gagal memproses pasangan Gambar+Audio '{aud_f['name']}': {e}")
            continue

    return processed_pairs, history_file_id, False


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

    # 1. Pastikan struktur folder di Google Drive 2 TB siap (termasuk 05_Antrian_Gambar_Shorts & 06_Antrian_Gambar_Dan_Audio)
    root_id = ensure_drive_folder(drive, DRIVE_ROOT_FOLDER)
    assets_id = ensure_drive_folder(drive, DRIVE_ASSETS_FOLDER, root_id)
    queue_id = ensure_drive_folder(drive, DRIVE_QUEUE_FOLDER, root_id)
    done_id = ensure_drive_folder(drive, DRIVE_DONE_FOLDER, root_id)
    form_queue_id = ensure_drive_folder(drive, DRIVE_FORM_QUEUE_FOLDER, root_id)
    image_shorts_id = ensure_drive_folder(drive, DRIVE_IMAGE_SHORTS_FOLDER, root_id)
    image_audio_id = ensure_drive_folder(drive, DRIVE_IMAGE_AUDIO_FOLDER, root_id)

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

    # 2A. PRIORITAS #0A: Proses antrian Gambar + Audio (.m4a) di `06_Antrian_Gambar_Dan_Audio`
    img_aud_processed, history_file_id, ia_quota_hit = process_image_and_audio_queue(
        gemini_api_key=gemini_api_key,
        root_id=root_id,
        assets_id=assets_id,
        img_audio_queue_id=image_audio_id,
        done_id=done_id,
        history_data=history_data,
        history_file_id=history_file_id,
        existing_yt_videos=existing_yt_videos,
    )
    if ia_quota_hit:
        print(f"[SELESAI SESI] Kuota harian YouTube tercapai. Total Gambar+Audio (.m4a) diproses: {img_aud_processed}")
        return

    # 2B. PRIORITAS #0B: Proses antrian Gambar Shorts di `05_Antrian_Gambar_Shorts`
    img_processed, history_file_id, img_quota_hit = process_image_shorts_queue(
        gemini_api_key=gemini_api_key,
        root_id=root_id,
        assets_id=assets_id,
        image_queue_id=image_shorts_id,
        done_id=done_id,
        history_data=history_data,
        history_file_id=history_file_id,
        existing_yt_videos=existing_yt_videos,
    )
    if img_quota_hit:
        print(f"[SELESAI SESI] Kuota harian YouTube tercapai. Total Gambar Shorts diproses: {img_processed}")
        return

    # 3. NONAKTIFKAN PEMBUATAN VIDEO DARI GOOGLE FORM (Sesuai Instruksi Tegas Pengguna: Hentikan pembuatan/upload video dari Google Form)
    form_processed = 0
    print("[GOOGLE FORM] Pembuatan & upload video dari Google Form telah DIHENTIKAN PERMANEN sesuai instruksi pengguna.")

    processed_count = img_aud_processed + img_processed + form_processed

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
                is_vert_nlm = is_portrait_video(raw_video_path)
                mode_label = "YOUTUBE SHORTS POTRET (9:16)" if is_vert_nlm else "VIDEO LANDSCAPE (16:9)"

                print("[AI] Mentranskripsi penuh hingga salam penutup & menyusun metadata 10 bahasa...")
                ai_data = analyze_video_with_gemini(
                    video_path=raw_video_path,
                    trimmed_duration=orig_duration,
                    original_filename=target_file["name"],
                    gemini_api_key=gemini_api_key,
                )

                trimmed_duration, smart_cut_seconds = detect_smart_end_trim_timestamp(
                    video_path=raw_video_path,
                    orig_duration=orig_duration,
                    transcript_segments=ai_data.get("transcript_segments"),
                )
                print(
                    f"[SMART TRIM SALAM] Mode: {mode_label} | Durasi asli: {orig_duration:.2f}s -> "
                    f"Salam selesai di {trimmed_duration:.2f}s (Memotong ekor watermark {smart_cut_seconds:.2f}s)"
                )

                final_video_path = os.path.join(work_dir, "final_islamick1.mp4")
                print(
                    f"[FFMPEG] Merender {mode_label} (potong tepat setelah salam {smart_cut_seconds:.2f}s + logo kanan atas + outro SUBSCRIBE)..."
                )
                final_duration = render_final_video(
                    input_video_path=raw_video_path,
                    outro_video_path=outro_path,
                    logo_path=logo_path,
                    output_video_path=final_video_path,
                    cut_last_seconds=smart_cut_seconds,
                    force_portrait=is_vert_nlm,
                )
                print(f"[FFMPEG] Selesai! Durasi total dengan outro: {final_duration:.2f}s")

                # Seragamkan Judul YouTube ("... I PAIBP 6 I Bab 9", "... I Fikih 5 I Bab 1", dst.)
                uniform_title = format_uniform_youtube_title(ai_data["title"], target_file["name"])
                if is_vert_nlm and "#shorts" not in uniform_title.lower():
                    uniform_title = f"{uniform_title[:88]} #Shorts"
                ai_data["title"] = uniform_title

                kitab_pub_iso = compute_kitab_weekly_publish_time_utc(
                    filename=target_file["name"],
                    raw_title=uniform_title,
                    history_data=history_data,
                    is_shorts=is_vert_nlm,
                )
                if kitab_pub_iso:
                    publish_at_iso = kitab_pub_iso
                else:
                    publish_at_iso = compute_next_prime_time_utc(
                        recommended_slot=ai_data.get("recommended_publish_slot", "MALAM"),
                        last_scheduled_iso=history_data.get("last_scheduled_iso"),
                        history_data=history_data,
                    )
                md5_ref = (target_file.get("md5Checksum") or target_file["id"])[:10]
                full_description = f"{ai_data['full_description']}\n\n[Ref:{md5_ref}]"
                if is_vert_nlm and "#shorts" not in full_description.lower():
                    full_description = f"{full_description}\n#Shorts #IslamicK1"

                localizations_map = ai_data.get("localizations", {})
                localizations_map["id"] = {
                    "title": uniform_title[:100],
                    "description": full_description[:4900],
                }

                tags_list = ai_data.get("tags", ["IslamicK1", "Keluarga Muslim", "Kajian Islam"])[:13]
                if is_vert_nlm and "Shorts" not in tags_list:
                    tags_list.extend(["Shorts", "YouTubeShorts"])

                video_body = {
                    "snippet": {
                        "title": uniform_title[:100],
                        "description": full_description[:4900],
                        "tags": tags_list[:15],
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
                post_official_promo_comment_if_needed(youtube, uploaded_video_id)

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
                if not kitab_pub_iso:
                    history_data["last_scheduled_iso"] = publish_at_iso
                history_file_id = save_upload_history(drive, root_id, history_data, history_file_id)
                sync_google_form_status_to_sheet(drive, root_id, form_queue_id, history_data)

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

    # 5A. Sinkronisasi Jadwal Khusus (Ramadhan 05.30 WIB untuk Seri Muawiyah Ibn Abi Sufyan,
    #     Mingguan 18.30 WIB untuk Seri Kajian Kitab, dan Slot Rapat 05:00/12:00/19:00 WIB untuk Non-Kitab)
    uploaded_map = history_data.get("uploaded_files", {})
    schedule_updates = []
    base_monday_kitab_wib = datetime(2026, 11, 23, 18, 30, 0, tzinfo=TZ_WIB)

    # Kelompokkan Kitab per weekday dan urutkan berdasarkan Bagian Ke-N agar teratur tiap minggu pukul 18.30 WIB
    kitab_by_weekday: Dict[Tuple[int, bool], List[Tuple[int, str, Dict[str, Any]]]] = {}
    non_kitab_pushed = []

    for fid, info in uploaded_map.items():
        vid_id = info.get("youtube_video_id")
        if not vid_id or vid_id == "N1_9RX2ZMP8":
            continue
        orig_n = info.get("original_name", "")
        cur_t = info.get("youtube_title", "")
        cur_sched = info.get("scheduled_publish_at", "")

        # 1) Cek apakah Seri Muawiyah Ibn Abi Sufyan (Ramadhan pukul 05.30 WIB berurutan Episode 1..30)
        muawiyah_iso = compute_muawiyah_ramadhan_publish_time_utc(orig_n, cur_t)
        if muawiyah_iso:
            if cur_sched != muawiyah_iso:
                schedule_updates.append((fid, info, muawiyah_iso, f"RAMADHAN 05.30 WIB (Ep {parse_muawiyah_episode(orig_n, cur_t)})"))
            continue

        # 2) Cek apakah Seri Kajian Kitab (Senin-Sabtu pukul 18.30 WIB)
        k_sched = determine_kitab_schedule_weekday(orig_n, cur_t)
        if k_sched is not None:
            w_idx, s_key, b_num = k_sched
            is_sh = "#shorts" in cur_t.lower() or orig_n.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
            kitab_by_weekday.setdefault((w_idx, is_sh), []).append((b_num if b_num is not None else 999, fid, info))
            continue

        # 3) Cek apakah video Non-Kitab yang sempat terdorong ke April/Mei 2027 oleh jadwal kitab
        if cur_sched and cur_sched >= "2027-04-01T00:00:00Z":
            non_kitab_pushed.append((fid, info))

    for (w_idx, is_sh), k_list in kitab_by_weekday.items():
        k_list.sort(key=lambda x: x[0])
        first_day_wib = base_monday_kitab_wib + timedelta(days=w_idx)
        for seq_idx, (b_num, fid, info) in enumerate(k_list):
            # Gunakan urutan sekuensial (0, 1, 2...) berdasarkan Bagian yang sudah diurutkan agar tidak ada minggu yang bolong
            target_dt_wib = first_day_wib + timedelta(days=7 * seq_idx)
            target_iso = target_dt_wib.astimezone(TZ_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            if info.get("scheduled_publish_at") != target_iso:
                schedule_updates.append((fid, info, target_iso, f"KITAB HARI KE-{w_idx + 1} 18.30 WIB (Bagian {b_num})"))

    # Tarik video Non-Kitab yang sempat terdorong ke April/Mei 2027 kembali ke slot 05:00/12:00/19:00 WIB setelah 21 Maret 2027
    if non_kitab_pushed:
        temp_assigned_wib = set()
        now_w = datetime.now(TZ_WIB)
        for _, inf_o in uploaded_map.items():
            if not inf_o.get("youtube_video_id"):
                continue
            on_o = inf_o.get("original_name", "")
            yt_o = inf_o.get("youtube_title", "")
            if determine_kitab_schedule_weekday(on_o, yt_o) is not None or parse_muawiyah_episode(on_o, yt_o) is not None:
                continue
            sc_o = inf_o.get("scheduled_publish_at", "")
            if sc_o and sc_o < "2027-04-01T00:00:00Z":
                try:
                    dt_o = datetime.fromisoformat(sc_o.replace("Z", "+00:00")).astimezone(TZ_WIB)
                    if dt_o > now_w:
                        temp_assigned_wib.add(dt_o.strftime("%Y-%m-%d %H:%M"))
                except Exception:
                    pass
        base_march_day = datetime(2027, 3, 21, 0, 0, 0, tzinfo=TZ_WIB)
        if temp_assigned_wib:
            latest_m = max(temp_assigned_wib)
            base_march_day = datetime.strptime(latest_m, "%Y-%m-%d %H:%M").replace(
                hour=0, minute=0, second=0, microsecond=0, tzinfo=TZ_WIB
            )
        for fid, info in non_kitab_pushed:
            found_slot_iso = None
            for d_off in range(0, 120):
                d_cur = base_march_day + timedelta(days=d_off)
                for hr in (5, 12, 19):
                    c_wib = d_cur.replace(hour=hr, minute=0, second=0, microsecond=0)
                    s_key = c_wib.strftime("%Y-%m-%d %H:%M")
                    if s_key not in temp_assigned_wib and c_wib > now_w:
                        temp_assigned_wib.add(s_key)
                        found_slot_iso = c_wib.astimezone(TZ_UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                        break
                if found_slot_iso:
                    break
            if found_slot_iso and info.get("scheduled_publish_at") != found_slot_iso:
                schedule_updates.append((fid, info, found_slot_iso, "RAPATKAN SLOT NON-KITAB"))

    if schedule_updates:
        print(f"[JADWAL KHUSUS] Menyinkronkan jadwal tayang YouTube untuk {len(schedule_updates)} video (Muawiyah Ramadhan 05.30 WIB / Kitab 18.30 WIB / Non-Kitab)...")
        for fid, info, new_iso, lbl in schedule_updates[:65]:
            vid_id = info["youtube_video_id"]
            try:
                youtube, drive = get_google_services()
                youtube.videos().update(
                    part="status",
                    body={
                        "id": vid_id,
                        "status": {
                            "privacyStatus": "private",
                            "publishAt": new_iso,
                            "selfDeclaredMadeForKids": False,
                            "containsSyntheticMedia": True,
                            "embeddable": True,
                            "publicStatsViewable": True,
                        },
                    },
                ).execute(num_retries=2)
                info["scheduled_publish_at"] = new_iso
                history_file_id = save_upload_history(drive, root_id, history_data, history_file_id)
                print(f"  [JADWAL OK] [{lbl}] {info.get('original_name')} ({vid_id}) -> {new_iso}")
            except HttpError as he:
                if "quotaExceeded" in str(he):
                    print("[INFO KUOTA] Kuota harian YouTube tercapai saat sinkronisasi jadwal, akan dilanjutkan otomatis setelah reset kuota.")
                    break
                print(f"  [LEWATI JADWAL] {vid_id}: {str(he)[:80]}")
            except Exception as e:
                print(f"  [LEWATI JADWAL] {vid_id}: {str(e)[:80]}")

    # 5B. Perbarui otomatis Judul Seragam (Materi Pelajaran `I <Mapel> <Kelas> I Bab <N>` & Kajian Kitab `Bagian Ke (N) - Kitab (X), Bab (Y) - Fashal (Z)`)
    #     serta Playlist untuk video yang sudah diupload tanpa membuat/mengubah thumbnail!
    needs_v3_upgrade = []
    seen_upgrade_vid_ids = set()

    for fid, info in uploaded_map.items():
        vid_id = info.get("youtube_video_id")
        if not vid_id:
            continue
        seen_upgrade_vid_ids.add(vid_id)
        orig_name = info.get("original_name", "Materi PAI")
        old_yt_title = info.get("youtube_title", orig_name)
        is_sh = "#shorts" in old_yt_title.lower() or orig_name.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        expected_title = format_uniform_youtube_title(old_yt_title, orig_name, is_shorts=is_sh)
        if not info.get("upgraded_v3_cover_title_playlist") or old_yt_title != expected_title:
            needs_v3_upgrade.append((fid, info, expected_title))

    # Cek juga riwayat Google Form (misal Syarah Kitab Riyadhus Shalihin atau Materi Pelajaran dari Form)
    for fk, finfo in history_data.get("processed_form_requests", {}).items():
        vid_id = finfo.get("youtube_video_id")
        if not vid_id or vid_id in seen_upgrade_vid_ids:
            continue
        seen_upgrade_vid_ids.add(vid_id)
        f_title = finfo.get("form_title", "")
        old_yt_title = finfo.get("youtube_title", f_title)
        expected_title = format_uniform_youtube_title(old_yt_title, f_title, is_shorts=False)
        if old_yt_title != expected_title:
            finfo["original_name"] = f_title
            needs_v3_upgrade.append((fk, finfo, expected_title))

    # Utamakan video terbaru terlebih dahulu (seperti Al-Qur'an Hadis 12, Kajian Kitab, & Al-Qur'an Hadis 1-5)
    needs_v3_upgrade.reverse()

    if needs_v3_upgrade:
        batch_v3 = needs_v3_upgrade[:85]
        print(
            f"[UPGRADE JUDUL & PLAYLIST] Memperbarui Judul Seragam (Mapel / Kajian Kitab) untuk {len(batch_v3)} dari {len(needs_v3_upgrade)} video yang belum sesuai..."
        )
        # Ambil snippet secara batch (maks 50 ID sekaligus = hanya 1 unit kuota API!)
        snippet_map: Dict[str, Dict[str, Any]] = {}
        try:
            youtube, drive = get_google_services()
            all_b_ids = [inf["youtube_video_id"] for _, inf, _ in batch_v3 if inf.get("youtube_video_id")]
            for i_chunk in range(0, len(all_b_ids), 45):
                chunk_ids = all_b_ids[i_chunk : i_chunk + 45]
                v_res = youtube.videos().list(part="snippet", id=",".join(chunk_ids)).execute(num_retries=3)
                for v_it in v_res.get("items", []):
                    snippet_map[v_it["id"]] = v_it["snippet"]
        except Exception as b_err:
            print(f"[INFO BATCH LIST] {b_err}")

        for fid, info, uniform_title in batch_v3:
            try:
                youtube, drive = get_google_services()
                vid_id = info["youtube_video_id"]
                orig_name = info.get("original_name", "Materi PAI")
                old_yt_title = info.get("youtube_title", orig_name)
                was_already_in_pl = bool(info.get("upgraded_v3_cover_title_playlist"))

                snippet = snippet_map.get(vid_id)
                if not snippet:
                    vid_res = youtube.videos().list(part="snippet", id=vid_id).execute(num_retries=3)
                    vid_items = vid_res.get("items", [])
                    if vid_items:
                        snippet = vid_items[0]["snippet"]

                if snippet:
                    live_yt_title = snippet.get("title", "")
                    # Jika video Kajian Kitab sudah diubah manual oleh pengguna di YouTube Studio dan sesuai aturan, JANGAN diubah lagi!
                    if determine_kitab_schedule_weekday(orig_name, live_yt_title) is not None and is_already_valid_kitab_title(live_yt_title):
                        info["youtube_title"] = live_yt_title
                        for cv in existing_yt_videos:
                            if cv.get("video_id") == vid_id:
                                cv["title"] = live_yt_title
                        print(f"[SKIP JUDUL KITAB SUDAH SESUAI DI YOUTUBE] '{live_yt_title}' ({vid_id})")
                    else:
                        if live_yt_title != uniform_title:
                            snippet["title"] = uniform_title
                            youtube.videos().update(
                                part="snippet",
                                body={"id": vid_id, "snippet": snippet},
                            ).execute(num_retries=3)
                            print(f"[JUDUL SERAGAM DIPERBARUI] '{live_yt_title}' -> '{uniform_title}'")
                        info["youtube_title"] = uniform_title
                        for cv in existing_yt_videos:
                            if cv.get("video_id") == vid_id:
                                cv["title"] = uniform_title

                if not was_already_in_pl:
                    add_video_to_matching_playlists(
                        youtube=youtube,
                        video_id=vid_id,
                        original_filename=orig_name,
                        ai_playlist_name="Kajian Keluarga Muslim",
                    )

                info["upgraded_v3_cover_title_playlist"] = True
                history_file_id = save_upload_history(drive, root_id, history_data, history_file_id)
                print(f"[UPGRADE BERHASIL] {orig_name} ({vid_id}) -> {uniform_title}")
            except HttpError as he:
                if "quotaExceeded" in str(he):
                    print("[INFO KUOTA] Kuota harian YouTube tercapai saat update judul, akan otomatis dilanjutkan saat reset kuota berikutnya.")
                    break
                print(f"[PERINGATAN] Gagal memperbarui judul/playlist untuk {fid}: {he}")
            except Exception as e:
                print(f"[PERINGATAN] Gagal memperbarui judul/playlist untuk {fid}: {e}")
                break

    # 6. Perbarui bertahap seluruh video di channel Islamic K1 yang belum memiliki deskripsi lengkap / link Buku Mengaji Jilid 1-3
    try:
        youtube, drive = get_google_services()
        history_file_id = upgrade_legacy_channel_videos_metadata(
            youtube=youtube,
            drive=drive,
            root_id=root_id,
            history_data=history_data,
            history_file_id=history_file_id,
            existing_yt_videos=existing_yt_videos,
            gemini_api_key=gemini_api_key,
            max_per_run=8,
        )
    except Exception as up_desc_err:
        print(f"[INFO UPGRADE DESKRIPSI] Dilewati sementara ({up_desc_err}).")

    # 7. Moderasi Komentar Buruk/Kasar & Balas Otomatis Semua Komentar Baik secara Sopan & Islami
    try:
        youtube, drive = get_google_services()
        history_file_id = moderate_and_reply_channel_comments(
            youtube=youtube,
            drive=drive,
            root_id=root_id,
            history_data=history_data,
            history_file_id=history_file_id,
            gemini_api_key=gemini_api_key,
            max_replies_per_run=12,
        )
    except Exception as mod_err:
        print(f"[INFO MODERASI KOMENTAR] Dilewati sementara ({mod_err}).")


if __name__ == "__main__":
    run_queue_pipeline()
