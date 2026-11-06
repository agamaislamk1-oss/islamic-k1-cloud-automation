"""
Modul AI Transkripsi, Metadata Islami Viral (Sesuai Kebijakan YouTube),
Timeline Otomatis, Klasifikasi Playlist Kelas PAI, dan Terjemahan Multi-Bahasa Global.
Menggunakan kombinasi:
1. Faster-Whisper (lokal di Cloud VM, bebas error 503, akurasi timestamp tinggi untuk subtitle Mala's Handwriting)
2. Gemini API (gemini-3.6-flash, gemini-3.5-flash-lite, gemini-3.1-flash-lite, gemini-3.8-flash)
   untuk menyusun Judul, Deskripsi 3 Paragraf Islami, Timeline, Hashtag, & Terjemahan 10 Bahasa.
"""

import os
import re
import time
import json
import subprocess
from typing import Dict, Any, List


def extract_compressed_audio(video_path: str, audio_output_path: str, max_duration: float) -> str:
    """
    Mengekstrak audio MP3 ringan (mono, 16kHz, 32kbps) dari video yang sudah dipotong 4 detik terakhir.
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-t", f"{max_duration:.2f}",
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-b:a", "32k",
        audio_output_path,
    ]
    subprocess.run(cmd, check=True)
    return audio_output_path


def transcribe_audio_with_whisper(audio_path: str, max_duration: float) -> List[Dict[str, Any]]:
    """
    Mentranskripsikan audio menggunakan Faster-Whisper (CPU int8) secara lokal di Cloud Runner
    agar menghasilkan timestamp subtitle per kalimat pendek yang sangat akurat dan bebas limit API.
    """
    from faster_whisper import WhisperModel

    print("[WHISPER] Memulai transkripsi audio untuk subtitle Mala's Handwriting...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments_gen, _ = model.transcribe(
        audio_path,
        language="id",
        beam_size=3,
        vad_filter=True,
        word_timestamps=False,
    )

    transcript_segments: List[Dict[str, Any]] = []
    for seg in segments_gen:
        start_s = float(seg.start)
        end_s = min(float(seg.end), max_duration)
        if start_s >= max_duration:
            break
        text = seg.text.strip()
        if not text:
            continue
        # Jika kalimat terlalu panjang (> 14 kata), bagi menjadi 2 bagian agar tetap kecil & rapi di tengah bawah
        words = text.split()
        if len(words) > 14:
            mid = len(words) // 2
            mid_time = start_s + (end_s - start_s) * 0.5
            transcript_segments.append({"start": round(start_s, 2), "end": round(mid_time, 2), "text": " ".join(words[:mid])})
            transcript_segments.append({"start": round(mid_time, 2), "end": round(end_s, 2), "text": " ".join(words[mid:])})
        else:
            transcript_segments.append({"start": round(start_s, 2), "end": round(end_s, 2), "text": text})

    print(f"[WHISPER] Selesai! Dihasilkan {len(transcript_segments)} baris subtitle.")
    return transcript_segments


def validate_youtube_timeline(chapters: List[Dict[str, Any]], total_duration: float) -> str:
    """
    Memastikan format Timeline/Chapters 100% mematuhi syarat resmi YouTube:
    1. Chapter pertama WAJIB 00:00.
    2. Minimal ada 3 chapter.
    3. Jarak antar chapter minimal 10 detik dan berurutan naik.
    """
    valid_chapters = []
    last_sec = -15

    for ch in chapters:
        try:
            sec = int(float(ch.get("time_seconds", 0)))
        except Exception:
            sec = 0
        title = str(ch.get("title", "Pembahasan Utama")).strip()
        if not valid_chapters:
            sec = 0
        if sec >= total_duration - 5:
            continue
        if sec - last_sec >= 10:
            valid_chapters.append((sec, title))
            last_sec = sec

    if len(valid_chapters) < 3:
        valid_chapters = [
            (0, "Pembukaan & Pengantar Materi"),
            (int(total_duration * 0.35), "Pembahasan Inti & Hikmah Utama"),
            (int(total_duration * 0.75), "Kesimpulan, Pesan Keluarga Muslim & Penutup"),
        ]

    lines = []
    for sec, title in valid_chapters:
        hours = sec // 3600
        minutes = (sec % 3600) // 60
        secs = sec % 60
        if total_duration >= 3600 or hours > 0:
            ts = f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            ts = f"{minutes:02d}:{secs:02d}"
        lines.append(f"{ts} {title}")

    return "\n".join(lines)


def build_fallback_metadata(
    original_filename: str,
    trimmed_duration: float,
    transcript_segments: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Cadangan otomatis jika seluruh server Gemini sedang mengalami gangguan 503 serentak,
    sehingga proses upload ke YouTube tetap berjalan tanpa pernah gagal.
    """
    clean_title = os.path.splitext(original_filename)[0].replace("_", " ").strip()
    is_long = trimmed_duration > 1200.0
    num_chapters = 14 if is_long else 6
    step = max(30, int(trimmed_duration // num_chapters))

    chapters = [{"time_seconds": 0, "title": f"Pembukaan & Pengantar: {clean_title}"}]
    for i in range(1, num_chapters):
        t_sec = i * step
        if t_sec >= trimmed_duration - 15:
            break
        # Cari teks transkrip terdekat dengan waktu t_sec
        sample_topic = f"Pembahasan Bagian {i}"
        for seg in transcript_segments:
            if seg["start"] >= t_sec:
                words = seg["text"].split()[:6]
                if len(words) >= 3:
                    sample_topic = " ".join(words).capitalize()
                break
        chapters.append({"time_seconds": t_sec, "title": sample_topic})

    paragraphs = [
        f"Assalamu'alaikum Warahmatullahi Wabarakatuh.\nSelamat datang kembali di channel Islamic K1, sahabat belajar dan inspirasi kebaikan untuk seluruh keluarga Muslim. Pada kesempatan penuh berkah ini, kita akan menyimak pembahasan mendalam mengenai {clean_title} yang disajikan secara ringkas, jelas, dan mudah dipahami.",
        f"Di dalam video {clean_title} ini, kita mempelajari berbagai konsep penting, dalil, serta hikmah aplikatif yang dapat langsung diterapkan dalam kehidupan sehari-hari. Materi ini sangat cocok disimak bersama keluarga tercinta maupun sebagai pendamping belajar Pendidikan Agama Islam dan Budi Pekerti.",
        "Semoga ilmu yang kita pelajari hari ini menjadi amal jariyah dan membawa keberkahan bagi keluarga kita di dunia maupun di akhirat. Jangan lupa klik tombol Subscribe, Like, dan bagikan video channel Islamic K1 ini kepada keluarga dan sahabat lainnya.\nWassalamu'alaikum Warahmatullahi Wabarakatuh.",
    ]

    localizations = {}
    try:
        from deep_translator import GoogleTranslator

        base_desc = "\n\n".join(paragraphs)
        for lang_code in ["en", "ar", "ms", "tr", "ur", "fr", "de", "es", "ru"]:
            try:
                tr_title = GoogleTranslator(source="id", target=lang_code).translate(clean_title)[:95]
                tr_desc = GoogleTranslator(source="id", target=lang_code).translate(base_desc)[:4500]
                localizations[lang_code] = {"title": tr_title, "description": tr_desc}
            except Exception:
                pass
    except Exception:
        pass

    return {
        "title": f"{clean_title} | Kajian & Materi PAI Keluarga Muslim"[:95],
        "thumbnail_hook": clean_title.upper()[:40],
        "thumbnail_badge": "ISLAMIC K1 • KELUARGA MUSLIM",
        "description_paragraphs": paragraphs,
        "chapters": chapters,
        "hashtags": ["#IslamicK1", "#KeluargaMuslim", "#PendidikanAgamaIslam", "#KajianIslam", "#BelajarIslam", "#PAI"],
        "tags": ["Islamic K1", "Keluarga Muslim", "Pendidikan Agama Islam", clean_title[:50], "Kajian Islam"],
        "playlist_name": "Kajian Keluarga Muslim",
        "recommended_publish_slot": "MALAM",
        "localizations": localizations,
    }


def analyze_video_with_gemini(
    video_path: str,
    trimmed_duration: float,
    original_filename: str,
    gemini_api_key: str,
) -> Dict[str, Any]:
    """
    1. Transkripsi audio presisi tinggi dengan Faster-Whisper untuk subtitle Mala's Handwriting.
    2. Analisis teks transkrip dengan Gemini (menggunakan model-model yang aktif & cepat:
       gemini-3.6-flash, gemini-3.5-flash-lite, gemini-3.1-flash-lite, gemini-flash-lite-latest)
       untuk menghasilkan Judul, Deskripsi 3 Paragraf Islami, Timeline, Hashtag, Playlist, & Terjemahan 10 Bahasa.
    """
    temp_audio = video_path + ".temp_audio.mp3"
    extract_compressed_audio(video_path, temp_audio, trimmed_duration)

    # 1. Transkripsi menggunakan Faster-Whisper
    transcript_segments = transcribe_audio_with_whisper(temp_audio, trimmed_duration)
    if os.path.exists(temp_audio):
        os.remove(temp_audio)

    # Ringkas transkrip per 15-20 detik untuk dikirim sebagai teks ringan ke Gemini
    sampled_lines = []
    last_t = -20.0
    for seg in transcript_segments:
        if seg["start"] - last_t >= 12.0 or len(sampled_lines) < 20:
            m_sec = int(seg["start"])
            sampled_lines.append(f"[{m_sec // 60:02d}:{m_sec % 60:02d} ({m_sec}s)] {seg['text']}")
            last_t = seg["start"]
    transcript_summary_text = "\n".join(sampled_lines[:180])

    is_long_video = trimmed_duration > 1200.0  # > 20 menit (1200 detik)
    timeline_instruction = (
        "Karena durasi video LEBIH DARI 20 MENIT, buat daftar `chapters` yang SANGAT LENGKAP DAN MENDETAIL "
        "(minimal 12 hingga 22 titik waktu/chapter yang merinci setiap sub-topik pembahasan)."
        if is_long_video
        else "Karena durasi video KURANG DARI 20 MENIT, buat daftar `chapters` dengan detail STANDAR "
             "(6 hingga 9 titik waktu/chapter utama)."
    )

    prompt = f"""
Anda adalah pakar strategi konten dakwah & pendidikan Islam YouTube profesional untuk channel **Islamic K1** (https://www.youtube.com/@islamick1832) dengan target audiens **Keluarga Muslim & Pelajar Muslim**.
Nama file asli dari NotebookLM: "{original_filename}"
Durasi bersih video (setelah dipotong 4 detik terakhir): {trimmed_duration:.1f} detik ({trimmed_duration/60:.1f} menit).

Berikut adalah transkrip ber-timestamp dari isi video tersebut:
{transcript_summary_text}

TUGAS ANDA (Kembalikan HANYA dalam format JSON valid sesuai skema):
1. `title`: Judul YouTube bahasa Indonesia (maksimal 75 karakter, TANPA menulis kode kelas/bab di akhir karena sistem akan otomatis menambahkan akhiran seragam seperti `I PAIBP 5 I Bab 1` atau `I Fikih 5 I Bab 1`) yang sesuai dengan topik "{original_filename}", menarik perhatian keluarga & pelajar Muslim, memancing rasa ingin tahu secara positif (CTR tinggi), jujur sesuai isi materi, Islami, dan 100% mematuhi aturan YouTube.
2. `thumbnail_hook`: Teks singkat 3-6 kata yang kuat untuk dipasang di gambar Thumbnail (contoh: "PANDUAN PUASA SUNAH & HIKMAHNYA").
3. `thumbnail_badge`: Kategori singkat 2-4 kata untuk label atas Thumbnail (contoh: "PAI KELAS 6 • ISLAMIC K1").
4. `description_paragraphs`: Buat minimal 3 paragraf deskripsi yang rapi, hangat, menginspirasi keluarga Muslim, dan tertata dengan baik:
   - Paragraf 1 WAJIB diawali dengan salam lengkap: "Assalamu'alaikum Warahmatullahi Wabarakatuh." lalu memperkenalkan topik video dengan hangat kepada keluarga Muslim.
   - Paragraf 2 berisi ulasan mendalam mengenai materi, manfaat, dan poin-poin hikmah penting yang dibahas di dalam video.
   - Paragraf 3 berisi ajakan mengamalkan ilmu dalam kehidupan sehari-hari, ajakan ramah untuk Subscribe & membagikan video channel Islamic K1, serta WAJIB diakhiri dengan doa dan salam penutup: "Wassalamu'alaikum Warahmatullahi Wabarakatuh."
5. `chapters`: {timeline_instruction}
   - Chapter pertama WAJIB dimulai pada `time_seconds`: 0.
   - Urutkan `time_seconds` secara kronologis berdasarkan transkrip di atas dan pastikan tidak melebihi {int(trimmed_duration - 5)} detik.
6. `hashtags`: Buat 6 hingga 8 hashtag Islami yang paling relevan (diawali `#`, tanpa spasi, contoh: `["#IslamicK1", "#KeluargaMuslim", "#PendidikanAgamaIslam"]`). Jangan lebih dari 8 hashtag agar 100% aman dari kebijakan anti-spam YouTube.
7. `tags`: Buat 10 hingga 14 kata kunci pencarian YouTube yang relevan (total di bawah 400 karakter).
8. `playlist_name`: Jika nama file menyebutkan kelas (misal "PAI 6", "PAI 7", "PAI 8", "PAI 9"), tulis kelasnya (contoh: "PAI SD Kelas 6 (K13 & Merdeka)", "PAI SMP Kelas 7 (K13 & Merdeka)", "PAI SMP Kelas 8 (K13 & Merdeka)").
9. `recommended_publish_slot`: Pilih jam tayang utama (WIB) yang paling cocok dengan isi video agar cepat viral:
   - `"SUBUH"` (05:00 WIB - cocok untuk dzikir, Al-Quran, ibadah, puasa, amalan harian)
   - `"SIANG"` (12:00 WIB - cocok untuk fiqih praktis, muamalah, edukasi singkat)
   - `"MALAM"` (19:00 WIB - cocok untuk sejarah peradaban Islam, kisah teladan, kajian keluarga)
10. `localizations`: Terjemahkan `title` dan ringkasan deskripsi (tetap diawali & diakhiri salam Islami yang santun dalam bahasa tersebut) ke 9 bahasa internasional berikut agar video bisa diakses & dimengerti di seluruh dunia:
   - `"en"` (Inggris)
   - `"ar"` (Arab)
   - `"ms"` (Melayu)
   - `"tr"` (Turki)
   - `"ur"` (Urdu)
   - `"fr"` (Prancis)
   - `"de"` (Jerman)
   - `"es"` (Spanyol)
   - `"ru"` (Rusia)

Kembalikan output dalam JSON murni dengan struktur persis:
{{
  "title": "...",
  "thumbnail_hook": "...",
  "thumbnail_badge": "...",
  "description_paragraphs": ["Paragraf 1...", "Paragraf 2...", "Paragraf 3..."],
  "chapters": [{{"time_seconds": 0, "title": "..."}}],
  "hashtags": ["#IslamicK1", "..."],
  "tags": ["islamic k1", "..."],
  "playlist_name": "...",
  "recommended_publish_slot": "MALAM",
  "localizations": {{
    "en": {{"title": "...", "description": "..."}},
    "ar": {{"title": "...", "description": "..."}},
    "ms": {{"title": "...", "description": "..."}},
    "tr": {{"title": "...", "description": "..."}},
    "ur": {{"title": "...", "description": "..."}},
    "fr": {{"title": "...", "description": "..."}},
    "de": {{"title": "...", "description": "..."}},
    "es": {{"title": "...", "description": "..."}},
    "ru": {{"title": "...", "description": "..."}}
  }}
}}
"""

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=gemini_api_key)
    data = None
    candidate_models = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.5-flash-lite",
        "gemini-flash-latest",
    ]
    for model_name in candidate_models:
        try:
            print(f"[AI] Menyusun metadata & terjemahan 10 bahasa dengan model {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3,
                ),
            )
            data = json.loads(response.text)
            print(f"[AI] Berhasil menyusun metadata dengan model {model_name}!")
            break
        except Exception as e:
            print(f"[AI] Model {model_name} sibuk ({e}), mencoba model berikutnya...")
            time.sleep(2)

    if not data:
        print("[AI] Menggunakan generator metadata cadangan karena semua model Gemini sedang penuh...")
        data = build_fallback_metadata(original_filename, trimmed_duration, transcript_segments)

    data["transcript_segments"] = transcript_segments

    paragraphs = data.get("description_paragraphs", [])
    if len(paragraphs) < 3:
        paragraphs = [
            "Assalamu'alaikum Warahmatullahi Wabarakatuh.\nSelamat datang kembali di channel Islamic K1, ruang belajar dan inspirasi penuh berkah untuk keluarga Muslim.",
            "Pada video kali ini, kita bersama-sama menyimak pembahasan penting yang insyaAllah sangat bermanfaat untuk menambah ilmu, keimanan, dan ketakwaan keluarga kita.",
            "Semoga ilmu yang disampaikan membawa keberkahan dunia dan akhirat. Jangan lupa klik Subscribe dan bagikan kebaikan ini kepada keluarga tercinta. Wassalamu'alaikum Warahmatullahi Wabarakatuh.",
        ]

    if "assalamu" not in paragraphs[0].lower():
        paragraphs[0] = "Assalamu'alaikum Warahmatullahi Wabarakatuh.\n\n" + paragraphs[0]
    if "wassalamu" not in paragraphs[-1].lower() and "assalamu" not in paragraphs[-1].lower():
        paragraphs[-1] = paragraphs[-1] + "\n\nWassalamu'alaikum Warahmatullahi Wabarakatuh."

    timeline_str = validate_youtube_timeline(data.get("chapters", []), trimmed_duration)
    hashtags = data.get("hashtags", ["#IslamicK1", "#KeluargaMuslim", "#KajianIslam"])[:8]
    hashtags_str = " ".join(hashtags)

    opening_and_body = "\n\n".join(paragraphs[:-1])
    closing_paragraph = paragraphs[-1]

    full_description = (
        f"{opening_and_body}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 TIMELINE / CHAPTER PEMBAHASAN:\n"
        f"{timeline_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{closing_paragraph}\n\n"
        f"{hashtags_str}"
    )

    data["full_description"] = full_description
    data["timeline_text"] = timeline_str

    # Pastikan 10 bahasa global (id + 9 bahasa internasional) SELALU terisi penuh untuk Judul & Deskripsi
    locs = data.get("localizations") or {}
    target_langs = ["en", "ar", "ms", "tr", "ur", "fr", "de", "es", "ru"]
    missing_langs = [lg for lg in target_langs if lg not in locs or not locs[lg].get("title")]
    if missing_langs:
        try:
            from deep_translator import GoogleTranslator
            base_t = data.get("title", original_filename)
            for lg in missing_langs:
                try:
                    tr_t = GoogleTranslator(source="id", target=lg).translate(base_t)[:95]
                    tr_d = GoogleTranslator(source="id", target=lg).translate(full_description[:3500])[:4800]
                    locs[lg] = {"title": tr_t, "description": tr_d}
                except Exception:
                    pass
        except Exception:
            pass
    data["localizations"] = locs
    return data
