"""
Modul Pembuat Video Motion Grafis Explainer 3 Menit (Islami & Umum) dari Google Form
Untuk Channel YouTube Resmi: Islamic K1 (https://www.youtube.com/@islamick1832)

Fitur Utama (100% GRATIS / Rp 0):
1. Hanya dari input "Judul/Topik" & "Target Audience" di Google Form:
   - Gemini AI menyusun Naskah Voiceover ~3 menit (10 Scene terstruktur), Storyboard Visual,
     Deskripsi 3+ Paragraf (diawali & diakhiri Salam), Hashtag, Tags, Playlist, & Terjemahan 10 Bahasa.
   - Narasi WAJIB diawali Salam & sapaan sesuai Audience, serta diakhiri ajakan Subscribe Islamic K1 & Salam.
2. Voiceover Bahasa Indonesia Natural (100% Gratis):
   - Menggunakan Microsoft Edge Neural TTS (`edge-tts`: id-ID-ArdiNeural / id-ID-GadisNeural)
     dengan fallback otomatis agar tidak pernah gagal.
3. Motion Graphics Explainer Engine (1080p Full HD):
   - Setiap scene memiliki 4 tahap animasi progresif (Judul & Ikon Vektor -> Poin 1 -> Poin 2 -> Poin 3 + Kotak Dalil/Hikmah)
     yang muncul berurutan mengikuti suara narator (Kinetic Reveal) + efek gerakan kamera halus & transisi antar-scene.
4. Branding Resmi Islamic K1:
   - Menempelkan `logo.png` Islamic K1 kecil di pojok kanan atas sepanjang video.
   - Menyambungkan video `SUBSCRIBE ISLAMIC K1.mp4` di bagian paling akhir.
   - Membuat Thumbnail High-CTR Studio V3 (Panel Emerald & Emas di kiri + Kartu Ilustrasi Infografis di kanan).
"""

import os
import re
import math
import json
import time
import asyncio
import textwrap
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

from video_editor import (
    get_video_duration,
    render_final_video,
    generate_youtube_thumbnail,
    _load_bold_font,
    _draw_text_with_3d_stroke,
)
from ai_metadata_generator import validate_youtube_timeline


# Palet warna elegan untuk variasi visual antar-scene Motion Grafis
SCENE_THEMES: Dict[str, Dict[str, Tuple[int, int, int]]] = {
    "emerald_gold": {
        "bg_top": (7, 42, 34),
        "bg_bottom": (4, 22, 18),
        "card_bg": (14, 64, 52),
        "card_border": (255, 204, 0),
        "accent": (255, 210, 30),
        "accent_soft": (255, 242, 185),
        "badge_bg": (255, 204, 0),
        "badge_text": (8, 32, 24),
        "highlight_bg": (18, 86, 68),
    },
    "royal_teal": {
        "bg_top": (8, 45, 58),
        "bg_bottom": (5, 24, 34),
        "card_bg": (14, 68, 86),
        "card_border": (80, 225, 210),
        "accent": (100, 240, 225),
        "accent_soft": (210, 252, 248),
        "badge_bg": (80, 225, 210),
        "badge_text": (6, 30, 38),
        "highlight_bg": (18, 88, 108),
    },
    "midnight_amber": {
        "bg_top": (18, 30, 56),
        "bg_bottom": (8, 15, 32),
        "card_bg": (28, 46, 82),
        "card_border": (255, 190, 40),
        "accent": (255, 200, 55),
        "accent_soft": (255, 238, 190),
        "badge_bg": (255, 190, 40),
        "badge_text": (12, 20, 40),
        "highlight_bg": (38, 62, 106),
    },
    "deep_ocean": {
        "bg_top": (10, 38, 66),
        "bg_bottom": (5, 20, 38),
        "card_bg": (18, 58, 98),
        "card_border": (110, 205, 255),
        "accent": (130, 215, 255),
        "accent_soft": (215, 242, 255),
        "badge_bg": (110, 205, 255),
        "badge_text": (8, 26, 48),
        "highlight_bg": (24, 76, 124),
    },
    "warm_emerald": {
        "bg_top": (14, 48, 38),
        "bg_bottom": (7, 26, 20),
        "card_bg": (22, 74, 58),
        "card_border": (245, 215, 90),
        "accent": (250, 222, 105),
        "accent_soft": (255, 248, 210),
        "badge_bg": (245, 215, 90),
        "badge_text": (10, 34, 26),
        "highlight_bg": (30, 96, 76),
    },
}

# 7 Gaya Visual Sinematik dari Motion Format v2 (Integrasi E:\Motion Course\motion-format)
MOTION_FORMAT_STYLES: Dict[str, str] = {
    "isometrik-dibongkar": "3D isometric cutaway diagram illustration, glowing technical blueprint lines, cross-section layers, clean dark studio lighting, no text",
    "sejarah-3d": "cinematic 3D historical architecture and Islamic civilization scene, warm golden sunbeams, atmospheric mist, epic lighting, no text",
    "tubuh-anime": "vibrant Makoto Shinkai anime style educational illustration, glowing biological and natural particles, twilight sky gradient, no text",
    "dunia-2d": "artistic textured 2D storybook illustration, warm watercolor and classic engraving style, soft paper grain, rich narrative feel, no text",
    "kartun-cel": "bright 2D cel-shaded cartoon educational illustration, bold clean outlines, expressive visual storytelling, vibrant colors, no text",
    "peta-relief": "3D cinematic topographic relief map, glowing route path and location marker, elevated terrain contours, dramatic lighting, no text",
    "promo-produk": "modern 3D spotlight hero educational showcase, floating geometric accents, high-contrast emerald and gold studio lighting, no text",
}


def select_motion_format_style(scene: Dict[str, Any], scene_idx: int, topic_title: str) -> str:
    """Memilih salah satu dari 7 gaya visual Motion Format v2 secara cerdas & bervariasi antar-scene."""
    raw = str(scene.get("motion_style", "")).strip().lower()
    if raw in MOTION_FORMAT_STYLES:
        return raw
    text_blob = f"{topic_title} {scene.get('headline', '')} {scene.get('chapter_title', '')} {scene.get('narration_text', '')}".lower()
    if scene_idx == 9:
        return "promo-produk"
    if any(k in text_blob for k in ["peta", "wilayah", "negeri", "hijrah", "jalur", "perjalanan", "arab", "indonesia", "bumi", "ketinggian", "benua"]):
        cand = "peta-relief"
    elif any(k in text_blob for k in ["mesin", "cara kerja", "gaya", "sayap", "teknologi", "fisika", "struktur", "komponen", "kemudi", "rumus"]):
        cand = "isometrik-dibongkar"
    elif any(k in text_blob for k in ["sejarah", "kisah", "sahabat", "ulama", "nabi", "rasul", "masjid", "peradaban", "abad", "habibie", "ibnu"]):
        cand = "sejarah-3d"
    elif any(k in text_blob for k in ["tubuh", "hati", "otak", "kesehatan", "biologi", "darah", "napas", "jiwa", "tidur", "makanan"]):
        cand = "tubuh-anime"
    elif any(k in text_blob for k in ["anak", "adik", "pelajar", "tips", "adab", "doa", "sehari-hari", "keluarga", "praktik"]):
        cand = "kartun-cel"
    elif any(k in text_blob for k in ["ayat", "surat", "hikmah", "makna", "tafsir", "burung", "alam", "langit"]):
        cand = "dunia-2d"
    else:
        style_keys = list(MOTION_FORMAT_STYLES.keys())
        cand = style_keys[scene_idx % len(style_keys)]
    # Variasikan jika kebetulan sama dengan indeks urutan agar 10 scene selalu dinamis
    style_keys = list(MOTION_FORMAT_STYLES.keys())
    if scene_idx % 2 == 1 and cand == style_keys[(scene_idx - 1) % len(style_keys)]:
        cand = style_keys[(scene_idx + 2) % len(style_keys)]
    return cand


def _load_regular_font(size: int, fallback_font_path: str = "") -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        fallback_font_path,
    ]
    for p in candidates:
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return _load_bold_font(size, fallback_font_path)


