"""
Modul Editing Video & Pembuatan Thumbnail Profesional High-CTR untuk Channel Islamic K1 (@islamick1832)
Fitur:
1. Deteksi durasi nyata (real frame packet timestamp) agar tidak tertipu header MP4 NotebookLM.
2. Potong 4 detik terakhir dari video NotebookLM (menghapus watermark NotebookLM).
3. Pasang transkrip/subtitle di tengah bawah dengan font "Mala's Handwriting" ukuran kecil.
4. Pasang logo Islamic K1 ukuran kecil di pojok kanan atas sepanjang video.
5. Sambungkan video outro "SUBSCRIBE ISLAMIC K1.mp4" di bagian akhir.
6. Buat Thumbnail YouTube Modern, Cerah, Kontras Tinggi & Menarik (1280x720, < 2MB):
   - Memilih frame paling cerah & tajam dari beberapa titik waktu di video.
   - Desain Split-Card Modern Islami (Panel Royal Emerald & Emas di kiri + Visual Cerah Berbingkai di kanan)
     sehingga teks judul TIDAK menabrak teks slide di dalam video.
   - Font ekstra tebal (Bold Sans-Serif) dengan efek 3D Shadow & warna kontras Kuning Emas + Putih.
"""

import os
import re
import subprocess
import textwrap
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageStat

_LOCAL_FFMPEG_BIN = r"E:\ISLAMIC K1\Video Extender\ffmpeg\bin"
if os.path.isdir(_LOCAL_FFMPEG_BIN) and _LOCAL_FFMPEG_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _LOCAL_FFMPEG_BIN + os.pathsep + os.environ.get("PATH", "")


