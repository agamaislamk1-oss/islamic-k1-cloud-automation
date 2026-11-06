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
from typing import List, Dict, Any, Optional
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
    """Membuat file .SRT standar untuk diunggah ke fitur Subtitle/CC YouTube."""
    lines = []
    idx = 1
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
        idx += 1

    with open(output_srt_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def render_final_video(
    input_video_path: str,
    outro_video_path: str,
    logo_path: str,
    ass_subtitle_path: str = "",
    fonts_dir: str = "",
    output_video_path: str = "",
    cut_last_seconds: float = 4.0,
) -> float:
    """
    Memproses video secara lengkap dengan FFmpeg (TANPA SUBTITLE sesuai permintaan):
    1. Memotong 4 detik terakhir dari durasi nyata video utama (menghilangkan logo NotebookLM).
    2. Menambahkan logo Islamic K1 ukuran kecil di pojok kanan atas sepanjang video.
    3. Menyambungkan video SUBSCRIBE ISLAMIC K1 di akhir video.
    """
    original_duration = get_video_duration(input_video_path)
    trimmed_duration = max(1.0, original_duration - cut_last_seconds)

    filter_complex = (
        f"[0:v]trim=0:{trimmed_duration:.3f},setpts=PTS-STARTPTS,"
        f"scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[main_v];"
        f"[0:a]atrim=0:{trimmed_duration:.3f},asetpts=PTS-STARTPTS,"
        f"aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[main_a];"
        f"[1:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[outro_v];"
        f"[1:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[outro_a];"
        f"[main_v][main_a][outro_v][outro_a]concat=n=2:v=1:a=1[joined_v][joined_a];"
        f"[2:v]scale=110:-1[logo_small];"
        f"[joined_v][logo_small]overlay=W-w-30:25:format=auto,format=yuv420p[final_v]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_video_path,
        "-i", outro_video_path,
        "-i", logo_path,
        "-filter_complex", filter_complex,
        "-map", "[final_v]",
        "-map", "[joined_a]",
        "-c:v", "libx264",
        "-preset", "faster",
        "-crf", "21",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
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