def build_fallback_explainer_data(topic_title: str, target_audience: str, category: str = "Islami") -> Dict[str, Any]:
    """
    Cadangan cerdas jika Gemini API mengalami gangguan jaringan, memastikan pembuatan video 3 menit
    tetap berjalan tuntas 100% tanpa pernah gagal.
    """
    clean_topic = topic_title.strip()
    clean_audience = (target_audience or "Keluarga Muslim").strip()

    if "pesawat" in clean_topic.lower() and "terbang" in clean_topic.lower():
        scenes = [
            {
                "scene_number": 1,
                "chapter_title": "Keajaiban Pesawat Besi yang Bisa Terbang",
                "narration_text": (
                    f"Assalamu'alaikum warahmatullahi wabarakatuh. Alhamdulillahi rabbil 'alamin, apa kabar adik-adik dan {clean_audience} "
                    f"yang dirahmati Allah? Pernahkah kalian menatap langit dan bertanya, bagaimana pesawat terbang yang terbuat dari besi "
                    f"seberat ratusan ton bisa melayang tinggi di udara tanpa jatuh? Yuk kita pelajari rahasia sains dan tanda kebesaran Allah bersama channel Islamic K1!"
                ),
                "headline": "BAGAIMANA PESAWAT BISA TERBANG?",
                "bullet_points": [
                    "Pesawat besi ratusan ton melayang tinggi di angkasa",
                    "Perpaduan hukum sains fisika dan ketetapan Allah",
                    "Inspirasi dari cara burung mengepakkan sayapnya",
                ],
                "highlight_box": "Tidakkah mereka memperhatikan burung-burung yang dimudahkan terbang di angkasa bebas? Tidak ada yang menahannya selain Allah. (QS. An-Nahl: 79)",
                "theme": "deep_ocean",
                "icon_type": "plane",
            },
            {
                "scene_number": 2,
                "chapter_title": "Inspirasi dari Burung di Angkasa (QS. Al-Mulk: 19)",
                "narration_text": (
                    "Sejak ratusan tahun lalu, para ilmuwan termasuk ilmuwan Muslim seperti Abbas Ibnu Firnas memperhatikan bagaimana burung terbang di langit. "
                    "Allah Subhanahu wa Ta'ala berfirman dalam Qur'an Surat Al-Mulk ayat sembilan belas tentang burung yang mengembangkan dan melipat sayapnya. "
                    "Dari bentuk sayap burung itulah manusia menemukan ilmu aerodinamika untuk membuat sayap pesawat terbang!"
                ),
                "headline": "INSPIRASI DARI SAYAP BURUNG",
                "bullet_points": [
                    "Mengamati burung yang membentangkan sayap di langit",
                    "Abbas Ibnu Firnas: pelopor percobaan terbang Muslim",
                    "Melahirkan ilmu aerodinamika modern pada sayap pesawat",
                ],
                "highlight_box": "Dan apakah mereka tidak memperhatikan burung-burung yang mengembangkan dan mengatupkan sayapnya di atas mereka? (QS. Al-Mulk: 19)",
                "theme": "emerald_gold",
                "icon_type": "book",
            },
            {
                "scene_number": 3,
                "chapter_title": "Empat Gaya Utama yang Bekerja pada Pesawat",
                "narration_text": (
                    "Adik-adik sekalian, agar sebuah pesawat bisa terbang dengan stabil di udara, ada empat gaya fisika yang bekerja secara bersamaan. "
                    "Pertama adalah gaya dorong atau Thrust ke depan, kedua gaya angkat atau Lift ke atas, "
                    "ketiga gaya berat atau gravitasi ke bawah, dan keempat gaya hambat udara atau Drag ke belakang."
                ),
                "headline": "4 GAYA FISIKA PENERBANGAN",
                "bullet_points": [
                    "1. Gaya Angkat (Lift) yang mengangkat pesawat ke atas",
                    "2. Gaya Dorong (Thrust) dari mesin jet yang super kuat",
                    "3. Mengimbangi Gravitasi (Weight) dan Hambat Udara (Drag)",
                ],
                "highlight_box": "Pesawat bisa naik ke langit ketika Gaya Angkat (Lift) lebih besar daripada Gaya Berat (Gravitasi).",
                "theme": "royal_teal",
                "icon_type": "lightbulb",
            },
            {
                "scene_number": 4,
                "chapter_title": "Rahasia Bentuk Sayap Pesawat (Hukum Bernoulli)",
                "narration_text": (
                    "Lalu bagaimana sayap pesawat yang diam tidak mengepak seperti burung bisa mengangkat badan pesawat? "
                    "Rahasianya ada pada bentuk melengkung sayap yang disebut Airfoil dan Hukum Bernoulli! "
                    "Bagian atas sayap dibuat melengkung sedangkan bagian bawahnya lebih datar, sehingga udara di atas sayap mengalir jauh lebih cepat."
                ),
                "headline": "RAHASIA SAYAP & HUKUM BERNOULLI",
                "bullet_points": [
                    "Bentuk sayap melengkung khusus bernama Airfoil",
                    "Udara di atas sayap bergerak cepat (tekanan rendah)",
                    "Udara di bawah sayap mendorong kuat pesawat ke atas!",
                ],
                "highlight_box": "Perbedaan tekanan udara di bawah dan di atas sayap menghasilkan Gaya Angkat raksasa!",
                "theme": "midnight_amber",
                "icon_type": "plane",
            },
            {
                "scene_number": 5,
                "chapter_title": "Kekuatan Mesin Jet & Baling-Baling (Gaya Dorong)",
                "narration_text": (
                    "Namun sayap tidak akan bisa menghasilkan gaya angkat jika pesawat hanya diam di tempat. "
                    "Di sinilah peran mesin jet atau baling-baling raksasa di bawah sayap pesawat! "
                    "Mesin jet menghisap udara dari depan, memampatkannya, lalu menyemburkannya ke belakang dengan kecepatan tinggi sehingga pesawat melesat maju."
                ),
                "headline": "TENAGA MESIN JET PENDORONG",
                "bullet_points": [
                    "Menghisap udara dan menyemburkan tenaga dorong kuat",
                    "Membuat pesawat berlari hingga 250 km/jam di landasan",
                    "Aliran udara cepat di sayap mulai mengangkat pesawat",
                ],
                "highlight_box": "Kombinasi dorongan mesin jet dan lengkungan sayap membuat pesawat lepas landas dengan mulus.",
                "theme": "warm_emerald",
                "icon_type": "plane",
            },
            {
                "scene_number": 6,
                "chapter_title": "Bagaimana Pilot Mengemudikan Pesawat di Udara?",
                "narration_text": (
                    "Saat sudah berada di atas awan, bagaimana Bapak atau Ibu Pilot membelokkan pesawat ke kanan, ke kiri, naik, atau turun? "
                    "Di ujung sayap dan ekor pesawat terdapat sirip-sirip kecil yang bisa bergerak, yaitu Aileron untuk berbelok, "
                    "Elevator di ekor untuk menanjak atau menurun, serta Rudder untuk menjaga arah pesawat tetap lurus."
                ),
                "headline": "KEMUDI SAYAP & EKOR PESAWAT",
                "bullet_points": [
                    "Aileron di sayap untuk memiringkan dan membelokkan pesawat",
                    "Elevator di ekor untuk mengatur pesawat naik dan turun",
                    "Rudder tegak di ekor menjaga keseimbangan arah terbang",
                ],
                "highlight_box": "Teknologi kemudi canggih membantu pilot menjaga keselamatan ratusan penumpang di udara.",
                "theme": "deep_ocean",
                "icon_type": "shield",
            },
            {
                "scene_number": 7,
                "chapter_title": "Kenapa Pesawat Terbang Tinggi di Atas Awan?",
                "narration_text": (
                    "Adik-adik mungkin sering melihat pesawat terbang sangat tinggi hingga menembus di atas awan, sekitar sepuluh kilometer dari permukaan bumi. "
                    "Mengapa demikian? Karena di ketinggian tersebut udara lebih tipis sehingga hambatan angin berkurang, "
                    "pesawat lebih hemat bahan bakar, dan terhindar dari cuaca buruk atau awan hujan di bawahnya."
                ),
                "headline": "TERBANG DI ATAS AWAN (10 KM)",
                "bullet_points": [
                    "Udara di ketinggian 10 km lebih tenang dan stabil",
                    "Hambatan udara kecil sehingga hemat bahan bakar",
                    "Kabin pesawat diberi tekanan udara agar penumpang nyaman",
                ],
                "highlight_box": "Di balik kecanggihan kabin pesawat, ada ilmu fisika dan rekayasa teknologi yang luar biasa.",
                "theme": "emerald_gold",
                "icon_type": "lightbulb",
            },
            {
                "scene_number": 8,
                "chapter_title": "Tokoh Kebanggaan Indonesia: B.J. Habibie",
                "narration_text": (
                    "Tahukah adik-adik bahwa bangsa Indonesia memiliki ilmuwan pesawat terbang kelas dunia yang sangat saleh dan jenius? "
                    "Beliau adalah Bapak Bacharuddin Jusuf Habibie, Presiden ketiga Republik Indonesia yang dijuluki Mr. Crack! "
                    "Beliau menemukan rumus ketahanan keretakan sayap pesawat yang dipakai oleh seluruh maskapai penerbangan di dunia hingga hari ini."
                ),
                "headline": "TELADAN ILMUWAN: B.J. HABIBIE",
                "bullet_points": [
                    "Penemu teori Faktor Habibie untuk keamanan sayap pesawat",
                    "Perancang pesawat karya anak bangsa N-250 Gatotkaca",
                    "Memadukan kecerdasan sains dengan iman dan takwa",
                ],
                "highlight_box": "Jadilah anak Muslim yang unggul dalam iman dan takwa (IMTAK) serta ilmu pengetahuan dan teknologi (IPTEK).",
                "theme": "royal_teal",
                "icon_type": "heart",
            },
            {
                "scene_number": 9,
                "chapter_title": "Adab & Doa Naik Kendaraan Sesuai Sunnah",
                "narration_text": (
                    "Sehebat apa pun mesin pesawat terbang, keselamatan kita tetap berada dalam penjagaan Allah Subhanahu wa Ta'ala. "
                    "Oleh karena itu, Rasulullah shallallahu 'alaihi wa sallam mengajarkan kita untuk selalu membaca doa naik kendaraan: "
                    "Subhanalladzi sakhkhara lana hadza wama kunna lahu muqrinin, wa inna ila rabbina lamunqalibun."
                ),
                "headline": "ADAB & DOA NAIK PESAWAT",
                "bullet_points": [
                    "Membaca Bismillah dan doa naik kendaraan (QS. Az-Zukhruf: 13)",
                    "Bersyukur atas nikmat ilmu yang memudahkan perjalanan",
                    "Menjaga adab, ketertiban, dan dzikir selama di perjalanan",
                ],
                "highlight_box": "Maha Suci Allah yang telah menundukkan semua ini bagi kami padahal sebelumnya kami tidak mampu menguasainya. (QS. Az-Zukhruf: 13)",
                "theme": "midnight_amber",
                "icon_type": "mosque",
            },
            {
                "scene_number": 10,
                "chapter_title": "Kesimpulan, Ajakan Belajar Sains & Penutup",
                "narration_text": (
                    "Nah adik-adik, sekarang kita sudah tahu bahwa pesawat bisa terbang berkat bentuk sayap Airfoil, gaya angkat Bernoulli, "
                    "dorongan mesin jet, serta hukum alam ciptaan Allah! Teruslah rajin belajar sains dan Al-Qur'an agar kelak kalian menjadi ilmuwan Muslim kebanggaan umat. "
                    "Jangan lupa klik tombol Subscribe, Like, dan bagikan video channel Islamic K1 ini ya. Wassalamu'alaikum warahmatullahi wabarakatuh."
                ),
                "headline": "SUBSCRIBE CHANNEL ISLAMIC K1",
                "bullet_points": [
                    "Klik SUBSCRIBE untuk video sains & edukasi Islami terbaru",
                    "Tekan LIKE dan bagikan ilmu bermanfaat ini ke teman-teman",
                    "Rajin belajar sains dan Al-Qur'an sejak usia dini!",
                ],
                "highlight_box": "Mari dukung channel edukasi keluarga Muslim Islamic K1 (@islamick1832)!",
                "theme": "emerald_gold",
                "icon_type": "plane",
            },
        ]
        return {
            "title": "Bagaimana Pesawat Bisa Terbang? ✈️ Rahasia Sains & Keajaiban Ciptaan Allah untuk Anak",
            "thumbnail_hook": "BAGAIMANA PESAWAT BISA TERBANG?",
            "thumbnail_badge": f"SAINS & IMAN • {clean_audience.upper()[:16]}",
            "category": "Islami & Sains Anak",
            "voice_gender": "male",
            "description_paragraphs": [
                (
                    "Assalamu'alaikum Warahmatullahi Wabarakatuh.\n"
                    "Pernahkah adik-adik dan sahabat keluarga Muslim bertanya, bagaimana pesawat terbang yang terbuat dari logam berat bisa melayang tinggi di atas awan? "
                    "Dalam video animasi Remotion 3 menit dari channel Islamic K1 ini, kita mengupas rahasia sains aerodinamika secara seru dan mudah dipahami untuk anak!"
                ),
                (
                    "Kita akan belajar bersama tentang 4 gaya penerbangan (Gaya Angkat/Lift, Gaya Dorong/Thrust, Gravitasi, dan Hambatan Udara), "
                    "rahasia bentuk sayap Airfoil (Hukum Bernoulli), teladan ilmuwan dirgantara Muslim B.J. Habibie, hingga renungan ayat Al-Qur'an (QS. An-Nahl: 79 & QS. Al-Mulk: 19) "
                    "serta doa naik kendaraan sesuai sunnah Rasulullah SAW."
                ),
                (
                    "Semoga video edukasi sains dan iman ini menambah rasa syukur serta semangat belajar adik-adik semua. "
                    "Jangan lupa klik tombol Subscribe, Like, dan bagikan video channel Islamic K1 ini kepada keluarga dan sahabat lainnya.\n"
                    "Wassalamu'alaikum Warahmatullahi Wabarakatuh."
                ),
            ],
            "hashtags": [
                "#IslamicK1",
                "#BagaimanaPesawatBisaTerbang",
                "#SainsAnakMuslim",
                "#EdukasiAnakIslami",
                "#RemotionAnimation",
                "#KeluargaMuslim",
            ],
            "tags": [
                "Islamic K1",
                "Bagaimana pesawat bisa terbang",
                "Sains untuk anak Muslim",
                "Cara kerja pesawat terbang",
                "Hukum Bernoulli anak",
                "Edukasi Islami Anak",
                "Animasi Remotion Edukasi",
            ],
            "playlist_name": "Explainer Islami & Edukasi Keluarga Muslim",
            "recommended_publish_slot": "SIANG",
            "scenes": scenes,
            "localizations": {
                "en": {
                    "title": "How Do Airplanes Fly? ✈️ Fun Science & Islamic Wisdom for Kids | Islamic K1",
                    "description": "Discover the science of aerodynamics, Bernoulli's principle, jet engines, and Quranic reflections (Surah An-Nahl: 79 & Al-Mulk: 19) on how airplanes fly in this 3-minute animated explainer for children.",
                },
                "ar": {
                    "title": "كيف تطير الطائرة؟ ✈️ أسرار العلوم وآيات الله في الكون للأطفال | Islamic K1",
                    "description": "تعرف على كيفية طيران الطائرات، وقوة الرفع والدفع، والتأمل في آيات الله في سورة النحل وسورة الملك في هذا الفيديو التعليمي الممتع للأطفال.",
                },
                "ms": {
                    "title": "Bagaimana Kapal Terbang Boleh Terbang? ✈️ Sains & Hikmah Islam untuk Kanak-Kanak",
                    "description": "Pelajari rahsia aerodinamik, sayap pesawat, enjin jet, dan tadabbur Al-Quran tentang bagaimana kapal terbang boleh terbang di udara.",
                },
            },
        }

    scenes = [
        {
            "scene_number": 1,
            "chapter_title": f"Pembukaan & Pengantar: {clean_topic[:35]}",
            "narration_text": (
                f"Assalamu'alaikum warahmatullahi wabarakatuh. Alhamdulillahi rabbil 'alamin, "
                f"apa kabar sahabat dan {clean_audience} yang dirahmati Allah? Selamat datang kembali di channel Islamic K1. "
                f"Pada video kali ini, kita akan membahas secara lengkap dan mudah dipahami tentang {clean_topic}. "
                f"Mari kita simak bersama-sama hingga selesai agar kita mendapatkan ilmu yang bermanfaat."
            ),
            "headline": clean_topic.upper()[:42],
            "bullet_points": [
                f"Pengantar khusus untuk {clean_audience}",
                f"Mengapa {clean_topic} sangat penting dipahami",
                "Panduan ringkas, jelas, dan mudah diamalkan",
            ],
            "highlight_box": "Menuntut ilmu yang bermanfaat adalah cahaya penuntun kebaikan di dunia dan akhirat.",
            "theme": "emerald_gold",
            "icon_type": "mosque",
        },
        {
            "scene_number": 2,
            "chapter_title": f"Pengertian & Makna Utama {clean_topic[:28]}",
            "narration_text": (
                f"Langkah pertama agar kita benar-benar paham adalah mengenal makna dasar dari {clean_topic}. "
                f"Bagi {clean_audience}, memahami konsep dasar ini sangatlah penting agar kita tidak salah langkah "
                f"dalam mempraktikkannya di kehidupan sehari-hari. Ketika pondasi pemahamannya kuat, maka manfaatnya akan jauh lebih terasa."
            ),
            "headline": "MAKNA & KONSEP DASAR",
            "bullet_points": [
                "Memahami definisi dan hakikat utama secara utuh",
                "Mengetahui tujuan baik di balik pembahasan ini",
                "Membangun pondasi pemahaman yang lurus dan benar",
            ],
            "highlight_box": f"Pemahaman yang benar adalah kunci utama keberhasilan bagi {clean_audience}.",
            "theme": "royal_teal",
            "icon_type": "book",
        },
        {
            "scene_number": 3,
            "chapter_title": "Landasan Ilmu & Nilai Kebaikan",
            "narration_text": (
                f"Dalam ajaran Islam maupun ilmu pengetahuan yang bermanfaat, segala kebaikan selalu memiliki landasan yang jelas. "
                f"Begitu pula dengan {clean_topic}. Nilai-nilai luhur yang terkandung di dalamnya mengajarkan kita untuk menjadi pribadi "
                f"yang lebih tertib, bijaksana, dan penuh tanggung jawab terhadap diri sendiri maupun orang-orang di sekitar kita."
            ),
            "headline": "LANDASAN & NILAI KEBAIKAN",
            "bullet_points": [
                "Berlandaskan nilai-nilai kebenaran dan akhlak mulia",
                "Mendidik kedisiplinan serta tanggung jawab diri",
                "Membawa manfaat nyata bagi lingkungan sekitar",
            ],
            "highlight_box": "Sebaik-baik manusia adalah yang paling bermanfaat bagi manusia lainnya. (HR. Ahmad)",
            "theme": "midnight_amber",
            "icon_type": "star",
        },
        {
            "scene_number": 4,
            "chapter_title": "Mengapa Hal Ini Penting Bagi Kita?",
            "narration_text": (
                f"Mungkin kita bertanya, mengapa {clean_topic} begitu penting untuk diperhatikan oleh {clean_audience}? "
                f"Jawabannya karena hal ini berkaitan langsung dengan kualitas hidup, ketenangan hati, serta keberhasilan kita setiap hari. "
                f"Banyak masalah bisa dihindari ketika kita menguasai ilmu ini sejak dini."
            ),
            "headline": "MENGAPA SANGAT PENTING?",
            "bullet_points": [
                "Meningkatkan kualitas diri dan ketenangan hati",
                "Mencegah kekeliruan dalam mengambil keputusan harian",
                "Membentuk kebiasaan positif yang berkelanjutan",
            ],
            "highlight_box": "Ilmu yang diamalkan setiap hari akan melahirkan perubahan besar dalam hidup.",
            "theme": "deep_ocean",
            "icon_type": "lightbulb",
        },
        {
            "scene_number": 5,
            "chapter_title": "Poin Penting Pertama dalam Praktik",
            "narration_text": (
                f"Sekarang mari kita bahas langkah praktis yang pertama dalam {clean_topic}. "
                f"Mulailah dengan niat yang tulus karena Allah Subhanahu wa Ta'ala dan tekad yang kuat untuk memperbaiki diri. "
                f"Dengan niat yang lurus, setiap usaha belajar dan kebaikan yang kita lakukan akan bernilai ibadah dan pahala."
            ),
            "headline": "LANGKAH 1: NIAT & KESADARAN",
            "bullet_points": [
                "Meluruskan niat semata-mata mengharap ridha Allah",
                "Memulai dari hal kecil yang bisa dilakukan hari ini",
                "Menjaga semangat belajar bersama keluarga dan sahabat",
            ],
            "highlight_box": "Sesungguhnya setiap amal perbuatan itu tergantung pada niatnya. (HR. Bukhari & Muslim)",
            "theme": "warm_emerald",
            "icon_type": "heart",
        },
        {
            "scene_number": 6,
            "chapter_title": "Poin Penting Kedua & Penerapan Nyata",
            "narration_text": (
                f"Langkah praktis yang kedua adalah menerapkan {clean_topic} secara bertahap namun konsisten. "
                f"Bagi {clean_audience}, konsistensi atau istiqamah jauh lebih berharga daripada melakukan sesuatu secara berlebihan "
                f"namun cepat berhenti. Buatlah jadwal atau kebiasaan harian yang ringan tetapi rutin dilakukan."
            ),
            "headline": "LANGKAH 2: KONSISTEN & ISTIQAMAH",
            "bullet_points": [
                "Menerapkan ilmu secara bertahap dan terukur",
                "Menjaga keistiqamahan dalam rutinitas sehari-hari",
                "Mengevaluasi perkembangan diri secara berkala",
            ],
            "highlight_box": "Amalan yang paling dicintai Allah adalah yang dilakukan secara rutin meskipun sedikit.",
            "theme": "emerald_gold",
            "icon_type": "compass",
        },
        {
            "scene_number": 7,
            "chapter_title": "Tantangan yang Sering Dihadapi & Solusinya",
            "narration_text": (
                f"Tentu saja dalam menerapkan {clean_topic}, terkadang kita menghadapi rasa malas, lupa, atau kurang fokus. "
                f"Solusinya bagi {clean_audience} adalah menciptakan lingkungan yang saling mengingatkan dalam kebaikan, "
                f"serta selalu memohon pertolongan dan kemudahan kepada Allah dalam setiap aktivitas kita."
            ),
            "headline": "MENGATASI TANTANGAN HARIAN",
            "bullet_points": [
                "Kenali penghambat utama seperti menunda-nunda waktu",
                "Bangun lingkungan positif yang saling mendukung",
                "Perbanyak doa memohon keteguhan dan kemudahan",
            ],
            "highlight_box": "Bersama kesulitan pasti ada kemudahan. Jangan pernah menyerah dalam kebaikan!",
            "theme": "royal_teal",
            "icon_type": "shield",
        },
        {
            "scene_number": 8,
            "chapter_title": "Hikmah & Manfaat Jangka Panjang",
            "narration_text": (
                f"Ketika {clean_topic} sudah menjadi bagian dari karakter dan kebiasaan {clean_audience}, "
                f"maka kita akan merasakan hikmah dan manfaat yang luar biasa. Hati menjadi lebih tenteram, "
                f"hubungan dengan sesama semakin harmonis, dan hidup kita menjadi jauh lebih produktif serta penuh berkah."
            ),
            "headline": "HIKMAH & KEBERKAHAN HIDUP",
            "bullet_points": [
                "Hati lebih tenang, damai, dan penuh rasa syukur",
                "Hubungan keluarga dan sosial menjadi lebih harmonis",
                "Mendatangkan keberkahan ilmu dan waktu setiap hari",
            ],
            "highlight_box": "Kebaikan yang ditanam hari ini adalah keberkahan yang akan kita tuai di masa depan.",
            "theme": "midnight_amber",
            "icon_type": "sparkle",
        },
        {
            "scene_number": 9,
            "chapter_title": "Tips Ringkas Agar Mudah Diingat",
            "narration_text": (
                f"Sebagai rangkuman praktis untuk {clean_audience}, ingatlah tiga kunci utama dari {clean_topic}: "
                f"pertama pahami ilmunya dengan benar, kedua amalkan mulai dari hal yang paling sederhana hari ini, "
                f"dan ketiga ajarkan atau bagikan kebaikan ini kepada orang-orang terdekat di sekitar kita."
            ),
            "headline": "3 KUNCI UTAMA KEBERHASILAN",
            "bullet_points": [
                "1. Pahami ilmunya dengan jelas dan menyeluruh",
                "2. Praktikkan langsung dalam aktivitas harian",
                "3. Bagikan manfaatnya kepada keluarga dan teman",
            ],
            "highlight_box": "Ilmu yang dibagikan dan diamalkan akan terus mengalir pahalanya tanpa terputus.",
            "theme": "deep_ocean",
            "icon_type": "check",
        },
        {
            "scene_number": 10,
            "chapter_title": "Kesimpulan, Ajakan Subscribe & Penutup",
            "narration_text": (
                f"Demikianlah pembahasan lengkap kita mengenai {clean_topic} untuk {clean_audience}. "
                f"Semoga apa yang kita pelajari hari ini membawa manfaat dan keberkahan bagi kita semua. "
                f"Jangan lupa klik tombol Subscribe, Like, dan bagikan video channel Islamic K1 ini kepada keluarga serta sahabat lainnya "
                f"agar semakin banyak yang mendapatkan manfaatnya. Terima kasih telah menyimak, semoga Allah senantiasa memberkahi kita. "
                f"Wassalamu'alaikum warahmatullahi wabarakatuh."
            ),
            "headline": "SUBSCRIBE CHANNEL ISLAMIC K1",
            "bullet_points": [
                "Klik SUBSCRIBE untuk video edukasi & kajian terbaru",
                "Tekan LIKE & aktifkan lonceng notifikasi",
                "BAGIKAN video ini agar menjadi amal jariyah bersama",
            ],
            "highlight_box": "Mari dukung dakwah & edukasi kebaikan di channel Islamic K1 (@islamick1832)!",
            "theme": "emerald_gold",
            "icon_type": "mosque",
        },
    ]

    paragraphs = [
        (
            f"Assalamu'alaikum Warahmatullahi Wabarakatuh.\n"
            f"Selamat datang di channel Islamic K1, sahabat belajar dan inspirasi kebaikan untuk {clean_audience} serta seluruh keluarga Muslim. "
            f"Di dalam video explainer motion grafis berdurasi 3 menit ini, kita membahas secara tuntas, ringkas, dan menarik mengenai "
            f"{clean_topic} yang dirancang khusus agar mudah dipahami oleh {clean_audience}."
        ),
        (
            f"Melalui pembahasan {clean_topic} ini, kita mempelajari konsep dasar, landasan kebaikan, langkah-langkah penerapan praktis, "
            f"hingga hikmah dan manfaat besar yang dapat langsung dipraktikkan dalam kehidupan sehari-hari. "
            f"Setiap bagian disajikan secara visual dan terstruktur agar belajar menjadi jauh lebih menyenangkan dan bermakna."
        ),
        (
            f"Semoga ilmu yang kita pelajari bersama hari ini menjadi amal jariyah dan mendatangkan keberkahan bagi kita semua di dunia maupun di akhirat. "
            f"Jangan lupa untuk klik tombol Subscribe, Like, dan bagikan video channel Islamic K1 ini kepada keluarga, teman, dan sahabat lainnya.\n"
            f"Wassalamu'alaikum Warahmatullahi Wabarakatuh."
        ),
    ]

    return {
        "title": f"{clean_topic} | Penjelasan Lengkap untuk {clean_audience} | Islamic K1"[:95],
        "thumbnail_hook": clean_topic.upper()[:40],
        "thumbnail_badge": f"ISLAMIC K1 • {clean_audience.upper()[:18]}",
        "category": category,
        "voice_gender": "male",
        "description_paragraphs": paragraphs,
        "hashtags": [
            "#IslamicK1",
            "#KeluargaMuslim",
            "#EdukasiIslami",
            "#BelajarIslam",
            "#MotionGrafisIslami",
            "#IlmuBermanfaat",
        ],
        "tags": [
            "Islamic K1",
            clean_topic[:45],
            clean_audience[:35],
            "Video Explainer Islami",
            "Motion Grafis Dakwah",
            "Edukasi Keluarga Muslim",
            "Kajian Singkat 3 Menit",
        ],
        "playlist_name": "Explainer Islami & Edukasi Keluarga Muslim",
        "recommended_publish_slot": "MALAM",
        "scenes": scenes,
        "localizations": {},
    }