def get_video_duration(video_path: str) -> float:
    """
    Mendapatkan durasi video NYATA dalam detik berdasarkan timestamp paket video terakhir
    (agar akurat meskipun header container MP4 NotebookLM menulis durasi yang salah).
    """
    try:
        cmd_pkt = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "packet=pts_time",
            "-of", "csv=p=0",
            video_path,
        ]
        res_pkt = subprocess.run(cmd_pkt, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        valid_times = []
        for line in res_pkt.stdout.splitlines():
            val = line.strip().rstrip(",")
            if val and val != "N/A":
                try:
                    valid_times.append(float(val))
                except ValueError:
                    pass
        if valid_times:
            return max(valid_times)
    except Exception:
        pass

    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return float(result.stdout.strip())


def format_ass_time(seconds: float) -> str:
    """Konversi detik ke format waktu ASS (H:MM:SS.cc)."""
    if seconds < 0:
        seconds = 0.0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int(round((seconds - int(seconds)) * 100))
    if centisecs >= 100:
        centisecs = 99
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"


def format_srt_time(seconds: float) -> str:
    """Konversi detik ke format waktu SRT (HH:MM:SS,mmm) untuk upload Closed Captions YouTube."""
    if seconds < 0:
        seconds = 0.0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        millis = 999
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def create_ass_subtitle(
    segments: List[Dict[str, Any]],
    output_ass_path: str,
    max_duration: float,
    font_name: str = "Mala's Handwriting",
    font_size: int = 14,
) -> None:
    """
    Membuat file subtitle .ASS dengan font Mala's Handwriting ukuran kecil
    di posisi Tengah Bawah (Alignment=2).
    """
    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 384
PlayResY: 288
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,1.2,0.5,2,20,20,14,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [ass_header]
    for seg in segments:
        start_sec = float(seg.get("start", 0.0))
        end_sec = float(seg.get("end", start_sec + 3.0))
        if start_sec >= max_duration:
            continue
        if end_sec > max_duration:
            end_sec = max_duration
        text = str(seg.get("text", "")).strip().replace("\n", " ")
        if not text:
            continue
        start_str = format_ass_time(start_sec)
        end_str = format_ass_time(end_sec)
        lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}\n")

    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def create_srt_subtitle(
    segments: List[Dict[str, Any]],
    output_srt_path: str,
    max_duration: float,
) -> None:
    """Membuat file .SRT standar untuk diunggah ke fitur Subtitle/CC YouTube (+ Info Buku Mengaji di akhir)."""
    lines = []
    idx = 1
    last_end = 0.0
    for seg in segments:
        start_sec = float(seg.get("start", 0.0))
        end_sec = float(seg.get("end", start_sec + 3.0))
        if start_sec >= max_duration:
            continue
        if end_sec > max_duration:
            end_sec = max_duration
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        lines.append(f"{idx}\n{format_srt_time(start_sec)} --> {format_srt_time(end_sec)}\n{text}\n\n")
        last_end = max(last_end, end_sec)
        idx += 1

    # Usulan 4: Sisipkan informasi Buku Catatan Materi & Aktivitas Perkembangan Mengaji di baris akhir CC resmi YouTube
    promo_start = max(0.5, min(last_end + 0.2, max_duration - 4.5))
    promo_end = max(promo_start + 3.5, max_duration)
    promo_cc_text = (
        "📖 Miliki Buku Catatan Materi & Aktivitas Perkembangan Mengaji (Jilid 1, 2, 3) "
        "— Klik Link Shopee di Deskripsi & Komentar Video!"
    )
    lines.append(f"{idx}\n{format_srt_time(promo_start)} --> {format_srt_time(promo_end)}\n{promo_cc_text}\n\n")

    with open(output_srt_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def get_video_dimensions(video_path: str) -> Tuple[int, int]:
    """Mengembalikan (width, height) efektif video dengan memperhitungkan rotasi metadata HP/Shorts."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height:stream_side_data=rotation:stream_tags=rotate",
            "-of", "json",
            video_path,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        import json as _json
        info = _json.loads(res.stdout or "{}")
        streams = info.get("streams", [{}])
        st = streams[0] if streams else {}
        w = int(st.get("width") or 1920)
        h = int(st.get("height") or 1080)
        rot = 0
        tags = st.get("tags") or {}
        if "rotate" in tags:
            rot = abs(int(float(tags["rotate"])))
        for sd in st.get("side_data_list") or []:
            if "rotation" in sd:
                rot = abs(int(float(sd["rotation"])))
        if rot in (90, 270):
            w, h = h, w
        return w, h
    except Exception:
        return 1920, 1080


def is_portrait_video(video_path: str) -> bool:
    """True jika tinggi video lebih besar dari lebarnya (format Vertikal 9:16 / Shorts)."""
    w, h = get_video_dimensions(video_path)
    return h > w


def detect_smart_end_trim_timestamp(
    video_path: str,
    orig_duration: float,
    transcript_segments: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[float, float]:
    """
    Mendeteksi titik potong akhir video NotebookLM secara cerdas & presisi TEPAT SETELAH
    ucapan salam penutup selesai diucapkan lengkap (tidak dipatok kaku 4 detik):
    1. Memindai bagian akhir audio (14 detik terakhir) dengan FFmpeg `silencedetect` untuk menemukan
       detik tepat saat suara narator selesai berbicara sebelum layar hening watermark NotebookLM muncul.
    2. Memeriksa timestamp akhir segmen transkrip Whisper (`transcript_segments[-1]['end']`) agar
       kalimat salam penutup ('Wassalamu'alaikum warahmatullahi wabarakatuh') TIDAK PERNAH terpotong!
    3. Memberikan jeda napas alami +0.35 detik setelah kata terakhir selesai diucapkan.
    Mengembalikan tuple: (trimmed_duration, cut_last_seconds).
    """
    if orig_duration <= 6.0:
        return orig_duration, 0.0

    # 1. Deteksi batas akhir suara bicara menggunakan FFmpeg silencedetect pada 14 detik terakhir
    tail_window = min(14.0, orig_duration * 0.5)
    start_offset = max(0.0, orig_duration - tail_window)
    silence_speech_end = 0.0
    try:
        cmd = [
            "ffmpeg",
            "-ss", f"{start_offset:.3f}",
            "-i", video_path,
            "-vn",
            "-af", "silencedetect=n=-35dB:d=0.22",
            "-f", "null",
            "-",
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        starts = [float(x) for x in re.findall(r"silence_start:\s*([\d.]+)", res.stderr or "")]
        ends = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", res.stderr or "")]
        if starts:
            last_s_start = start_offset + starts[-1]
            last_s_end = (start_offset + ends[-1]) if len(ends) >= len(starts) else orig_duration
            # Jika hening terakhir berlangsung sampai ujung video (atau < 0.35s dari ujung video)
            if orig_duration - last_s_end <= 0.45 and (orig_duration - last_s_start) <= 7.0:
                silence_speech_end = last_s_start
    except Exception:
        pass

    # 2. Cek batas akhir segmen ucapan & apakah ada ucapan Salam di bagian akhir dari transkrip Whisper
    whisper_speech_end = 0.0
    has_closing_salam = False
    if transcript_segments:
        try:
            valid_ends = [float(seg.get("end", 0.0)) for seg in transcript_segments if float(seg.get("end", 0.0)) <= orig_duration]
            if valid_ends:
                whisper_speech_end = max(valid_ends)
            tail_text = " ".join([str(seg.get("text", "")).lower() for seg in transcript_segments[-3:]])
            if any(k in tail_text for k in ("salam", "warahmatullah", "wabarakatuh", "warohmatulloh", "wabarokatuh")):
                has_closing_salam = True
        except Exception:
            pass

    # Jika terdeteksi ada ucapan salam penutup ATAU ada jeda hening khas watermark NotebookLM di ujung:
    # potong tepat setelah salam/ucapan selesai (+0.35s) agar salam TIDAK PERNAH terpotong!
    # Namun jika video BUKAN dari NotebookLM (tidak ada salam di akhir & tidak ada jeda hening watermark),
    # otomatis potong 4.0 detik terakhir lalu sambung dengan outro Islamic K1 sesuai instruksi!
    if has_closing_salam or silence_speech_end > 0.0:
        detected_speech_end = max(silence_speech_end, whisper_speech_end)
        if detected_speech_end > (orig_duration - 8.5) and detected_speech_end < orig_duration:
            trimmed_duration = min(orig_duration - 0.5, detected_speech_end + 0.35)
        else:
            trimmed_duration = max(1.0, orig_duration - 2.0)
    else:
        # Video non-NotebookLM: potong 4 detik terakhir dan sambung dengan video outro Islamic K1
        trimmed_duration = max(1.0, orig_duration - 4.0)

    cut_last_seconds = max(0.0, orig_duration - trimmed_duration)
    return trimmed_duration, cut_last_seconds


def _load_book_cover_images_from_env() -> List[str]:
    """Mengambil daftar file gambar sampul buku yang ditaruh pengguna di folder `00_Assets`."""
    covers_dir = os.environ.get("ISLAMICK1_BOOK_COVERS_DIR", "")
    if not covers_dir or not os.path.isdir(covers_dir):
        return []
    files = sorted(
        [
            os.path.join(covers_dir, f)
            for f in os.listdir(covers_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
        ]
    )
    return files


def _create_lower_third_promo_png(out_png_path: str, font_path: str, is_portrait: bool = False) -> str:
    """
    Usulan 3: Membuat overlay transparan Pop-Up Lower-Third Banner (muncul 6 detik di tengah video)
    lengkap dengan gambar sampul buku dari `00_Assets` (jika ada) + info Jilid 1, 2, 3.
    """
    W, H = (1080, 1920) if is_portrait else (1920, 1080)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    covers = _load_book_cover_images_from_env()

    if is_portrait:
        bx1, by1, bx2, by2 = 44, H - 360, W - 44, H - 210
    else:
        bx1, by1, bx2, by2 = 64, H - 185, 1340, H - 52

    draw.rounded_rectangle([bx1, by1, bx2, by2], radius=22, fill=(6, 32, 24, 242), outline=(255, 208, 0, 255), width=4)
    text_x = bx1 + 28
    if covers:
        try:
            cov_im = Image.open(covers[0]).convert("RGBA")
            ch = (by2 - by1) - 20
            cw = max(65, int(cov_im.width * (ch / float(max(1, cov_im.height)))))
            cov_im = cov_im.resize((min(130, cw), ch), Image.Resampling.LANCZOS)
            canvas.paste(cov_im, (bx1 + 16, by1 + 10), cov_im)
            text_x = bx1 + cov_im.width + 32
        except Exception:
            pass

    f_title = _load_bold_font(23 if is_portrait else 27, font_path)
    f_sub = _load_bold_font(19 if is_portrait else 22, font_path)
    draw.text((text_x, by1 + 22), "📖 BUKU CATATAN MATERI & AKTIVITAS MENGAJI (JILID 1, 2, 3)", font=f_title, fill=(255, 216, 35, 255))
    draw.text((text_x, by1 + 66), "👉 Pesan di Shopee: Klik Link Resmi di Deskripsi & Komentar Pertama!", font=f_sub, fill=(255, 255, 255, 250))
    canvas.save(out_png_path, "PNG")
    return out_png_path


def _build_product_bumper_mp4(work_dir: str, font_path: str, is_portrait: bool = False) -> Optional[str]:
    """
    Usulan 2: Membuat klip video 4.2 detik (Kartu Visual Sampul Buku dari `00_Assets` + Suara Narator)
    yang otomatis diselipkan tepat sebelum video outro `SUBSCRIBE ISLAMIC K1.mp4`.
    """
    import asyncio

    try:
        W, H = (1080, 1920) if is_portrait else (1920, 1080)
        bumper_png = os.path.join(work_dir, "product_bumper_card.png")
        bumper_mp3 = os.path.join(work_dir, "product_bumper_vo.mp3")
        bumper_mp4 = os.path.join(work_dir, "product_bumper_clip.mp4")

        canvas = Image.new("RGBA", (W, H), (6, 34, 26, 255))
        draw = ImageDraw.Draw(canvas)
        for y in range(0, H, 6):
            t = y / float(H)
            draw.rectangle([0, y, W, y + 6], fill=(int(10 * (1 - t) + 4 * t), int(48 * (1 - t) + 20 * t), int(36 * (1 - t) + 15 * t), 255))
        draw.rounded_rectangle([28, 28, W - 28, H - 28], radius=28, outline=(255, 208, 0, 220), width=4)

        f_head = _load_bold_font(36 if is_portrait else 46, font_path)
        f_sub = _load_bold_font(26 if is_portrait else 32, font_path)
        f_pill = _load_bold_font(24 if is_portrait else 28, font_path)

        draw.rounded_rectangle([W // 2 - 290, 56, W // 2 + 290, 114], radius=16, fill=(255, 208, 0, 255))
        draw.text((W // 2 - 255, 69), "📖 REKOMENDASI BUKU MENGAJI", font=f_pill, fill=(8, 32, 24, 255))

        title_lines = ["ISLAMIC STUDIES: BUKU CATATAN MATERI", "& AKTIVITAS PERKEMBANGAN MENGAJI"]
        for i_l, tl in enumerate(title_lines):
            draw.text((70 if is_portrait else 180, 140 + i_l * 56), tl, font=f_head, fill=(255, 255, 255, 255))

        covers = _load_book_cover_images_from_env()
        mid_y = 320 if is_portrait else 280
        box_h = 680 if is_portrait else 480
        if covers:
            n_cov = min(3, len(covers))
            slot_w = (W - 160) // n_cov
            for idx_c, cpath in enumerate(covers[:3]):
                try:
                    cim = Image.open(cpath).convert("RGB")
                    tw = min(slot_w - 30, int(cim.width * (box_h / float(max(1, cim.height)))))
                    cim = cim.resize((max(180, tw), box_h), Image.Resampling.LANCZOS)
                    cx = 80 + idx_c * slot_w + (slot_w - cim.width) // 2
                    draw.rounded_rectangle([cx - 6, mid_y - 6, cx + cim.width + 6, mid_y + box_h + 6], radius=18, fill=(255, 208, 0, 255))
                    canvas.paste(cim.convert("RGBA"), (cx, mid_y))
                except Exception:
                    pass
        else:
            # Visual 3 kartu Jilid 1, 2, 3 elegan jika gambar sampul belum diunggah ke 00_Assets
            for j_idx, j_col in enumerate([(16, 88, 68), (18, 76, 98), (92, 68, 18)]):
                cw = 280 if is_portrait else 380
                ch = 360 if is_portrait else 420
                cx = (W - (3 * cw + 60)) // 2 + j_idx * (cw + 30)
                cy = mid_y + 20
                draw.rounded_rectangle([cx, cy, cx + cw, cy + ch], radius=22, fill=j_col + (255,), outline=(255, 208, 0, 255), width=4)
                draw.text((cx + 42, cy + 60), f"JILID {j_idx + 1}", font=f_head, fill=(255, 216, 35, 255))
                draw.text((cx + 32, cy + 140), "Buku Catatan\n& Aktivitas\nMengaji", font=f_sub, fill=(255, 255, 255, 245))

        bot_y = H - 340 if is_portrait else H - 220
        draw.rounded_rectangle([68, bot_y, W - 68, bot_y + 145], radius=22, fill=(12, 62, 48, 248), outline=(255, 208, 0, 255), width=4)
        draw.text((100, bot_y + 24), "📗 Jilid 1   •   📘 Jilid 2   •   📙 Jilid 3   (Tersedia di Shopee)", font=f_sub, fill=(255, 220, 40, 255))
        draw.text((100, bot_y + 78), "👉 Klik Link Pemesanan Resmi di Deskripsi & Komentar Pertama Video Ini!", font=f_pill, fill=(255, 255, 255, 255))
        canvas.convert("RGB").save(bumper_png, "PNG")

        vo_text = "Miliki juga Buku Catatan dan Aktivitas Perkembangan Mengaji Jilid satu, dua, dan tiga melalui link Shopee di deskripsi atau kolom komentar video ini."
        tts_done = False
        try:
            import edge_tts
            async def _save_vo():
                comm = edge_tts.Communicate(text=vo_text, voice="id-ID-ArdiNeural", rate="+4%")
                await comm.save(bumper_mp3)
            asyncio.run(_save_vo())
            tts_done = os.path.exists(bumper_mp3) and os.path.getsize(bumper_mp3) > 800
        except Exception:
            pass
        if not tts_done:
            from gtts import gTTS
            gTTS(text=vo_text, lang="id", slow=False).save(bumper_mp3)

        subprocess.run(
            [
                "ffmpeg", "-y", "-loop", "1", "-i", bumper_png, "-i", bumper_mp3,
                "-vf", f"fps=30,scale={W}:{H},setsar=1,format=yuv420p,fade=t=in:st=0:d=0.25",
                "-af", "aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                "-c:a", "aac", "-b:a", "192k", "-shortest", bumper_mp4,
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
        return bumper_mp4 if os.path.exists(bumper_mp4) else None
    except Exception as e:
        print(f"[INFO BUMPER BUKU] Dilewati ({e})")
        return None


def render_final_video(
    input_video_path: str,
    outro_video_path: str,
    logo_path: str,
    ass_subtitle_path: str = "",
    fonts_dir: str = "",
    output_video_path: str = "",
    cut_last_seconds: float = 4.0,
    force_portrait: Optional[bool] = None,
) -> float:
    """
    Memproses video secara lengkap dengan FFmpeg:
    1. Otomatis mendeteksi apakah video Landscape (1920x1080) atau Portrait Shorts (1080x1920).
    2. Memotong ekor akhir sesuai `cut_last_seconds` (Smart Salam Trim / 4s).
    3. Menampilkan Pop-Up Lower-Third Banner Buku Mengaji Jilid 1-3 selama 6 detik di pertengahan video (Usulan 3).
    4. Menyelipkan Kartu Visual + Suara Narator Promosi Buku Mengaji (Usulan 2) sebelum video SUBSCRIBE ISLAMIC K1.
    5. Menambahkan logo Islamic K1 ukuran kecil di pojok kanan atas sepanjang video.
    """
    original_duration = get_video_duration(input_video_path)
    trimmed_duration = max(1.0, original_duration - cut_last_seconds)
    is_vert = is_portrait_video(input_video_path) if force_portrait is None else force_portrait
    work_dir = os.path.dirname(os.path.abspath(output_video_path))

    # Buat Pop-Up Lower-Third PNG (Usulan 3) & Klip Bumper Buku Mengaji (Usulan 2)
    lt_png = os.path.join(work_dir, "lower_third_promo.png")
    _create_lower_third_promo_png(lt_png, fonts_dir, is_portrait=is_vert)
    lt_start = min(35.0, max(4.0, trimmed_duration * 0.35))
    lt_end = min(trimmed_duration - 0.5, lt_start + 6.5)

    bumper_mp4 = _build_product_bumper_mp4(work_dir, fonts_dir, is_portrait=is_vert)
    target_w, target_h = (1080, 1920) if is_vert else (1920, 1080)
    pad_col = ":color=#051c14" if is_vert else ""
    logo_w = 120 if is_vert else 110
    logo_pos = "W-w-32:36" if is_vert else "W-w-30:25"

    if bumper_mp4 and os.path.exists(bumper_mp4):
        filter_complex = (
            f"[0:v]trim=0:{trimmed_duration:.3f},setpts=PTS-STARTPTS,"
            f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2{pad_col},setsar=1,fps=30,format=yuv420p[v0_raw];"
            f"[v0_raw][4:v]overlay=0:0:enable='between(t,{lt_start:.2f},{lt_end:.2f})',format=yuv420p[main_v];"
            f"[0:a]atrim=0:{trimmed_duration:.3f},asetpts=PTS-STARTPTS,"
            f"aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[main_a];"
            f"[3:v]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2{pad_col},setsar=1,fps=30,format=yuv420p[bump_v];"
            f"[3:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[bump_a];"
            f"[1:v]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2{pad_col},setsar=1,fps=30,format=yuv420p[outro_v];"
            f"[1:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[outro_a];"
            f"[main_v][main_a][bump_v][bump_a][outro_v][outro_a]concat=n=3:v=1:a=1[joined_v][joined_a];"
            f"[2:v]scale={logo_w}:-1[logo_small];"
            f"[joined_v][logo_small]overlay={logo_pos}:format=auto,format=yuv420p[final_v]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", input_video_path,
            "-i", outro_video_path,
            "-i", logo_path,
            "-i", bumper_mp4,
            "-i", lt_png,
            "-filter_complex", filter_complex,
            "-map", "[final_v]", "-map", "[joined_a]",
            "-c:v", "libx264", "-preset", "faster", "-crf", "21",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
            output_video_path,
        ]
    else:
        filter_complex = (
            f"[0:v]trim=0:{trimmed_duration:.3f},setpts=PTS-STARTPTS,"
            f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2{pad_col},setsar=1,fps=30,format=yuv420p[v0_raw];"
            f"[v0_raw][3:v]overlay=0:0:enable='between(t,{lt_start:.2f},{lt_end:.2f})',format=yuv420p[main_v];"
            f"[0:a]atrim=0:{trimmed_duration:.3f},asetpts=PTS-STARTPTS,"
            f"aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[main_a];"
            f"[1:v]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2{pad_col},setsar=1,fps=30,format=yuv420p[outro_v];"
            f"[1:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[outro_a];"
            f"[main_v][main_a][outro_v][outro_a]concat=n=2:v=1:a=1[joined_v][joined_a];"
            f"[2:v]scale={logo_w}:-1[logo_small];"
            f"[joined_v][logo_small]overlay={logo_pos}:format=auto,format=yuv420p[final_v]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", input_video_path,
            "-i", outro_video_path,
            "-i", logo_path,
            "-i", lt_png,
            "-filter_complex", filter_complex,
            "-map", "[final_v]", "-map", "[joined_a]",
            "-c:v", "libx264", "-preset", "faster", "-crf", "21",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
            output_video_path,
        ]

    subprocess.run(cmd, check=True)
    return get_video_duration(output_video_path)


def _load_bold_font(size: int, fallback_font_path: str) -> ImageFont.FreeTypeFont:
    """
    Mencari font Sans-Serif Extra Bold / Bold sistem agar teks Thumbnail
    sangat tegas, tebal, dan mudah dibaca di beranda YouTube (bukan font tipis).
    """
    bold_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\impact.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        fallback_font_path,
    ]
    for path in bold_candidates:
        if path and os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _pick_best_video_frame(video_path: str, duration: float, temp_prefix: str) -> Image.Image:
    """
    Mengambil 5 sampel frame dari video dan memilih frame yang paling kaya warna,
    cerah, dan memiliki detail visual paling menarik (bukan layar gelap/kosong).
    """
    sample_fractions = [0.15, 0.30, 0.45, 0.60, 0.75]
    best_img = None
    best_score = -1.0

    for idx, frac in enumerate(sample_fractions):
        sec = max(1.5, min(duration - 5.0, duration * frac))
        frame_path = f"{temp_prefix}_cand_{idx}.png"
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", f"{sec:.2f}",
            "-i", video_path,
            "-frames:v", "1",
            frame_path,
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if os.path.exists(frame_path) and os.path.getsize(frame_path) > 1000:
            try:
                img = Image.open(frame_path).convert("RGB")
                stat = ImageStat.Stat(img)
                # Hitung skor kecerahan + variasi kontras warna (stddev)
                mean_brightness = sum(stat.mean) / 3.0
                color_std = sum(stat.stddev) / 3.0
                # Hindari frame yang terlalu gelap (<30) atau terlalu putih polos (>240)
                penalty = 0.5 if (mean_brightness < 35 or mean_brightness > 235) else 1.0
                score = color_std * penalty
                if score > best_score:
                    best_score = score
                    best_img = img.copy()
            except Exception:
                pass
            finally:
                try:
                    os.remove(frame_path)
                except Exception:
                    pass

    if best_img is None:
        best_img = Image.new("RGB", (1280, 720), (18, 65, 52))
    return best_img


def _draw_text_with_3d_stroke(
    draw: ImageDraw.ImageDraw,
    pos: tuple,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple,
    stroke_fill: tuple = (8, 20, 15, 255),
    stroke_width: int = 6,
    shadow_offset: int = 6,
):
    """Menggambar teks tebal dengan bayangan 3D dan garis tepi (stroke) kontras tinggi."""
    x, y = pos
    # Gambar bayangan 3D hitam pekat di bawah
    draw.text(
        (x + shadow_offset, y + shadow_offset),
        text,
        font=font,
        fill=(0, 0, 0, 230),
        stroke_width=stroke_width,
        stroke_fill=(0, 0, 0, 230),
    )
    # Gambar teks utama dengan outline tegas
    draw.text(
        (x, y),
        text,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )


def generate_youtube_thumbnail(
    video_path: str,
    logo_path: str,
    font_path: str,
    thumbnail_title: str,
    subtitle_badge: str,
    output_thumb_path: str,
    original_filename: str = "",
    book_cover_path: Optional[str] = None,
) -> str:
    """
    Membuat Thumbnail YouTube 1280x720 (<2MB) Bergaya Studio Profesional V3 (High CTR):
    - Sisi Kanan: Menampilkan GAMBAR COVER BUKU RESMI secara utuh, tajam, dengan efek kartu buku 3D
      bercahaya emas di atas latar cuplikan video yang diburamkan (atau frame video tajam jika bukan buku).
    - Sisi Kiri: Panel gradasi Royal Emerald & Gold Islami dengan Badge Mapel/Kelas/Bab menyala,
      teks Judul 3D Extra-Bold bergantian warna Putih & Kuning Emas, serta Logo & Pita Islamic K1.
    """
    duration = get_video_duration(video_path) if (video_path and os.path.exists(video_path)) else 0.0
    if duration > 0:
        raw_frame = _pick_best_video_frame(video_path, duration, output_thumb_path)
    else:
        raw_frame = Image.new("RGB", (1280, 720), (14, 52, 40))

    canvas = Image.new("RGBA", (1280, 720), (10, 38, 30, 255))

    # 1. Siapkan latar belakang sisi kanan
    right_bg = raw_frame.resize((1280, 720), Image.Resampling.LANCZOS)
    if book_cover_path and os.path.exists(book_cover_path):
        # Jika ada Cover Buku, jadikan latar kanan agak gelap & blur lembut agar Cover Buku 100% menonjol
        right_bg = right_bg.filter(ImageFilter.GaussianBlur(radius=10))
        right_bg = ImageEnhance.Brightness(right_bg).enhance(0.55)
        right_bg = ImageEnhance.Color(right_bg).enhance(1.25)
    else:
        right_bg = ImageEnhance.Brightness(right_bg).enhance(1.12)
        right_bg = ImageEnhance.Color(right_bg).enhance(1.32)
        right_bg = ImageEnhance.Contrast(right_bg).enhance(1.18)
        right_bg = ImageEnhance.Sharpness(right_bg).enhance(1.35)
    canvas.paste(right_bg.convert("RGBA"), (180, 0))

    # 2. Buat Panel Diagonal Royal Emerald & Deep Teal di Sisi Kiri
    panel_overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    p_draw = ImageDraw.Draw(panel_overlay)

    # Poligon diagonal dari kiri (lebar 720px di atas, 640px di bawah)
    p_draw.polygon([(0, 0), (720, 0), (640, 720), (0, 720)], fill=(7, 36, 30, 250))
    # Garis sabuk emas diagonal pemisah antara teks dan cover buku
    p_draw.polygon([(710, 0), (732, 0), (652, 720), (630, 720)], fill=(255, 204, 0, 255))
    p_draw.polygon([(732, 0), (740, 0), (660, 720), (652, 720)], fill=(255, 255, 255, 195))

    # Ornamen bingkai luar emas bercahaya
    p_draw.rectangle([10, 10, 1270, 710], outline=(255, 204, 0, 235), width=5)

    canvas = Image.alpha_composite(canvas, panel_overlay)

    # 3. Tampilkan Gambar COVER BUKU di Sisi Kanan (jika tersedia)
    if book_cover_path and os.path.exists(book_cover_path):
        try:
            cover_img = Image.open(book_cover_path).convert("RGBA")
            # Ukuran proporsional buku tegak di sisi kanan (tinggi ~600px, lebar menyesuaikan maks 440px)
            target_h = 600
            target_w = int(cover_img.width * (target_h / cover_img.height))
            if target_w > 450:
                target_w = 450
                target_h = int(cover_img.height * (target_w / cover_img.width))
            if target_w < 340:
                target_w = 380
                target_h = min(610, int(cover_img.height * (target_w / cover_img.width)))

            cover_resized = cover_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            cover_resized = ImageEnhance.Sharpness(cover_resized).enhance(1.25)
            cover_resized = ImageEnhance.Contrast(cover_resized).enhance(1.08)

            # Posisi tengah di area kanan (x: 745..1255, y: 0..720)
            cx = 745 + (510 - target_w) // 2
            cy = (720 - target_h) // 2

            # Gambar bayangan buku 3D & bingkai emas di sekeliling cover buku
            book_layer = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
            b_draw = ImageDraw.Draw(book_layer)
            # Bayangan hitam lembut di kanan bawah buku
            b_draw.rounded_rectangle(
                [cx + 14, cy + 16, cx + target_w + 18, cy + target_h + 18],
                radius=14,
                fill=(0, 0, 0, 185),
            )
            # Punggung buku 3D (spine) di sisi kiri cover
            b_draw.polygon(
                [
                    (cx - 12, cy + 8),
                    (cx, cy),
                    (cx, cy + target_h),
                    (cx - 12, cy + target_h - 6),
                ],
                fill=(210, 165, 15, 255),
            )
            # Bingkai emas dan putih mengelilingi cover buku
            b_draw.rounded_rectangle(
                [cx - 6, cy - 6, cx + target_w + 6, cy + target_h + 6],
                radius=10,
                fill=(255, 255, 255, 255),
                outline=(255, 204, 0, 255),
                width=5,
            )
            canvas = Image.alpha_composite(canvas, book_layer)
            canvas.paste(cover_resized, (cx, cy), cover_resized)
        except Exception as e:
            print(f"[PERINGATAN] Gagal menempelkan cover buku di thumbnail: {e}")

    draw = ImageDraw.Draw(canvas)

    # 4. Deteksi Mapel, Kelas & Bab untuk Lencana Atas yang Mencolok
    badge_str = (subtitle_badge or "KAJIAN KELUARGA MUSLIM").upper().strip()
    try:
        from book_cover_helper import parse_textbook_metadata

        meta = parse_textbook_metadata(original_filename)
        if meta.get("badge_text"):
            badge_str = meta["badge_text"]
    except Exception:
        m_pai = re.search(r"PAI\s*(\d+)\s*Bab\s*(\d+)", original_filename, re.IGNORECASE)
        if m_pai:
            badge_str = f"PAIBP {m_pai.group(1)} • BAB {m_pai.group(2)}"

    badge_font = _load_bold_font(31, font_path)
    # Gambar pita kuning emas menyala untuk Badge Mapel/Kelas/Bab di kiri atas
    draw.rounded_rectangle([42, 42, 555, 102], radius=14, fill=(255, 208, 0, 255), outline=(255, 255, 255, 240), width=3)
    draw.text((60, 54), badge_str[:26], font=badge_font, fill=(10, 28, 22, 255))

    # Tempelkan Logo Islamic K1 di sebelah kanan Badge (di dalam panel kiri atas) agar tidak menutupi Cover Buku!
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo_w = 95
            logo_h = int(logo.height * (logo_w / logo.width))
            logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            draw.rounded_rectangle([572, 26, 685, 118], radius=16, fill=(12, 54, 42, 235), outline=(255, 204, 0, 220), width=2)
            canvas.paste(logo, (581, 32), logo)
        except Exception:
            pass

    # 5. Susun Teks Hook Utama (4 Baris Besar, Tegas, Warna Berselang-seling Putih & Kuning Emas)
    clean_hook = thumbnail_title.strip()
    if original_filename:
        try:
            from book_cover_helper import parse_textbook_metadata

            t_meta = parse_textbook_metadata(original_filename)
            if len(clean_hook) < 8 or clean_hook.lower().startswith("pai"):
                clean_hook = t_meta["clean_topic"]
        except Exception:
            pass

    # Hapus akhiran "I PAIBP X I Bab Y" dari teks hook gambar jika ikut terbawa
    clean_hook = re.sub(r"\s*I\s*[A-Za-z\-\s']+\s*\d*\s*I\s*Bab\s*\d+.*$", "", clean_hook, flags=re.IGNORECASE).strip()
    clean_hook = clean_hook.upper()
    wrapped_lines = textwrap.wrap(clean_hook, width=15)[:4]

    font_size = 64 if len(wrapped_lines) <= 3 else 54
    title_font = _load_bold_font(font_size, font_path)

    y_cursor = 140
    line_spacing = font_size + 22
    for idx, line in enumerate(wrapped_lines):
        text_color = (255, 255, 255, 255) if idx % 2 == 0 else (255, 230, 0, 255)
        _draw_text_with_3d_stroke(
            draw=draw,
            pos=(44, y_cursor),
            text=line,
            font=title_font,
            fill=text_color,
            stroke_fill=(5, 18, 14, 255),
            stroke_width=7,
            shadow_offset=6,
        )
        y_cursor += line_spacing

    # 6. Tambahkan Pita Bawah ("TONTON LENGKAP DI ISLAMIC K1")
    footer_font = _load_bold_font(25, font_path)
    draw.rounded_rectangle([42, 625, 555, 676], radius=12, fill=(18, 82, 64, 255), outline=(255, 208, 0, 255), width=2)
    draw.polygon([(62, 639), (62, 663), (82, 651)], fill=(255, 208, 0, 255))
    draw.text((94, 637), "TONTON LENGKAP DI ISLAMIC K1", font=footer_font, fill=(255, 245, 200, 255))

    final_rgb = canvas.convert("RGB")
    final_rgb.save(output_thumb_path, "JPEG", quality=92, optimize=True)
    return output_thumb_path


def _generate_arabic_hijaz_instrumental_wav(duration_sec: float, out_wav_path: str) -> str:
    """
    Menghasilkan instrumen bebas copyright TANPA VOKAL bernuansa Arab/Timur Tengah/Islami (Maqam Hijaz)
    secara prosedural 100% GRATIS & 100% Aman dari klaim Hak Cipta YouTube:
    - Melodi petikan hangat ala Oud/Qanun pada tangga nada Hijaz (D4, Eb4, F#4, G4, A4, Bb4, C5, D5)
    - Harmoni Drone lembut (D3 + A3)
    - Ketukan perkusi Daf/Frame-Drum lembut nan syahdu.
    """
    import math
    import wave
    import struct

    sr = 44100
    total_samples = int(max(10.0, duration_sec) * sr)
    # Tangga nada Maqam Hijaz (khas Timur Tengah / Islami yang menenangkan)
    hijaz_freqs = [293.66, 311.13, 369.99, 392.00, 440.00, 466.16, 523.25, 587.33]
    melody_pattern = [0, 1, 2, 3, 4, 3, 2, 1, 0, 3, 4, 5, 4, 3, 2, 0]
    note_dur = 0.75  # 80 BPM syahdu

    with wave.open(out_wav_path, "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        chunk_frames = bytearray()
        for i in range(total_samples):
            t = i / float(sr)
            # Fade in 1.2s & fade out 1.8s
            master_env = 1.0
            if t < 1.2:
                master_env = t / 1.2
            elif t > duration_sec - 1.8:
                master_env = max(0.0, (duration_sec - t) / 1.8)

            # 1. Warm Arabic Drone Pad (D3 = 146.83 Hz & A3 = 220.0 Hz)
            pad = (
                math.sin(2.0 * math.pi * 146.83 * t) * 0.14
                + math.sin(2.0 * math.pi * 220.00 * t) * 0.10
                + math.sin(2.0 * math.pi * 73.42 * t) * 0.08
            )

            # 2. Melodi Petikan Oud / Qanun (Maqam Hijaz) dengan efek gema (echo)
            step_idx = int(t / note_dur)
            local_t = t - (step_idx * note_dur)
            freq = hijaz_freqs[melody_pattern[step_idx % len(melody_pattern)]]
            pluck_env = math.exp(-local_t * 4.2) * (1.0 - math.exp(-local_t * 95.0))
            oud_note = (
                math.sin(2.0 * math.pi * freq * t) * 0.65
                + math.sin(2.0 * math.pi * (freq * 2.0) * t) * 0.25
                + math.sin(2.0 * math.pi * (freq * 3.0) * t) * 0.10
            ) * pluck_env * 0.34

            # Echo dari not sebelumnya (efek ruangan/hall)
            prev_freq = hijaz_freqs[melody_pattern[(step_idx - 1) % len(melody_pattern)]]
            echo_env = math.exp(-(local_t + note_dur) * 3.2)
            oud_echo = math.sin(2.0 * math.pi * prev_freq * t) * echo_env * 0.14

            # 3. Ketukan Daf / Doumbek Halus (tiap 1.5 detik = Dum, tiap 0.75 detik = Tek lembut)
            beat_pos = t % (note_dur * 2.0)
            daf = 0.0
            if beat_pos < 0.14:
                d_env = (1.0 - beat_pos / 0.14) ** 2.4
                d_freq = 115.0 - 55.0 * (beat_pos / 0.14)
                daf = math.sin(2.0 * math.pi * d_freq * beat_pos) * d_env * 0.22

            val_l = max(-0.92, min(0.92, (pad + oud_note + daf) * master_env))
            val_r = max(-0.92, min(0.92, (pad + oud_note * 0.85 + oud_echo + daf) * master_env))
            chunk_frames.extend(struct.pack("<hh", int(val_l * 32767), int(val_r * 32767)))
            if len(chunk_frames) >= 65536:
                wf.writeframes(bytes(chunk_frames))
                chunk_frames.clear()
        if chunk_frames:
            wf.writeframes(bytes(chunk_frames))
    return out_wav_path


def render_image_to_shorts_video(
    image_path: str,
    logo_path: str,
    font_path: str,
    output_video_path: str,
    duration_sec: float = 20.0,
) -> float:
    """
    Mengubah gambar (baik Potret maupun Landscape) dari folder `05_Antrian_Gambar_Shorts`
    menjadi Video YouTube Shorts 9:16 (1080x1920) lengkap dengan:
    1. Penyesuaian otomatis rasio Potret 1080x1920 (jika gambar asli Landscape, otomatis diberi latar belakang
       blur artistik + bingkai emas Islami agar utuh & tidak terpotong).
    2. Gerakan kamera halus (Ken Burns Zoom/Pan) + Banner informasi Buku Catatan Mengaji di bagian bawah.
    3. Instrumen bebas copyright tanpa vokal bernuansa Arab/Islami (Maqam Hijaz).
    4. Logo Islamic K1 di pojok kanan atas.
    """
    W, H = 1080, 1920
    src_im = Image.open(image_path).convert("RGB")
    sw, sh = src_im.size
    src_ratio = sw / float(max(1, sh))

    # Buat 3 keyframe animasi zoom halus agar ringan & cepat di Cloud maupun Lokal
    work_dir = os.path.dirname(os.path.abspath(output_video_path))
    stage_pngs: List[str] = []
    for st_i in range(3):
        zoom_f = 1.0 + st_i * 0.035
        canvas = Image.new("RGBA", (W, H), (6, 32, 24, 255))

        # Latar belakang gradasi + blur dari gambar asli
        bg_im = src_im.resize((W, H), Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(radius=28))
        bg_im = ImageEnhance.Brightness(bg_im).enhance(0.32)
        canvas.paste(bg_im.convert("RGBA"), (0, 0))

        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(ov)
        odraw.rounded_rectangle([24, 24, W - 24, H - 24], radius=28, outline=(255, 208, 0, 130), width=3)

        if src_ratio < 0.72:
            # Gambar sudah Potret: tampilkan besar memenuhi area utama (960x1540) dengan zoom halus
            box_w, box_h = 968, 1520
            box_x, box_y = (W - box_w) // 2, 140
        else:
            # Gambar Landscape atau Kotak: sesuaikan proporsional di tengah layar dengan bingkai emas elegan
            box_w = 980
            box_h = min(1320, max(620, int(box_w / src_ratio)))
            box_x = (W - box_w) // 2
            box_y = (H - box_h) // 2 - 40

        zw, zh = int(box_w * zoom_f), int(box_h * zoom_f)
        im_z = src_im.resize((zw, zh), Image.Resampling.LANCZOS)
        lc, tc = (zw - box_w) // 2, (zh - box_h) // 2
        im_crop = im_z.crop((lc, tc, lc + box_w, tc + box_h)).convert("RGBA")

        odraw.rounded_rectangle(
            [box_x - 6, box_y - 6, box_x + box_w + 6, box_y + box_h + 6],
            radius=24, fill=(8, 40, 30, 245), outline=(255, 208, 0, 255), width=5,
        )
        canvas.paste(im_crop, (box_x, box_y))

        # Banner Produk Buku Catatan Mengaji di Bagian Bawah (Zona Aman Shorts)
        b_font = _load_bold_font(23, font_path)
        s_font = _load_bold_font(20, font_path)
        odraw.rounded_rectangle(
            [48, 1690, W - 48, 1810],
            radius=20, fill=(6, 28, 21, 238), outline=(255, 208, 0, 235), width=3,
        )
        odraw.text((76, 1708), "📖 BUKU CATATAN MATERI & AKTIVITAS MENGAJI (JILID 1-3)", font=b_font, fill=(255, 215, 35, 255))
        odraw.text((76, 1748), "👉 Cek Link Pembelian Resmi & Donasi di Deskripsi Video!", font=s_font, fill=(255, 255, 255, 245))

        png_p = os.path.join(work_dir, f"img_short_st_{st_i}.png")
        Image.alpha_composite(canvas, ov).convert("RGB").save(png_p, "PNG")
        stage_pngs.append(png_p)

    wav_path = os.path.join(work_dir, "hijaz_instrumental.wav")
    _generate_arabic_hijaz_instrumental_wav(duration_sec, wav_path)

    concat_txt = os.path.join(work_dir, "img_short_frames.txt")
    st_dur = duration_sec / 3.0
    with open(concat_txt, "w", encoding="utf-8") as cf:
        for p in stage_pngs:
            cf.write(f"file '{p.replace(chr(92), '/')}'\n")
            cf.write(f"duration {st_dur:.3f}\n")
        cf.write(f"file '{stage_pngs[-1].replace(chr(92), '/')}'\n")

    raw_mp4 = os.path.join(work_dir, "img_short_raw.mp4")
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-i", wav_path,
            "-vf", "fps=30,scale=1080:1920,setsar=1,format=yuv420p,fade=t=in:st=0:d=0.4,fade=t=out:st=19.2:d=0.6",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", "-shortest", raw_mp4,
        ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    )

    if logo_path and os.path.exists(logo_path):
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", raw_mp4, "-i", logo_path,
                "-filter_complex", "[1:v]scale=125:-1[lg];[0:v][lg]overlay=W-w-36:40:format=auto,format=yuv420p[vout]",
                "-map", "[vout]", "-map", "0:a",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-c:a", "copy", output_video_path,
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
    else:
        import shutil as _sh
        _sh.copy2(raw_mp4, output_video_path)

    return get_video_duration(output_video_path)


def render_image_and_audio_to_video(
    image_path: str,
    audio_path: str,
    outro_video_path: str,
    logo_path: str,
    font_path: str,
    output_video_path: str,
    cut_last_seconds: float = 0.0,
) -> Tuple[float, bool]:
    """
    Menggabungkan 1 Gambar (.jpg/.png/.webp) + 1 Audio (.m4a/.mp3/.wav) dari folder `06_Antrian_Gambar_Dan_Audio`,
    menyesuaikan rasio gambar secara otomatis dengan bingkai emas Islami + latar belakang blur elegan,
    menambahkan Pop-Up Buku Mengaji, Bumper Sampul Buku 1-3, Logo Islamic K1 di kanan atas,
    dan menyambungkan video outro `SUBSCRIBE ISLAMIC K1.mp4` di bagian akhir!
    Mengembalikan tuple: (final_duration, is_portrait_shorts).
    """
    audio_dur = get_video_duration(audio_path)
    src_im = Image.open(image_path).convert("RGB")
    sw, sh = src_im.size
    src_ratio = sw / float(max(1, sh))

    # Jika gambar Potret dan durasi audio <= 52 detik, jadikan YouTube Shorts (9:16); selain itu Landscape Full HD (16:9)
    is_vert = (sh > sw * 1.15) and (audio_dur <= 52.0)
    W, H = (1080, 1920) if is_vert else (1920, 1080)

    work_dir = os.path.dirname(os.path.abspath(output_video_path))
    framed_png = os.path.join(work_dir, "img_audio_framed.png")

    canvas = Image.new("RGBA", (W, H), (6, 32, 24, 255))
    bg_im = src_im.resize((W, H), Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(radius=26))
    bg_im = ImageEnhance.Brightness(bg_im).enhance(0.32)
    canvas.paste(bg_im.convert("RGBA"), (0, 0))

    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(ov)
    odraw.rounded_rectangle([24, 24, W - 24, H - 24], radius=26, outline=(255, 208, 0, 140), width=3)

    max_bw, max_bh = (W - 110, H - 220) if is_vert else (W - 160, H - 140)
    if src_ratio > (max_bw / float(max_bh)):
        box_w = max_bw
        box_h = max(320, int(box_w / src_ratio))
    else:
        box_h = max_bh
        box_w = max(320, int(box_h * src_ratio))

    box_x = (W - box_w) // 2
    box_y = (H - box_h) // 2
    odraw.rounded_rectangle(
        [box_x - 6, box_y - 6, box_x + box_w + 6, box_y + box_h + 6],
        radius=22, fill=(8, 40, 30, 245), outline=(255, 208, 0, 255), width=5,
    )
    fg_im = src_im.resize((box_w, box_h), Image.Resampling.LANCZOS).convert("RGBA")
    canvas.paste(fg_im, (box_x, box_y))
    Image.alpha_composite(canvas, ov).convert("RGB").save(framed_png, "PNG")

    combined_raw_mp4 = os.path.join(work_dir, "img_audio_combined_raw.mp4")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1", "-framerate", "30", "-i", framed_png,
            "-i", audio_path,
            "-vf", f"scale={W}:{H},setsar=1,format=yuv420p",
            "-af", "aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo",
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage", "-crf", "21",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            combined_raw_mp4,
        ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    )

    final_dur = render_final_video(
        input_video_path=combined_raw_mp4,
        outro_video_path=outro_video_path,
        logo_path=logo_path,
        fonts_dir=font_path,
        output_video_path=output_video_path,
        cut_last_seconds=cut_last_seconds,
        force_portrait=is_vert,
    )
    return final_dur, is_vert