def generate_explainer_storyboard_and_metadata(
    topic_title: str,
    target_audience: str,
    gemini_api_key: str,
    category_hint: str = "",
) -> Dict[str, Any]:
    """
    Menggunakan Gemini API untuk menghasilkan:
    1. Script Voiceover ~3 menit (400-460 kata yang terbagi rata ke dalam 10 Scene Motion Grafis).
    2. Storyboard visual lengkap per scene (Headline, 3 Bullet Points progresif, Highlight Dalil/Fakta, Tema & Ikon).
    3. Metadata YouTube lengkap (Judul, Deskripsi 3 Paragraf dengan Salam Pembuka & Penutup, Hashtag, Tags, Playlist, & 10 Bahasa).
    """
    clean_topic = topic_title.strip()
    clean_audience = (target_audience or "Keluarga & Pelajar Muslim").strip()

    prompt = f"""
Anda adalah sutradara Motion Graphics Explainer, penulis naskah edukasi Islami & umum, sekaligus pakar SEO YouTube untuk channel **Islamic K1** (https://www.youtube.com/@islamick1832).

Pengguna baru saja mengisi Google Form dengan data berikut:
- **Judul / Topik Video**: "{clean_topic}"
- **Target Audience**: "{clean_audience}"
- **Kategori Tambahan**: "{category_hint or 'Deteksi otomatis Islami / Umum'}"

TUGAS UTAMA ANDA:
Buat paket lengkap **Video Motion Grafis Explainer berdurasi sekitar 3 MENIT (~170–190 detik)** yang terdiri dari **TEPAT 10 SCENE (Babak)** dalam bahasa Indonesia yang sangat mengalir, hangat, jelas, dan disesuaikan dengan tingkat pemahaman **{clean_audience}**.

ATURAN WAJIB NASKAH & VIDEO (JANGAN DILANGGAR):
1. **Durasi 3 Menit (~400 hingga 460 kata total)**:
   - Setiap scene (`scenes` 1 s/d 10) WAJIB memiliki `narration_text` sepanjang **38 hingga 46 kata** (3-4 kalimat lengkap yang natural saat dibacakan narator), sehingga total 10 scene menghasilkan durasi bicara sekitar 2 menit 50 detik + jeda & video outro Subscribe menjadi ~3 menit!
2. **Pembuka & Penutup Wajib**:
   - **Scene 1 (`scene_number`: 1)**: `narration_text` WAJIB dimulai dengan ucapan salam lengkap: *"Assalamu'alaikum warahmatullahi wabarakatuh..."*, dilanjutkan kalimat syukur singkat, menyapa **{clean_audience}** secara hangat, lalu memperkenalkan topik **"{clean_topic}"** dengan pembuka yang memikat.
   - **Scene 10 (`scene_number`: 10)**: `narration_text` WAJIB berisi kesimpulan singkat yang menyentuh hati, **ajakan jelas untuk klik tombol Subscribe, Like, dan membagikan video channel Islamic K1**, doa kebaikan, dan WAJIB ditutup dengan salam lengkap: *"Wassalamu'alaikum warahmatullahi wabarakatuh."*
3. **Isi Materi Berkualitas Tinggi (Islami maupun Umum)**:
   - Jika topiknya **Islami**, sertakan dalil Al-Qur'an atau Hadits yang **shahih** beserta nama surat/ayat atau perawinya di dalam narasi dan di `highlight_box`.
   - Jika topiknya **Umum** (sains, psikologi, tips belajar, kesehatan, sejarah, keuangan, dll.), jelaskan secara ilmiah, praktis, dan tetap selaras dengan adab serta nilai kebaikan keluarga Muslim.
4. **Struktur Visual Setiap Scene (Motion Graphics + Gambar Ilustrasi AI per Scene)**:
   - `scene_number`: 1 sampai 10.
   - `chapter_title`: Judul babak untuk fitur Chapters/Timeline YouTube (3-7 kata).
   - `narration_text`: Naskah voiceover bersih (tanpa simbol markdown `*` atau `#`, tulis angka/singkatan agar mudah dibaca oleh Text-to-Speech, misal tulis "Subhanahu wa Ta'ala" bukan "SWT", tulis "Shallallahu 'alaihi wa sallam" bukan "SAW").
   - `headline`: Judul besar di layar (maksimal 5 kata, huruf kapital tegas).
   - `bullet_points`: Tepat **3 poin ringkas** (masing-masing 5–9 kata) yang akan dimunculkan satu per satu secara animasi (*kinetic reveal*) seiring narator berbicara.
   - `highlight_box`: 1 kalimat kutipan dalil Al-Qur'an/Hadits, fakta kunci, atau hikmah utama (10–18 kata) untuk ditampilkan di kotak emas bagian bawah layar.
   - `image_prompt`: Deskripsi visual spesifik dalam **Bahasa Inggris** (15–25 kata) yang menggambarkan persis apa yang sedang dibahas pada scene tersebut untuk digenerate menjadi gambar ilustrasi 3D edukatif (contoh: `"3D Pixar style educational illustration of an airplane wing showing blue airflow arrows lifting the aircraft in bright sky, no text"`).
   - `motion_style`: Pilih salah satu dari **7 Gaya Visual Motion Format v2** secara bervariasi antar-scene sesuai isi adegan: `"isometrik-dibongkar"` (cara kerja/sains/teknologi), `"sejarah-3d"` (sejarah Islam/ulama/masjid/kisah), `"tubuh-anime"` (kesehatan/biologi/jiwa/alam), `"dunia-2d"` (narasi kitab/hikmah/lukisan), `"kartun-cel"` (edukasi anak/adab/praktik), `"peta-relief"` (geografi/jalur/wilayah), `"promo-produk"` (kesimpulan/spotlight).
   - `pointer_label`: Label penunjuk objek pendek (2–4 kata kapital, misal `"GAYA ANGKAT AIRFOIL"`, `"JEJAK PERADABAN"`, `"INTI HIKMAH AYAT"`) untuk fitur pointer titik + garis penunjuk di atas ilustrasi.
   - `theme`: Pilih salah satu secara bervariasi antar-scene: `"emerald_gold"`, `"royal_teal"`, `"midnight_amber"`, `"deep_ocean"`, `"warm_emerald"`.
   - `icon_type`: Pilih salah satu ikon yang paling cocok dengan isi scene: `"mosque"`, `"book"`, `"star"`, `"heart"`, `"lightbulb"`, `"shield"`, `"compass"`, `"check"`, `"sparkle"`, `"plane"`.
5. **Metadata YouTube Lengkap**:
   - `title`: Judul YouTube yang sangat menarik bagi **{clean_audience}** (maksimal 85 karakter, mengandung topik utama & kata kunci pencari).
   - `thumbnail_hook`: 3-5 kata ekstra tegas untuk gambar Thumbnail (contoh: `"RAHASIA & KEUTAMAAN SEDEKAH SUBUH"`).
   - `thumbnail_badge`: Label atas Thumbnail (contoh: `"EXPLAINER ISLAMI • {clean_audience.upper()[:16]}"`).
   - `voice_gender`: `"male"` atau `"female"` (pilih `"female"` jika audience anak-anak/balita/ibu, atau `"male"` untuk umum/remaja/keluarga).
   - `description_paragraphs`: Minimal 3 paragraf deskripsi YouTube:
     - Paragraf 1 WAJIB diawali *"Assalamu'alaikum Warahmatullahi Wabarakatuh."*
     - Paragraf 2 mengulas isi video dan manfaatnya bagi **{clean_audience}**.
     - Paragraf 3 mengajak mengamalkan ilmu, mengajak Subscribe channel Islamic K1, dan WAJIB diakhiri *"Wassalamu'alaikum Warahmatullahi Wabarakatuh."*
   - `hashtags`: 6 hingga 8 hashtag relevan (diawali `#`, wajib ada `#IslamicK1`).
   - `tags`: 10 hingga 14 kata kunci SEO YouTube.
   - `playlist_name`: Nama Playlist YouTube yang paling tepat (contoh: `"Explainer Islami & Edukasi Keluarga Muslim"`, atau jika menyebutkan kelas PAI seperti Kelas 1-12 tulis nama playlist kelasnya).
   - `recommended_publish_slot`: `"SUBUH"` (05:00 WIB), `"SIANG"` (12:00 WIB), atau `"MALAM"` (19:00 WIB).
   - `localizations`: Terjemahan `title` dan `description` ke 9 bahasa dunia (`"en"`, `"ar"`, `"ms"`, `"tr"`, `"ur"`, `"fr"`, `"de"`, `"es"`, `"ru"`).

Kembalikan HANYA JSON murni yang valid dengan struktur berikut:
{{
  "title": "...",
  "thumbnail_hook": "...",
  "thumbnail_badge": "...",
  "category": "Islami",
  "voice_gender": "male",
  "description_paragraphs": ["Paragraf 1...", "Paragraf 2...", "Paragraf 3..."],
  "hashtags": ["#IslamicK1", "..."],
  "tags": ["Islamic K1", "..."],
  "playlist_name": "Explainer Islami & Edukasi Keluarga Muslim",
  "recommended_publish_slot": "MALAM",
  "scenes": [
    {{
      "scene_number": 1,
      "chapter_title": "...",
      "narration_text": "...",
      "headline": "...",
      "bullet_points": ["Poin 1...", "Poin 2...", "Poin 3..."],
      "highlight_box": "...",
      "image_prompt": "3D Pixar style educational illustration of ..., warm lighting, no text",
      "theme": "emerald_gold",
      "icon_type": "mosque"
    }}
  ],
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

    data = None
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=gemini_api_key,
            http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)),
        )
        candidate_models = [
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
        ]

        for model_name in candidate_models:
            try:
                print(f"[AI EXPLAINER] Menyusun Script 3 Menit & Storyboard 10 Scene dengan {model_name}...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.35,
                    ),
                )
                raw_text = (response.text or "").strip()
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)
                parsed = json.loads(raw_text)
                if isinstance(parsed.get("scenes"), list) and len(parsed["scenes"]) >= 6:
                    data = parsed
                    print(f"[AI EXPLAINER] Berhasil membuat {len(data['scenes'])} scene dengan {model_name}!")
                    break
            except Exception as e:
                print(f"[PERINGATAN] Model {model_name} melewati batas/gangguan ({str(e)[:110]}), mencoba model cadangan...")
                time.sleep(1)
    except Exception as sdk_err:
        print(f"[PERINGATAN] Gagal menginisialisasi SDK Gemini ({sdk_err}), beralih ke generator AI Cloud gratis...")

    # Cadangan AI LLM 100% Gratis (Pollinations OpenAI JSON Endpoint) jika kuota/server Gemini sedang sibuk (503/429)
    if data is None:
        for poll_attempt in range(2):
            try:
                import urllib.request

                print(f"[AI EXPLAINER] Menyusun Script 10 Scene spesifik topik via Free AI Cloud (percobaan #{poll_attempt + 1})...")
                poll_payload = {
                    "model": "openai",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert Indonesian Islamic & Science Motion Graphics scriptwriter. Always respond with valid, pure JSON matching the requested schema.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.35,
                }
                req = urllib.request.Request(
                    "https://text.pollinations.ai/openai",
                    data=json.dumps(poll_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
                )
                resp_raw = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
                resp_obj = json.loads(resp_raw)
                content_str = (
                    resp_obj.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                content_str = re.sub(r"^```(?:json)?\s*", "", content_str)
                content_str = re.sub(r"\s*```$", "", content_str)
                parsed_poll = json.loads(content_str)
                if isinstance(parsed_poll.get("scenes"), list) and len(parsed_poll["scenes"]) >= 6:
                    data = parsed_poll
                    print(f"[AI EXPLAINER] Berhasil menyusun {len(data['scenes'])} scene spesifik topik via Free AI Cloud!")
                    break
            except Exception as poll_err:
                print(f"[PERINGATAN] Free AI Cloud percobaan #{poll_attempt + 1} gagal ({str(poll_err)[:110]})...")
                time.sleep(2)

    if data is None:
        print("[INFO] Menggunakan generator cadangan cerdas untuk menyusun 10 Scene Explainer...")
        data = build_fallback_explainer_data(clean_topic, clean_audience, category_hint or "Islami")

    # Pastikan selalu ada Salam di Scene 1 & Ajakan Subscribe + Salam di Scene Terakhir
    scenes = data.get("scenes", [])
    if scenes:
        first_narr = str(scenes[0].get("narration_text", "")).strip()
        if "assalamu" not in first_narr.lower():
            scenes[0]["narration_text"] = (
                f"Assalamu'alaikum warahmatullahi wabarakatuh. Sahabat dan {clean_audience} yang dirahmati Allah, "
                + first_narr
            )
        last_narr = str(scenes[-1].get("narration_text", "")).strip()
        if "subscribe" not in last_narr.lower():
            last_narr = (
                last_narr.rstrip(".")
                + ". Jangan lupa klik tombol Subscribe, Like, dan bagikan video channel Islamic K1 ini agar semakin banyak yang mendapatkan manfaatnya."
            )
        if "wassalamu" not in last_narr.lower():
            last_narr = last_narr.rstrip(".") + ". Wassalamu'alaikum warahmatullahi wabarakatuh."
        scenes[-1]["narration_text"] = last_narr

    return data


async def _edge_tts_save(text: str, voice: str, rate: str, out_path: str) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    await communicate.save(out_path)


def apply_islamic_phonetic_pronunciation(text: str) -> str:
    """
    Mengubah ejaan khusus untuk input mesin suara (TTS) agar pelafalan Lafaz Jalalah (Allah -> Alloh)
    dan seluruh turunannya (Rasulullah -> Rosululloh, warahmatullahi -> warohmatullohi, dll.)
    terdengar fasih dan tebal (tafkhim), TANPA mengubah teks visual yang tampil di layar!
    """
    phonetic_rules = [
        # Singkatan umum Islami -> dibaca penuh & fasih
        (r"\bSWT\b", "Subhanahu wa Ta'ala"),
        (r"\bSAW\b", "shollallohu 'alaihi wa sallam"),
        (r"\bRA\b", "rodhiyallohu 'anhu"),
        (r"\bQS\.\s*", "Qur'an Surat "),
        (r"\bHR\.\s*", "Hadits Riwayat "),
        # Salam, Basmalah, & Kalimat Thayyibah
        (r"(?i)\bwarahmatullahi\b", "warohmatullohi"),
        (r"(?i)\bwarahmatullah\b", "warohmatulloh"),
        (r"(?i)\bwabarakatuh\b", "wabarokatuh"),
        (r"(?i)\bbismillahirrahmanirrahim\b", "bismillahirrohmanirrohim"),
        (r"(?i)\bar-rahman\b", "ar-rohman"),
        (r"(?i)\bar-rahim\b", "ar-rohim"),
        # Rasulullah & Shalawat
        (r"(?i)\brasulullah\b", "Rosululloh"),
        (r"(?i)\brasul-nya\b", "Rosul-Nya"),
        (r"(?i)\brasul\b", "Rosul"),
        (r"(?i)\bshallallahu\b", "shollallohu"),
        (r"(?i)\bsallallahu\b", "shollallohu"),
        (r"(?i)\bshalawat\b", "sholawat"),
        # Sahabat & Ulama
        (r"(?i)\bradhiyallahu\b", "rodhiyallohu"),
        (r"(?i)\brahimahullahu\b", "rohimahullohu"),
        (r"(?i)\brahimahullah\b", "rohimahulloh"),
        # Turunan Lafaz Allah (Tafkhim: huruf sebelum Lafaz Allah berharakat fathah/dhammah dibaca "lloh")
        (r"(?i)\bsubhanallahi\b", "subhanallohi"),
        (r"(?i)\bsubhanallah\b", "subhanalloh"),
        (r"(?i)\binsya\s*allah\b", "insya Alloh"),
        (r"(?i)\bmasya\s*allah\b", "masya Alloh"),
        (r"(?i)\bastaghfirullahal\s*'azhim\b", "astaghfirullohal 'azhim"),
        (r"(?i)\bastaghfirullah\b", "astaghfirulloh"),
        (r"(?i)\bwallahu\b", "wallohu"),
        (r"(?i)\bwallahi\b", "wallohi"),
        (r"(?i)\bhadanallahu\b", "hadanallohu"),
        (r"(?i)\bbarakallahu\b", "barokallohu"),
        (r"(?i)\bbarakallah\b", "barokalloh"),
        (r"(?i)\baitullah\b", "baitulloh"),
        (r"(?i)\bhamba\s+allah\b", "hamba Alloh"),
        (r"(?i)\binsyaallah\b", "insya Alloh"),
        (r"(?i)\bmasyaallah\b", "masya Alloh"),
        (r"(?i)\ballahu\s+akbar\b", "Allohu Akbar"),
        (r"(?i)\ballahumma\b", "Allohumma"),
        (r"(?i)\ballahu\b", "Allohu"),
        (r"(?i)\ballah\b", "Alloh"),
        # Istilah ibadah & kitab yang sering dibaca kurang tepat oleh TTS standar
        (r"(?i)\bshalat\b", "sholat"),
        (r"(?i)\bshalihin\b", "sholihin"),
        (r"(?i)\bshalihah\b", "sholihah"),
        (r"(?i)\bshalih\b", "sholih"),
        (r"(?i)\bramadhan\b", "Romadhon"),
        (r"(?i)\brabbil\b", "robbil"),
        (r"(?i)\brabbina\b", "robbina"),
        (r"(?i)\brabbi\b", "robbi"),
        (r"(?i)\bsakhkhara\b", "sakhkhoro"),
    ]
    out = text
    for pattern, repl in phonetic_rules:
        out = re.sub(pattern, repl, out)
    return out


def synthesize_tts_audio(text: str, output_mp3_path: str, voice_gender: str = "male") -> float:
    """
    Menghasilkan suara narator Bahasa Indonesia jernih (100% GRATIS):
    - Prioritas 1: Microsoft Edge Neural TTS (`id-ID-ArdiNeural` atau `id-ID-GadisNeural`)
    - Prioritas 2: Google Translate TTS (`gTTS` bahasa Indonesia) jika server Edge sedang sibuk
    - Prioritas 3: Tone hening berdurasi proporsional agar pipeline tidak pernah crash.
    Mengembalikan durasi audio dalam detik.
    """
    clean_text = re.sub(r"[*#_~`<>]+", " ", text)
    clean_text = re.sub(r"\s+", " ", clean_text).strip()
    clean_text = apply_islamic_phonetic_pronunciation(clean_text)

    voice_name = "id-ID-GadisNeural" if str(voice_gender).lower() == "female" else "id-ID-ArdiNeural"
    raw_mp3 = output_mp3_path + ".raw.mp3"

    tts_ok = False
    for attempt in range(3):
        try:
            asyncio.run(_edge_tts_save(clean_text, voice_name, "-2%", raw_mp3))
            if os.path.exists(raw_mp3) and os.path.getsize(raw_mp3) > 1000:
                tts_ok = True
                break
        except Exception as e:
            print(f"[TTS] Percobaan Edge-TTS #{attempt + 1} gagal ({e}), mencoba ulang...")
            time.sleep(1.5)

    if not tts_ok:
        try:
            from gtts import gTTS

            tts = gTTS(text=clean_text, lang="id", slow=False)
            tts.save(raw_mp3)
            if os.path.exists(raw_mp3) and os.path.getsize(raw_mp3) > 500:
                tts_ok = True
        except Exception as e:
            print(f"[TTS] Fallback gTTS gagal ({e}), membuat audio cadangan...")

    if tts_ok:
        # Tambahkan jeda napas halus (0.35s di awal & 0.65s di akhir scene) + normalisasi audio stereo 44.1kHz
        cmd = [
            "ffmpeg",
            "-y",
            "-i", raw_mp3,
            "-af", "adelay=350|350,apad=pad_dur=0.65,aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            output_mp3_path,
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        try:
            os.remove(raw_mp3)
        except Exception:
            pass
    else:
        est_sec = max(14.0, len(clean_text.split()) * 0.42)
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=stereo:d={est_sec:.2f}",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            output_mp3_path,
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    return get_video_duration(output_mp3_path)


def _draw_vector_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, icon_type: str, color: Tuple[int, int, int]):
    """Menggambar ikon vektor Islami / Edukasi secara prosedural di dalam lencana lingkaran."""
    # Lingkaran luar bercahaya
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=(10, 32, 26, 240),
        outline=color + (255,),
        width=4,
    )
    inner_r = radius - 10
    draw.ellipse(
        [cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
        outline=(255, 255, 255, 90),
        width=2,
    )

    ic = icon_type.lower().strip()
    c_rgba = color + (255,)
    w_rgba = (255, 255, 255, 245)

    if ic in ("mosque", "islamic", "star"):
        # Bulan sabit & bintang 8-sudut Islami
        draw.ellipse([cx - 24, cy - 24, cx + 20, cy + 20], fill=c_rgba)
        draw.ellipse([cx - 14, cy - 28, cx + 26, cy + 12], fill=(10, 32, 26, 255))
        # Bintang kecil
        draw.polygon(
            [(cx + 14, cy - 18), (cx + 18, cy - 10), (cx + 26, cy - 10), (cx + 20, cy - 4), (cx + 22, cy + 4), (cx + 14, cy - 1), (cx + 6, cy + 4), (cx + 8, cy - 4), (cx + 2, cy - 10), (cx + 10, cy - 10)],
            fill=w_rgba,
        )
    elif ic == "book":
        # Buku terbuka
        draw.rounded_rectangle([cx - 28, cy - 18, cx - 2, cy + 18], radius=4, fill=c_rgba, outline=w_rgba, width=2)
        draw.rounded_rectangle([cx + 2, cy - 18, cx + 28, cy + 18], radius=4, fill=c_rgba, outline=w_rgba, width=2)
        draw.line([(cx, cy - 20), (cx, cy + 22)], fill=w_rgba, width=4)
    elif ic == "heart":
        draw.ellipse([cx - 24, cy - 18, cx + 2, cy + 8], fill=c_rgba)
        draw.ellipse([cx - 2, cy - 18, cx + 24, cy + 8], fill=c_rgba)
        draw.polygon([(cx - 23, cy - 2), (cx + 23, cy - 2), (cx, cy + 26)], fill=c_rgba)
    elif ic == "lightbulb":
        draw.ellipse([cx - 20, cy - 24, cx + 20, cy + 14], fill=c_rgba, outline=w_rgba, width=2)
        draw.rounded_rectangle([cx - 10, cy + 12, cx + 10, cy + 24], radius=3, fill=w_rgba)
    elif ic == "shield":
        draw.polygon(
            [(cx, cy - 26), (cx + 24, cy - 16), (cx + 20, cy + 10), (cx, cy + 28), (cx - 20, cy + 10), (cx - 24, cy - 16)],
            fill=c_rgba,
            outline=w_rgba,
            width=3,
        )
    elif ic == "compass":
        draw.ellipse([cx - 24, cy - 24, cx + 24, cy + 24], outline=w_rgba, width=3)
        draw.polygon([(cx, cy - 20), (cx + 8, cy), (cx, cy + 20), (cx - 8, cy)], fill=c_rgba)
    else:
        # Checkmark / Sparkle
        draw.line([(cx - 18, cy + 2), (cx - 4, cy + 16), (cx + 22, cy - 14)], fill=c_rgba, width=7)


def fetch_or_create_scene_illustration(
    scene: Dict[str, Any],
    topic_title: str,
    target_audience: str,
    font_path: str,
    work_dir: str,
) -> Tuple[str, str]:
    """
    Menghasilkan 1 gambar ilustrasi visual (640x480) yang menerangkan isi pembahasan pada scene tersebut (100% GRATIS):
    - Prioritas 1: Free AI Image Generator (Pollinations Flux/SDXL Tanpa API Key) berdasarkan `image_prompt` atau `headline`.
    - Prioritas 2: Ilustrasi Vektor Edukasi Prosedural beresolusi tinggi jika server gambar sedang sibuk.
    Mengembalikan tuple: (local_image_path, data_uri_base64_jpeg) untuk dipakai langsung di Remotion & FFmpeg.
    """
    import base64
    import urllib.parse
    import urllib.request

    scene_num = int(scene.get("scene_number", 1))
    out_jpg = os.path.join(work_dir, f"scene_{scene_num:02d}_illust.jpg")
    headline = str(scene.get("headline", topic_title)).strip()
    chapter = str(scene.get("chapter_title", topic_title)).strip()
    m_style = select_motion_format_style(scene, scene_num - 1, topic_title)
    scene["motion_style"] = m_style
    style_recipe = MOTION_FORMAT_STYLES.get(m_style, MOTION_FORMAT_STYLES["isometrik-dibongkar"])
    raw_prompt = str(scene.get("image_prompt", "")).strip()
    if not raw_prompt:
        raw_prompt = (
            f"Educational visual explaining {headline} ({chapter}) "
            f"about {topic_title} for {target_audience}, {style_recipe}"
        )
    else:
        raw_prompt = f"{raw_prompt}, {style_recipe}"

    img_loaded = False
    seed_val = 100 + scene_num * 37
    encoded_p = urllib.parse.quote(raw_prompt[:280])
    poll_url = f"https://image.pollinations.ai/prompt/{encoded_p}?width=640&height=480&nologo=true&seed={seed_val}"

    for attempt in range(2):
        try:
            req = urllib.request.Request(
                poll_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            raw_bytes = urllib.request.urlopen(req, timeout=22).read()
            if len(raw_bytes) > 4000:
                with open(out_jpg, "wb") as f:
                    f.write(raw_bytes)
                # Pastikan ukuran tepat 640x480 RGB
                im = Image.open(out_jpg).convert("RGB").resize((640, 480), Image.Resampling.LANCZOS)
                im.save(out_jpg, "JPEG", quality=88)
                img_loaded = True
                break
        except Exception as e:
            print(f"  [INFO GAMBAR SCENE {scene_num:02d}] Percobaan AI Image #{attempt + 1} lewat ({str(e)[:70]}), menggunakan ilustrasi cadangan...")
            time.sleep(1)

    if not img_loaded:
        # Buat ilustrasi kanvas edukatif berwarna kaya jika internet gambar sedang lambat
        theme_name = str(scene.get("theme", "emerald_gold")).lower()
        theme = SCENE_THEMES.get(theme_name, SCENE_THEMES["emerald_gold"])
        canvas = Image.new("RGBA", (640, 480), theme["bg_top"] + (255,))
        cdraw = ImageDraw.Draw(canvas)
        for y in range(0, 480, 4):
            t = y / 480.0
            r = int(theme["bg_top"][0] * (1 - t) + theme["card_bg"][0] * t)
            g = int(theme["bg_top"][1] * (1 - t) + theme["card_bg"][1] * t)
            b = int(theme["bg_top"][2] * (1 - t) + theme["card_bg"][2] * t)
            cdraw.rectangle([0, y, 640, y + 4], fill=(r, g, b, 255))
        acc = theme["accent"]
        for rad in (90, 140, 190, 240):
            cdraw.ellipse([320 - rad, 210 - rad, 320 + rad, 210 + rad], outline=acc + (55,), width=3)
        _draw_vector_icon(cdraw, cx=320, cy=195, radius=84, icon_type=str(scene.get("icon_type", "mosque")), color=acc)
        cap_font = _load_bold_font(26, font_path)
        wrapped = textwrap.wrap(headline.upper(), width=26)[:2]
        for idx_l, line_s in enumerate(wrapped):
            cdraw.text((60, 340 + idx_l * 36), line_s, font=cap_font, fill=(255, 255, 255, 245))
        canvas.convert("RGB").save(out_jpg, "JPEG", quality=88)

    with open(out_jpg, "rb") as bf:
        b64_str = base64.b64encode(bf.read()).decode("ascii")
    data_uri = f"data:image/jpeg;base64,{b64_str}"
    return out_jpg, data_uri


def render_scene_stage_image(
    scene: Dict[str, Any],
    total_scenes: int,
    stage_index: int,
    topic_title: str,
    target_audience: str,
    font_path: str,
    output_png_path: str,
) -> str:
    """
    Merender 1 keyframe state (1920x1080) dari sebuah Scene Motion Grafis:
    - stage_index = 0: Judul Utama, Header Babak, Ikon Vektor, & Progress Bar muncul
    - stage_index = 1: Kartu Poin 1 muncul menyala
    - stage_index = 2: Kartu Poin 1 + Poin 2 muncul menyala
    - stage_index = 3: Kartu Poin 1 + Poin 2 + Poin 3 + Kotak Emas Dalil/Hikmah di bawah muncul lengkap!
    Catatan: Area kanan atas (x: 1750..1900, y: 15..140) sengaja dibiarkan bersih untuk Logo Islamic K1.
    """
    W, H = 1920, 1080
    theme_name = str(scene.get("theme", "emerald_gold")).lower()
    theme = SCENE_THEMES.get(theme_name, SCENE_THEMES["emerald_gold"])

    # 1. Buat latar belakang gradasi halus + ornamen geometris Islami/modern
    base = Image.new("RGBA", (W, H), theme["bg_top"] + (255,))
    grad_draw = ImageDraw.Draw(base)
    r1, g1, b1 = theme["bg_top"]
    r2, g2, b2 = theme["bg_bottom"]
    for y in range(0, H, 4):
        t = y / float(H)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        grad_draw.rectangle([0, y, W, y + 4], fill=(r, g, b, 255))

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    # Ornamen lingkaran geometris lembut di sudut kiri bawah & kanan tengah
    acc_r, acc_g, acc_b = theme["accent"]
    for rad in (220, 300, 380):
        odraw.ellipse([-120 - rad, H - 80 - rad, -120 + rad, H - 80 + rad], outline=(acc_r, acc_g, acc_b, 26), width=3)
        odraw.ellipse([W - 180 - rad, 540 - rad, W - 180 + rad, 540 + rad], outline=(acc_r, acc_g, acc_b, 22), width=3)

    # Bingkai tipis elegan
    odraw.rounded_rectangle([28, 24, W - 28, H - 24], radius=24, outline=(acc_r, acc_g, acc_b, 95), width=2)

    # 2. Header Bar Atas (Nomor Scene, Kategori Audience, & Progress Indikator)
    scene_num = int(scene.get("scene_number", 1))
    chapter_title = str(scene.get("chapter_title", topic_title)).strip()

    # Lencana Nomor Bagian di Kiri Atas
    badge_font = _load_bold_font(26, font_path)
    small_font = _load_regular_font(24, font_path)

    odraw.rounded_rectangle(
        [68, 52, 330, 106],
        radius=14,
        fill=theme["badge_bg"] + (255,),
        outline=(255, 255, 255, 220),
        width=2,
    )
    odraw.text((90, 64), f"BAGIAN {scene_num:02d} / {total_scenes:02d}", font=badge_font, fill=theme["badge_text"] + (255,))

    # Pill Target Audience & Babak (x: 350..1680 agar tidak menabrak Logo Islamic K1 di kanan atas!)
    odraw.rounded_rectangle(
        [350, 52, 1680, 106],
        radius=14,
        fill=(255, 255, 255, 22),
        outline=(acc_r, acc_g, acc_b, 120),
        width=2,
    )
    header_info = f"AUDIENCE: {target_audience.upper()[:24]}   •   {chapter_title.upper()[:58]}"
    odraw.text((376, 65), header_info, font=small_font, fill=theme["accent_soft"] + (255,))

    # 3. Ikon Vektor & Headline Utama Scene
    _draw_vector_icon(odraw, cx=132, cy=195, radius=54, icon_type=str(scene.get("icon_type", "mosque")), color=theme["accent"])

    headline_text = str(scene.get("headline", topic_title)).upper().strip()
    headline_font = _load_bold_font(54, font_path)
    _draw_text_with_3d_stroke(
        draw=odraw,
        pos=(212, 145),
        text=headline_text[:46],
        font=headline_font,
        fill=(255, 255, 255, 255),
        stroke_fill=(4, 16, 12, 255),
        stroke_width=6,
        shadow_offset=5,
    )

    sub_topic_font = _load_bold_font(27, font_path)
    odraw.text(
        (215, 214),
        f"TOPIK UTAMA: {topic_title.upper()[:68]}",
        font=sub_topic_font,
        fill=theme["accent"] + (255,),
    )

    # 4. Kartu Poin Penjelasan (3 Bullet Points yang Muncul Bertahap sesuai stage_index)
    bullets = scene.get("bullet_points", [])
    if not isinstance(bullets, list):
        bullets = [str(bullets)]
    while len(bullets) < 3:
        bullets.append("Memahami dan mengamalkan ilmu dengan penuh keikhlasan.")

    bullet_font = _load_bold_font(34, font_path)
    num_font = _load_bold_font(38, font_path)

    card_y_positions = [285, 455, 625]
    card_h = 142
    illust_local_path = str(scene.get("_local_image_path", "")).strip()
    has_illust = bool(illust_local_path and os.path.exists(illust_local_path))
    card_x2 = 1230 if has_illust else (W - 76)

    for idx in range(3):
        cy = card_y_positions[idx]
        is_revealed = stage_index >= (idx + 1)
        is_current_active = stage_index == (idx + 1)

        if is_revealed:
            bg_alpha = 242 if is_current_active else 210
            border_col = theme["accent"] + (255,) if is_current_active else (255, 255, 255, 110)
            border_w = 4 if is_current_active else 2

            # Bayangan kartu
            odraw.rounded_rectangle(
                [76, cy + 8, card_x2 + 8, cy + card_h + 8],
                radius=22,
                fill=(0, 0, 0, 125),
            )
            # Badan kartu utama
            odraw.rounded_rectangle(
                [68, cy, card_x2, cy + card_h],
                radius=22,
                fill=theme["card_bg"] + (bg_alpha,),
                outline=border_col,
                width=border_w,
            )
            # Lencana angka di sisi kiri kartu
            odraw.rounded_rectangle(
                [92, cy + 24, 186, cy + card_h - 24],
                radius=16,
                fill=theme["badge_bg"] + (255,),
            )
            odraw.text((124, cy + 46), f"0{idx + 1}", font=num_font, fill=theme["badge_text"] + (255,))

            # Teks poin penjelasan (maksimal 2 baris)
            b_text = str(bullets[idx]).strip()
            wrap_w = 43 if has_illust else 62
            wrapped_b = textwrap.wrap(b_text, width=wrap_w)[:2]
            if len(wrapped_b) == 1:
                odraw.text((216, cy + 48), wrapped_b[0], font=bullet_font, fill=(255, 255, 255, 255))
            else:
                odraw.text((216, cy + 28), wrapped_b[0], font=bullet_font, fill=(255, 255, 255, 255))
                odraw.text((216, cy + 74), wrapped_b[1], font=bullet_font, fill=theme["accent_soft"] + (255,))
        else:
            # Placeholder tipis sebelum poin muncul
            odraw.rounded_rectangle(
                [68, cy, card_x2, cy + card_h],
                radius=22,
                fill=(255, 255, 255, 10),
                outline=(255, 255, 255, 30),
                width=1,
            )

    # 4B. Gambar Visual Ilustrasi di Sisi Kanan (x: 1265..1845, y: 285..767) dengan efek Zoom Bertahap!
    if has_illust:
        try:
            box_x1, box_y1, box_w, box_h = 1265, 285, 580, 482
            odraw.rounded_rectangle(
                [box_x1 - 6, box_y1 - 6, box_x1 + box_w + 6, box_y1 + box_h + 6],
                radius=26,
                fill=theme["card_bg"] + (240,),
                outline=theme["accent"] + (255,),
                width=4,
            )
            im_src = Image.open(illust_local_path).convert("RGB")
            # Efek Ken Burns (zoom bertahap per stage_index)
            zoom_factor = 1.0 + (stage_index * 0.04)
            zw, zh = int(box_w * zoom_factor), int(box_h * zoom_factor)
            im_zoomed = im_src.resize((zw, zh), Image.Resampling.LANCZOS)
            left_c = (zw - box_w) // 2
            top_c = (zh - box_h) // 2
            im_cropped = im_zoomed.crop((left_c, top_c, left_c + box_w, top_c + box_h)).convert("RGBA")
            base.paste(im_cropped, (box_x1, box_y1))
        except Exception:
            pass

    # 5. Kotak Highlight Dalil / Hikmah Utama di Bagian Bawah (Muncul penuh pada stage_index >= 3)
    highlight_text = str(scene.get("highlight_box", "")).strip()
    if highlight_text:
        hy = 805
        hh = 148
        if stage_index >= 3:
            odraw.rounded_rectangle(
                [68, hy, W - 76, hy + hh],
                radius=22,
                fill=theme["highlight_bg"] + (248,),
                outline=theme["accent"] + (255,),
                width=4,
            )
            # Pita label kiri "INTISARI / HIKMAH"
            label_font = _load_bold_font(24, font_path)
            odraw.rounded_rectangle(
                [94, hy + 18, 380, hy + 56],
                radius=10,
                fill=theme["badge_bg"] + (255,),
            )
            odraw.text((112, hy + 24), "HIKMAH & INTISARI", font=label_font, fill=theme["badge_text"] + (255,))

            h_font = _load_bold_font(30, font_path)
            wrapped_h = textwrap.wrap(f'"{highlight_text}"', width=76)[:2]
            for l_i, line_str in enumerate(wrapped_h):
                odraw.text(
                    (96, hy + 68 + l_i * 36),
                    line_str,
                    font=h_font,
                    fill=theme["accent_soft"] + (255,),
                )
        else:
            odraw.rounded_rectangle(
                [68, hy, W - 76, hy + hh],
                radius=22,
                fill=(255, 255, 255, 14),
                outline=(acc_r, acc_g, acc_b, 65),
                width=2,
            )
            hint_font = _load_regular_font(28, font_path)
            odraw.text(
                (96, hy + 56),
                "Simak penjelasan lengkap pada bagian ini...",
                font=hint_font,
                fill=(255, 255, 255, 135),
            )

    # 6. Progress Bar Video di Bagian Paling Bawah (y: 985..1025)
    bar_x1, bar_x2 = 68, W - 76
    bar_y = 995
    odraw.rounded_rectangle([bar_x1, bar_y, bar_x2, bar_y + 18], radius=9, fill=(255, 255, 255, 38))
    progress_frac = min(1.0, ((scene_num - 1) + (stage_index + 1) / 4.0) / float(max(1, total_scenes)))
    fill_w = max(24, int((bar_x2 - bar_x1) * progress_frac))
    odraw.rounded_rectangle([bar_x1, bar_y, bar_x1 + fill_w, bar_y + 18], radius=9, fill=theme["accent"] + (255,))

    footer_font = _load_bold_font(22, font_path)
    odraw.text((bar_x1, 1022), "ISLAMIC K1 • MOTION GRAPHICS EXPLAINER", font=footer_font, fill=(255, 255, 255, 185))
    odraw.text((bar_x2 - 380, 1022), "SUBSCRIBE • LIKE • BAGIKAN KEBAIKAN", font=footer_font, fill=theme["accent"] + (220,))

    final_img = Image.alpha_composite(base, overlay).convert("RGB")
    final_img.save(output_png_path, "PNG")
    return output_png_path


def generate_explainer_thumbnail_card(
    explainer_data: Dict[str, Any],
    topic_title: str,
    target_audience: str,
    font_path: str,
    output_card_path: str,
) -> str:
    """
    Membuat kartu ilustrasi visual tegak (440x600) untuk dipasang di sisi kanan Thumbnail Studio V3,
    sehingga Thumbnail video Explainer memiliki daya tarik visual tinggi dan seragam dengan brand Islamic K1.
    """
    cw, ch = 440, 600
    card = Image.new("RGBA", (cw, ch), (12, 54, 44, 255))
    draw = ImageDraw.Draw(card)

    # Gradasi kartu
    for y in range(0, ch, 4):
        t = y / float(ch)
        r = int(16 + (6 - 16) * t)
        g = int(72 + (30 - 72) * t)
        b = int(58 + (24 - 58) * t)
        draw.rectangle([0, y, cw, y + 4], fill=(r, g, b, 255))

    # Lencana atas
    b_font = _load_bold_font(24, font_path)
    draw.rounded_rectangle([24, 24, cw - 24, 78], radius=14, fill=(255, 204, 0, 255))
    draw.text((42, 37), "EXPLAINER 3 MENIT", font=b_font, fill=(10, 32, 24, 255))

    # Ikon besar di tengah atas
    _draw_vector_icon(draw, cx=cw // 2, cy=175, radius=68, icon_type="mosque", color=(255, 208, 0))

    # 3 Poin Ringkas di dalam kartu kanan thumbnail
    scenes = explainer_data.get("scenes", [])
    sample_points = [
        "Penjelasan Ringkas & Jelas",
        "Dilengkapi Dalil & Hikmah",
        f"Cocok untuk {target_audience[:18]}",
    ]
    if len(scenes) >= 3:
        sample_points = [
            str(scenes[1].get("headline", sample_points[0])).title()[:26],
            str(scenes[4].get("headline", sample_points[1])).title()[:26],
            str(scenes[7].get("headline", sample_points[2])).title()[:26],
        ]

    p_font = _load_bold_font(23, font_path)
    y_pt = 276
    for idx, pt in enumerate(sample_points):
        draw.rounded_rectangle(
            [24, y_pt, cw - 24, y_pt + 74],
            radius=14,
            fill=(7, 36, 28, 255),
            outline=(255, 204, 0, 255),
            width=3,
        )
        draw.rounded_rectangle(
            [36, y_pt + 16, 78, y_pt + 58],
            radius=10,
            fill=(255, 204, 0, 255),
        )
        draw.text((48, y_pt + 23), f"{idx + 1}", font=p_font, fill=(8, 30, 22, 255))
        draw.text((92, y_pt + 23), pt[:24], font=p_font, fill=(255, 252, 230, 255))
        y_pt += 90

    # Pita bawah kartu
    s_font = _load_bold_font(21, font_path)
    draw.text((48, ch - 46), f"AUDIENCE: {target_audience.upper()[:22]}", font=s_font, fill=(255, 210, 40, 255))

    card.convert("RGB").save(output_card_path, "PNG")
    return output_card_path


def render_single_scene_clip(
    scene: Dict[str, Any],
    total_scenes: int,
    topic_title: str,
    target_audience: str,
    voice_gender: str,
    font_path: str,
    work_dir: str,
) -> Tuple[str, float]:
    """
    Merender 1 Scene Motion Grafis lengkap (Audio Voiceover + 4 Tahap Animasi Kinetic Reveal + Subtle Zoom Motion)
    menjadi file MP4 berformat seragam (1920x1080, 30fps, stereo 44.1kHz).
    """
    scene_num = int(scene.get("scene_number", 1))
    audio_path = os.path.join(work_dir, f"scene_{scene_num:02d}.mp3")
    narration_text = str(scene.get("narration_text", "")).strip()

    audio_dur = synthesize_tts_audio(narration_text, audio_path, voice_gender=voice_gender)
    # Bagi durasi scene ke dalam 4 tahap kemunculan elemen visual (stage 0, 1, 2, 3)
    stage_weights = [0.16, 0.26, 0.26, 0.32]
    stage_durations = [max(1.2, audio_dur * w) for w in stage_weights]
    # Sesuaikan stage terakhir agar total durasi visual == audio_dur
    stage_durations[3] = max(1.2, audio_dur - sum(stage_durations[:3]))

    stage_pngs = []
    for st_idx in range(4):
        png_path = os.path.join(work_dir, f"scene_{scene_num:02d}_st_{st_idx}.png")
        render_scene_stage_image(
            scene=scene,
            total_scenes=total_scenes,
            stage_index=st_idx,
            topic_title=topic_title,
            target_audience=target_audience,
            font_path=font_path,
            output_png_path=png_path,
        )
        stage_pngs.append(png_path)

    # Buat file concat demuxer untuk 4 tahap visual di dalam scene ini + efek fade-in & fade-out halus
    concat_txt = os.path.join(work_dir, f"scene_{scene_num:02d}_frames.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for st_idx, png_p in enumerate(stage_pngs):
            safe_p = png_p.replace("\\", "/")
            f.write(f"file '{safe_p}'\n")
            f.write(f"duration {stage_durations[st_idx]:.3f}\n")
        # Ulangi gambar terakhir sesuai aturan concat demuxer FFmpeg
        f.write(f"file '{stage_pngs[-1].replace(chr(92), '/')}'\n")

    scene_mp4 = os.path.join(work_dir, f"scene_{scene_num:02d}_clip.mp4")
    fade_out_start = max(0.5, audio_dur - 0.40)
    vf_filter = (
        f"fps=30,scale=1920:1080,setsar=1,format=yuv420p,"
        f"fade=t=in:st=0:d=0.35,fade=t=out:st={fade_out_start:.2f}:d=0.35"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_txt,
        "-i", audio_path,
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "21",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        "-shortest",
        scene_mp4,
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    real_dur = get_video_duration(scene_mp4)
    return scene_mp4, real_dur


def build_complete_explainer_package(
    topic_title: str,
    target_audience: str,
    gemini_api_key: str,
    logo_path: str,
    outro_path: str,
    font_path: str,
    work_dir: str,
    category_hint: str = "",
) -> Dict[str, Any]:
    """
    Menjalankan seluruh proses pembuatan Video Motion Grafis Explainer 3 Menit dari awal sampai akhir:
    1. Menyusun Script 10 Scene, Storyboard, & Metadata dengan Gemini AI.
    2. Membuat Voiceover Bahasa Indonesia & Merender Motion Grafis per Scene.
    3. Menggabungkan seluruh Scene + Menempelkan Logo Islamic K1 di Kanan Atas + Menyambungkan Video Subscribe di Akhir.
    4. Menghitung Chapters/Timeline detik per detik secara presisi & merender Thumbnail High-CTR Studio V3.
    """
    explainer_data = generate_explainer_storyboard_and_metadata(
        topic_title=topic_title,
        target_audience=target_audience,
        gemini_api_key=gemini_api_key,
        category_hint=category_hint,
    )

    scenes = explainer_data.get("scenes", [])
    total_scenes = len(scenes)
    voice_gender = explainer_data.get("voice_gender", "male")

    scene_clips: List[str] = []
    chapters: List[Dict[str, Any]] = []
    cumulative_sec = 0.0

    print(f"[MOTION ENGINE] Merender {total_scenes} Scene Motion Grafis, Ilustrasi Visual AI, & Voiceover Bahasa Indonesia...")
    for idx, sc in enumerate(scenes):
        sc["scene_number"] = idx + 1
        local_img_path, img_data_uri = fetch_or_create_scene_illustration(
            scene=sc,
            topic_title=topic_title,
            target_audience=target_audience,
            font_path=font_path,
            work_dir=work_dir,
        )
        sc["_local_image_path"] = local_img_path
        sc["image_url"] = img_data_uri
        chapters.append(
            {
                "time_seconds": int(round(cumulative_sec)),
                "title": str(sc.get("chapter_title", f"Bagian {idx + 1}")).strip(),
            }
        )
        clip_path, clip_dur = render_single_scene_clip(
            scene=sc,
            total_scenes=total_scenes,
            topic_title=topic_title,
            target_audience=target_audience,
            voice_gender=voice_gender,
            font_path=font_path,
            work_dir=work_dir,
        )
        scene_clips.append(clip_path)
        cumulative_sec += clip_dur
        print(f"  -> Scene {idx + 1:02d}/{total_scenes:02d} selesai (+Gambar Ilustrasi | {clip_dur:.1f}s | Total: {cumulative_sec:.1f}s)")

    # Gabungkan semua klip scene menjadi satu video utama
    all_scenes_txt = os.path.join(work_dir, "all_scenes_concat.txt")
    with open(all_scenes_txt, "w", encoding="utf-8") as f:
        for cp in scene_clips:
            f.write(f"file '{cp.replace(chr(92), '/')}'\n")

    raw_explainer_mp4 = os.path.join(work_dir, "raw_explainer_body.mp4")
    cmd_join = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", all_scenes_txt,
        "-c", "copy",
        raw_explainer_mp4,
    ]
    subprocess.run(cmd_join, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    # Pasang Logo Islamic K1 kecil di Kanan Atas + Sambungkan Video SUBSCRIBE ISLAMIC K1.mp4 di Akhir
    # Jika engine Remotion (React 1080p Motion Graphics 100% Gratis) tersedia, render visual dengan Remotion
    base_dir = os.path.dirname(os.path.abspath(__file__))
    remotion_dir = os.path.join(base_dir, "remotion_explainer")
    portable_node_dir = os.path.join(base_dir, "node_portable", "node-v20.18.0-win-x64")
    if os.path.isdir(portable_node_dir) and portable_node_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = portable_node_dir + os.pathsep + os.environ.get("PATH", "")

    if os.path.isdir(os.path.join(remotion_dir, "node_modules")):
        try:
            print("[REMOTION ENGINE] Merender animasi React Remotion 1080p (100% Gratis)...")
            theme_keys = list(SCENE_THEMES.keys())
            remotion_fps = 12
            remotion_scenes = []
            for idx, sc in enumerate(scenes):
                c_dur = get_video_duration(scene_clips[idx])
                m_style = select_motion_format_style(sc, idx, topic_title)
                p_label = str(sc.get("pointer_label") or sc.get("headline") or f"FOKUS SCENE {idx + 1}").upper()[:28]
                remotion_scenes.append(
                    {
                        "scene_number": idx + 1,
                        "section_badge": str(sc.get("chapter_title") or sc.get("section_badge") or f"BAGIAN {idx + 1}"),
                        "headline": str(sc.get("headline", topic_title)),
                        "bullet_points": list(sc.get("bullet_points", []))[:3],
                        "highlight_box": str(sc.get("highlight_box", "")),
                        "narration_text": str(sc.get("narration_text", "")),
                        "motion_style": m_style,
                        "pointer_label": p_label,
                        "image_url": str(sc.get("image_url", "")),
                        "icon_type": str(sc.get("icon_type", "mosque")),
                        "theme_name": str(sc.get("theme") or sc.get("theme_name") or theme_keys[idx % len(theme_keys)]),
                        "durationInFrames": max(24, int(round(c_dur * remotion_fps))),
                    }
                )
            props_path = os.path.join(work_dir, "remotion_props.json")
            with open(props_path, "w", encoding="utf-8") as pf:
                json.dump(
                    {"topicTitle": topic_title, "targetAudience": target_audience, "scenes": remotion_scenes},
                    pf,
                    ensure_ascii=False,
                )
            remotion_vis = os.path.join(work_dir, "remotion_vis.mp4")
            npx_bin = os.path.join(portable_node_dir, "npx.cmd") if os.path.exists(os.path.join(portable_node_dir, "npx.cmd")) else ("npx.cmd" if os.name == "nt" else "npx")
            cpu_concurrency = max(2, min(6, os.cpu_count() or 4))
            subprocess.run(
                [
                    npx_bin,
                    "remotion",
                    "render",
                    "src/index.ts",
                    "IslamicK1Explainer",
                    remotion_vis,
                    f"--props={props_path}",
                    f"--concurrency={cpu_concurrency}",
                    "--image-format=jpeg",
                    "--jpeg-quality=85",
                ],
                cwd=remotion_dir,
                env=os.environ.copy(),
                check=True,
            )
            remotion_merged = os.path.join(work_dir, "remotion_merged.mp4")
            subprocess.run(
                ["ffmpeg", "-y", "-i", remotion_vis, "-i", raw_explainer_mp4, "-map", "0:v:0", "-map", "1:a:0", "-vf", "fps=30,scale=1920:1080,setsar=1,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-c:a", "copy", "-shortest", remotion_merged],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            os.replace(remotion_merged, raw_explainer_mp4)
            print("[REMOTION ENGINE] Animasi Remotion 1080p berhasil digabungkan dengan Voiceover!")
        except Exception as rem_err:
            print(f"[INFO REMOTION] Menggunakan hasil Kinetic Engine standar ({rem_err})")

    final_video_path = os.path.join(work_dir, "final_explainer_islamick1.mp4")
    print("[FFMPEG] Menambahkan Logo Islamic K1 di kanan atas & menyambungkan video SUBSCRIBE di akhir...")
    final_duration = render_final_video(
        input_video_path=raw_explainer_mp4,
        outro_video_path=outro_path,
        logo_path=logo_path,
        output_video_path=final_video_path,
        cut_last_seconds=0.0,  # Jangan potong 4 detik akhir karena ini video asli buatan kita, bukan NotebookLM!
    )
    print(f"[FFMPEG] Video Motion Grafis selesai! Durasi total dengan outro Subscribe: {final_duration:.1f} detik ({final_duration/60:.1f} menit)")
    thumb_path = ""

    # Susun Deskripsi Lengkap (Salam Pembuka + 3 Paragraf + Chapters/Timeline + Info Channel + Salam Penutup + Hashtag)
    timeline_block = validate_youtube_timeline(chapters, cumulative_sec)
    paragraphs = explainer_data.get("description_paragraphs", [])
    if len(paragraphs) < 3:
        paragraphs = build_fallback_explainer_data(topic_title, target_audience)["description_paragraphs"]

    if not paragraphs[0].lower().startswith("assalamu"):
        paragraphs[0] = "Assalamu'alaikum Warahmatullahi Wabarakatuh.\n" + paragraphs[0]
    if "wassalamu" not in paragraphs[-1].lower():
        paragraphs[-1] = paragraphs[-1] + "\nWassalamu'alaikum Warahmatullahi Wabarakatuh."

    hashtags = explainer_data.get("hashtags", ["#IslamicK1", "#KeluargaMuslim", "#EdukasiIslami", "#BelajarIslam"])
    hashtags = [h if str(h).startswith("#") else f"#{h}" for h in hashtags][:8]
    if "#IslamicK1" not in hashtags:
        hashtags.insert(0, "#IslamicK1")
    hashtag_line = " ".join(hashtags[:8])

    full_description = (
        f"{paragraphs[0]}\n\n"
        f"{paragraphs[1]}\n\n"
        f"📌 TIMELINE / CHAPTERS PEMBAHASAN:\n"
        f"{timeline_block}\n\n"
        f"{paragraphs[2]}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔔 Dukung terus dakwah & edukasi Keluarga Muslim di Channel Resmi Islamic K1:\n"
        f"👉 https://www.youtube.com/@islamick1832\n"
        f"🎯 Target Audience: {target_audience}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{hashtag_line}"
    )

    localizations = explainer_data.get("localizations", {})
    if not localizations:
        try:
            from deep_translator import GoogleTranslator

            base_title = explainer_data.get("title", f"{topic_title} | {target_audience} | Islamic K1")
            base_desc = "\n\n".join(paragraphs)
            for lang_code in ["en", "ar", "ms", "tr", "ur", "fr", "de", "es", "ru"]:
                try:
                    tr_title = GoogleTranslator(source="id", target=lang_code).translate(base_title)[:95]
                    tr_desc = GoogleTranslator(source="id", target=lang_code).translate(base_desc)[:4500]
                    localizations[lang_code] = {"title": tr_title, "description": tr_desc}
                except Exception:
                    pass
        except Exception:
            pass

    return {
        "final_video_path": final_video_path,
        "thumbnail_path": thumb_path,
        "final_duration": final_duration,
        "title": explainer_data.get("title", f"{topic_title} | {target_audience} | Islamic K1")[:95],
        "full_description": full_description,
        "tags": explainer_data.get("tags", ["Islamic K1", topic_title[:45], target_audience[:35], "Edukasi Islami"])[:15],
        "playlist_name": explainer_data.get("playlist_name", "Explainer Islami & Edukasi Keluarga Muslim"),
        "recommended_publish_slot": explainer_data.get("recommended_publish_slot", "MALAM"),
        "localizations": localizations,
    }
