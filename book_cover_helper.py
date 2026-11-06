"""
Modul Pembantu:
1. Standarisasi Akhiran Judul YouTube (Contoh: `... I PAIBP 5 I Bab 1`, `... I Fikih 5 I Bab 1`, dst.)
2. Pencari Gambar Cover Buku Resmi untuk Sisi Kanan Thumbnail:
   - Mencari di 2 folder Google Drive buku milik user:
     * Folder 1: 1clzgag-NRyYUhlxFEy9Pe2eX3b-Lt4ME (PAI Merdeka, B. Indonesia, Pancasila, IPAS, IQRO, Al-Barqy)
     * Folder 2: 1im355GYZfrBz9S8JuU_FHComBGGddG22 (Fikih, Akidah Akhlak, Al-Qur'an Hadis, Bahasa Arab, SKI)
   - Jika buku di Drive berupa potongan per-Bab (seperti PAI 1-9) atau belum ada di Drive,
     otomatis mencari gambar Cover Buku Siswa resmi di internet & menyimpannya di cache Google Drive `00_Assets`.
3. Penentuan & Pembuatan Playlist Otomatis sesuai Mata Pelajaran dan Kelasnya.
"""

import os
import re
import io
import urllib.parse
import urllib.request
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image
from googleapiclient.http import MediaFileUpload

# ID Folder Google Drive Buku milik User
DRIVE_BOOK_FOLDER_1 = "1clzgag-NRyYUhlxFEy9Pe2eX3b-Lt4ME"
DRIVE_BOOK_FOLDER_2 = "1im355GYZfrBz9S8JuU_FHComBGGddG22"

# Daftar Mapel & Normalisasi Kode Judul
SUBJECT_PATTERNS = [
    (r"\b(?:pai|paibp|pendidikan\s+agama\s+islam)\b", "PAIBP", "Pendidikan Agama Islam dan Budi Pekerti"),
    (r"\bushul\s*fiq[ih]*\b", "Ushul Fiqh", "Ushul Fiqh"),
    (r"\bfi(?:k|q)ih\b", "Fikih", "Fikih Kemenag"),
    (r"\ba[kq]idah\s*akhlak\b", "Akidah Akhlak", "Akidah Akhlak Kemenag"),
    (r"\b(?:al[-\s]*qur'?an\s*hadis?t?|qh)\b", "Al-Qur'an Hadis", "Al-Qur'an Hadis Kemenag"),
    (r"\b(?:ski|sejarah\s+kebudayaan\s+islam)\b", "SKI", "Sejarah Kebudayaan Islam Kemenag"),
    (r"\bbahasa\s+arab\b", "Bahasa Arab", "Bahasa Arab Kemenag"),
    (r"\bbahasa\s+indonesia\b", "Bahasa Indonesia", "Bahasa Indonesia Kurikulum Merdeka"),
    (r"\b(?:pendidikan\s+pancasila|ppkn|pkn)\b", "Pendidikan Pancasila", "Pendidikan Pancasila Kurikulum Merdeka"),
    (r"\bipas?\b", "IPAS", "IPAS Kurikulum Merdeka"),
]

# Peta File ID PDF Buku Utuh yang sudah ada di Google Drive User (Halaman 1 = Cover Buku Resmi)
KNOWN_FULL_BOOK_PDF_IDS: Dict[Tuple[str, int], str] = {
    # PAIBP SMA (Kelas 10-12) di Drive Folder 1
    ("PAIBP", 10): "1RjeuULh3QnMZwyDSzA2lXitGnrLdo-iE",
    ("PAIBP", 11): "1miSGaITGwC5chAy9zi_lBmoZbMJtsqww",
    ("PAIBP", 12): "1g5qDXEU5GR7BcWHkM4zjm09oVPJqK4Dm",
    # Akidah Akhlak (Kelas 1-12) di Drive Folder 2
    ("Akidah Akhlak", 1): "15OtVn0n3ym_JjaOAZyX6CvtzvcjJvg4t",
    ("Akidah Akhlak", 2): "1YxH2BfXUXoGe6tLfDU-P6SErSl4kuVtd",
    ("Akidah Akhlak", 3): "13PXKY2JlOvLdhTGjkxmgh6I-rsbc_5fZ",
    ("Akidah Akhlak", 4): "1RmtK16w_zGmGc9MQMp6qzwU-pfV8qoLw",
    ("Akidah Akhlak", 5): "128_rFFhvyL6NzZSKpbP8PdNcgLg-maCs",
    ("Akidah Akhlak", 6): "17qiq9tEJQKNUa75ws70nuGsuXbIFPJeD",
    ("Akidah Akhlak", 7): "1jLpFpjNbwoPL7serJrgaVigBeZUg9aB5",
    ("Akidah Akhlak", 8): "1tdMxxW53-Cro2N_2P9z7hsqPBccfg0B7",
    ("Akidah Akhlak", 9): "11FgOUDUm9HMb2FRE7xb07Z0trxLXUvE3",
    ("Akidah Akhlak", 10): "1yeHi5oxW8lrA9pEsNr7ZlpxDig34mIRh",
    ("Akidah Akhlak", 11): "1y81C78weO_zC5ym0icGCo8S_IG7Ylbmk",
    ("Akidah Akhlak", 12): "12GJ7rVMRyOd6nNqKpAXz040kY-i8gVBx",
    # Al-Qur'an Hadis (Kelas 1-12) di Drive Folder 2
    ("Al-Qur'an Hadis", 1): "1mmVLXkDSZ5KCAIYb6qmeRNlxr_lEXRr1",
    ("Al-Qur'an Hadis", 2): "1Kw9jNfsVn3OlFPNdTVyjjOdE0pk3daLW",
    ("Al-Qur'an Hadis", 3): "11kg1JxLi8Oxr6M5v6Y-73FeGjQu-HtZ5",
    ("Al-Qur'an Hadis", 4): "1IOVMnjAc-tiUgqfyp7ZcnUAVWcGhEamj",
    ("Al-Qur'an Hadis", 5): "1hO3h_HH1so7tdDopQsbMKvylPwUv8v6T",
    ("Al-Qur'an Hadis", 6): "1kh4Md3I4Rf-piYIZNR2gSc-HqH51bmAS",
    ("Al-Qur'an Hadis", 7): "1Vqd5YCuoanmq-mZXXHFEaMEoPO1ts-vQ",
    ("Al-Qur'an Hadis", 8): "16RbNDfSz6cvO4WVHEIg3gwo49wv6deIK",
    ("Al-Qur'an Hadis", 9): "1UL4Kz5MuMcWh_tDTTx2KUwxj2n1X2CCs",
    ("Al-Qur'an Hadis", 10): "1M_MkGdO1AHhOGxQdbw1cc4n45uqjH7dR",
    ("Al-Qur'an Hadis", 11): "1nzZgstiSJ53c_IEi9yFaQDqtawl72qOZ",
    ("Al-Qur'an Hadis", 12): "1BYYzX26dOBYF6h2i5CzD4WnxseEx0nnF",
    # Bahasa Arab (Kelas 1-12) di Drive Folder 2
    ("Bahasa Arab", 1): "1jWXMurFkB52S2vV-LzHVAeqIxdaZJpmS",
    ("Bahasa Arab", 2): "11EBEKtL2XLuXmqnXqKqcI3b-oe2oPo8l",
    ("Bahasa Arab", 3): "1uyiQHYFs7eHdc6vrSvQXSTPkWyPQoPIe",
    ("Bahasa Arab", 4): "1Q3USRGMyJ0EzExZGQnqI4BtXn7Djwxma",
    ("Bahasa Arab", 5): "1YT4bZVKauPTmcCDIqMileJ-b7gMvzrl5",
    ("Bahasa Arab", 6): "1v3FQQm3GG9Z1UaStbada0JFRqvdhYoGD",
    ("Bahasa Arab", 7): "10-eiHPs4QEwx1I1FyHabgooMSObq2duZ",
    ("Bahasa Arab", 8): "1ZlHDqV_YMP8x45x9LeZJ70RJkEMrQolx",
    ("Bahasa Arab", 9): "1Enj1qYE9JYQ9sl40cLjnpo4Ux8-bi0gl",
    ("Bahasa Arab", 10): "1GgmyZo8_ICHdil6lOsaSZCXMIs_mKxoG",
    ("Bahasa Arab", 11): "1O6EUiD9PzGt6ojNJOOPio7N2Yc2COSwU",
    ("Bahasa Arab", 12): "1W2us214iUtvaxTd2VNbfbk2WHD84jItG",
    # Fikih (Kelas 1-12) di Drive Folder 2
    ("Fikih", 1): "1k8trW60NpJTXKkIYT9rGYJX68m8F5_dg",
    ("Fikih", 2): "139FNodtMQmZ1ti8-XAO4ziGYrxTL85DP",
    ("Fikih", 3): "1L3FnqYoCitX9DRdC5t9-0vF6LBbDgGvQ",
    ("Fikih", 4): "1W57r9wkZugde5urSnmwxH0p8HqVTT5un",
    ("Fikih", 5): "16n-W0Ldy_JO9zfBa3BYxUjGeSawaMVm_",
    ("Fikih", 6): "1QtciGyYzeYsfASEg7SCZgLBy2tDcr2Je",
    ("Fikih", 7): "1j0rO_2KAEmrENvgw9BG2AB2SMbMwncsA",
    ("Fikih", 8): "1vQNUzOuN2SEj5SqLCduONNHo2xtzVjXb",
    ("Fikih", 9): "1jdNUI0g0qs1xk4ShYI-b4WaACuGfUBAy",
    ("Fikih", 10): "1w-wyKpe37-ePXm4lagaHyet9Tu0j4ubY",
    ("Fikih", 11): "16q9AVFaBTQdUePdV2AveYyDl45KWJV7E",
    ("Fikih", 12): "1hCO5AinWR-qRIT5zPjIJCVxtgfeN0owh",
    # SKI (Kelas 3-12) di Drive Folder 2
    ("SKI", 3): "14YDP7S6atb53AEYD41C2ETtCO1iFQhVD",
    ("SKI", 4): "1iB3ujPHySjNzawdrTkC3aJIi0p_ooOOB",
    ("SKI", 5): "1byd_2DVFreAGKafH1xRAbsUwhSZh4N21",
    ("SKI", 6): "1_2-xmCDN59Pm9_RlZYW6rFgFTST-i2VS",
    ("SKI", 7): "1fWrQpmyxPGOriCw7CycxBHePohp3TgQY",
    ("SKI", 8): "1bJxBDl72zqZ9RTbGxRNlUclEEG38N68u",
    ("SKI", 9): "1ygPuJxAEti9W7FtfLQLcnJ6Z4wvMHg05",
    ("SKI", 10): "1iJcMm49Zuk0NMkAuWx2zNk0ocYGfEV6Q",
    ("SKI", 11): "10ssO5AggX7zqUyhArdA0WSzShW0ntwu9",
    ("SKI", 12): "1vkZQ-empgoIbCNUURfPBrzURAsTNYvC8",
    # Bahasa Indonesia (Kelas 1-12) di Drive Folder 1
    ("Bahasa Indonesia", 1): "1HMm0Wo5lC1xJEcMu6_DjiwdZwa_ZA3Ci",
    ("Bahasa Indonesia", 2): "1Arw4di19rnzvvH7xtilGiSwmLfxYDhGz",
    ("Bahasa Indonesia", 3): "1ynN8zVTbSknZf1XuXnUBEl9CGVpDtwbQ",
    ("Bahasa Indonesia", 4): "1Weo7Up3e618qRZGKGr5ZdR1ApiC4o_MG",
    ("Bahasa Indonesia", 5): "1b8eXKqSEhNOhYVDI3YO65BGAVZrbJ4Ut",
    ("Bahasa Indonesia", 6): "1Zx5mHnwX9ysP4yZBEP8qFEipGHJr7nnc",
    ("Bahasa Indonesia", 7): "1XV7CMGwzOWb2MZ-IwZsDgT7l8HqW1irO",
    ("Bahasa Indonesia", 8): "1uT2sZPmlWnsvpjTy3VYhm1S1vbS5OAmg",
    ("Bahasa Indonesia", 9): "1H0lXNBqo66OuFfoLX3WNccUWfIm2e9fj",
    ("Bahasa Indonesia", 10): "1jwetoj4qfa4RYraOmBUuda9C_la8dPif",
    ("Bahasa Indonesia", 11): "1uLBVxHNUFywc4OP6D8ObwFHXqG8blIF8",
    ("Bahasa Indonesia", 12): "1qAIyvKm__cf7Gkfvs6eahpXUpOrCnAEV",
    # Pendidikan Pancasila (Kelas 1-12) di Drive Folder 1
    ("Pendidikan Pancasila", 1): "16fpUwufzBVaU8lRvtf0xR1NRKRoP1ZDE",
    ("Pendidikan Pancasila", 2): "1AxYT3HjCQWW_rQoYNYeLYQy185EJtriu",
    ("Pendidikan Pancasila", 3): "1JnAoHjibZYDpDQS1c_qZyf1-7SCH6RaK",
    ("Pendidikan Pancasila", 4): "1kRzHrHtjdQ4ozxO4f3-5ivzE_dTAazd_",
    ("Pendidikan Pancasila", 5): "103y1qI_A5I-L9vRxMrj9kb1oC5LfDtNB",
    ("Pendidikan Pancasila", 6): "1yaLayo4k_PJzcnBo-QJjlZkRpaKkgIwL",
    ("Pendidikan Pancasila", 7): "19nQ9YuuNPIU9SdtL39OFnXt2XxXwwa4h",
    ("Pendidikan Pancasila", 8): "1kLytt11JtSMv9h1-kuFkNzNEuyL7lb14",
    ("Pendidikan Pancasila", 9): "1jzDXllalWJW2AkSNdm_bZ_kSJl1pyIMb",
    ("Pendidikan Pancasila", 10): "10jeWY6DtxXq1AQf8nAGLMZ394AHoIXW5",
    ("Pendidikan Pancasila", 11): "1wLtRvU4sEovRtIieVTIBBYsozwvTF_zV",
    ("Pendidikan Pancasila", 12): "1iQ_uGPQm1U4V33NYSBzARgtuKqHXLjKx",
    # IPAS (Kelas 3-10) di Drive Folder 1
    ("IPAS", 3): "1c9gZHzd-toY5jPR1vZFvQu0tRcyIaPTD",
    ("IPAS", 4): "1fgmTriao26TkY89SbhboRnUy7T0gZwbq",
    ("IPAS", 5): "1YP0kzHtnS3ZZ2_q9nMt1Zvj4tEZ0CZsB",
    ("IPAS", 6): "1N7mGiXLDdqxWAFyzuyBJk0LZBI_l6K2t",
    ("IPAS", 7): "1fxO2wQmt5vUflQcoOXCvyAlRt-Vq6Qfz",
    ("IPAS", 8): "1oxIErR3DNxttvLJga9zGMxQjg2hy5d7y",
    ("IPAS", 9): "1J8JOEvggphCY1fOKhxOzCCdvKR_ogqte",
    ("IPAS", 10): "1-Z4JdqabiQGF3aUgn0lNL-lcIkuYaPA9",
}


def parse_textbook_metadata(filename: str) -> Dict[str, Any]:
    """
    Mengekstrak informasi Mata Pelajaran, Kelas, Bab, Topik Bersih, dan Akhiran Judul Seragam
    dari nama file video.
    Contoh:
    - "PAI 6 Bab 9. Panduan Puasa Sunah dalam Islam.mp4"
      -> subject_code: "PAIBP", kelas: 6, bab: 9,
         suffix: "I PAIBP 6 I Bab 9",
         topic: "Panduan Puasa Sunah dalam Islam"
    - "Fikih 5 Bab 1. Makanan Halal.mp4"
      -> subject_code: "Fikih", kelas: 5, bab: 1,
         suffix: "I Fikih 5 I Bab 1"
    """
    base = os.path.splitext(filename)[0].strip()

    subject_code = None
    subject_full = None
    for pattern, code, full_name in SUBJECT_PATTERNS:
        if re.search(pattern, base, flags=re.IGNORECASE):
            subject_code = code
            subject_full = full_name
            break

    # Cari pola "<Mapel> <Kelas> ... Bab <Bab>"
    kelas_num: Optional[int] = None
    bab_num: Optional[int] = None

    m_kb = re.search(
        r"(?:kelas|kls|pai|paibp|fikih|fiqih|ushul\s*fiq[ih]*|akidah\s*akhlak|al[-\s]*qur'?an\s*hadis?t?|ski|bahasa\s+arab|bahasa\s+indonesia|pendidikan\s+pancasila|ipas?)\s*(\d{1,2})\b.*?\bbab\s*(\d{1,2})\b",
        base,
        flags=re.IGNORECASE,
    )
    if m_kb:
        kelas_num = int(m_kb.group(1))
        bab_num = int(m_kb.group(2))
    else:
        m_k = re.search(r"\b(?:kelas|kls|pai|paibp|fikih|fiqih|ski|ipas?)\s*(\d{1,2})\b", base, flags=re.IGNORECASE)
        if m_k:
            kelas_num = int(m_k.group(1))
        m_b = re.search(r"\bbab\s*(\d{1,2})\b", base, flags=re.IGNORECASE)
        if m_b:
            bab_num = int(m_b.group(1))

    # Jika nama file diawali "<Mapel> <Kelas> Bab <Bab>" tapi belum masuk daftar baku (misal: "Tarikh 5 Bab 1")
    if not subject_code:
        m_generic = re.match(r"^([A-Za-z\s\-']+?)\s+(\d{1,2})\s*[-\.]*\s*Bab\s*(\d{1,2})\b", base, flags=re.IGNORECASE)
        if m_generic:
            subject_code = m_generic.group(1).strip().title()
            subject_full = subject_code
            kelas_num = int(m_generic.group(2))
            bab_num = int(m_generic.group(3))

    # Bersihkan topik dari awalan "PAI 6 Bab 9 - " dsb.
    clean_topic = re.sub(
        r"^.*?\bbab\s*\d{1,2}\s*[\.\-:|I]*\s*",
        "",
        base,
         count=1,
        flags=re.IGNORECASE,
    ).strip()
    if not clean_topic:
        clean_topic = base

    # Susun akhiran judul seragam: "I PAIBP 5 I Bab 1" atau "I Fikih 5 I Bab 1"
    if subject_code and kelas_num and bab_num:
        uniform_suffix = f"I {subject_code} {kelas_num} I Bab {bab_num}"
        badge_text = f"{subject_code.upper()} {kelas_num} • BAB {bab_num}"
    elif subject_code and kelas_num:
        uniform_suffix = f"I {subject_code} {kelas_num}"
        badge_text = f"{subject_code.upper()} KELAS {kelas_num}"
    elif subject_code and bab_num:
        uniform_suffix = f"I {subject_code} I Bab {bab_num}"
        badge_text = f"{subject_code.upper()} • BAB {bab_num}"
    else:
        uniform_suffix = ""
        badge_text = "ISLAMIC K1 • KELUARGA MUSLIM"

    return {
        "subject_code": subject_code,
        "subject_full": subject_full,
        "kelas": kelas_num,
        "bab": bab_num,
        "clean_topic": clean_topic,
        "uniform_suffix": uniform_suffix,
        "badge_text": badge_text,
    }


def format_uniform_youtube_title(raw_title: str, filename: str) -> str:
    """
    Memastikan Judul YouTube diakhiri secara seragam dengan format:
    `<Judul Materi> I PAIBP 5 I Bab 1` atau `<Judul Materi> I Fikih 5 I Bab 1`
    dan panjang total <= 100 karakter (tanpa memotong akhiran).
    """
    meta = parse_textbook_metadata(filename)
    suffix = meta["uniform_suffix"]
    if not suffix:
        return raw_title[:100]

    # Bersihkan embel-embel kelas/bab/channel lama di akhir raw_title agar tidak ganda
    cleaned = raw_title.strip()
    cleaned = re.sub(r"\s*[\|I]\s*(?:PAI|PAIBP|Islamic\s*K1|Materi\s*PAI).*$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"[:\-\|]\s*(?:Materi\s*)?(?:PAI|PAIBP)\s*Kelas\s*\d+.*$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\s*\((?:PAI|PAIBP)\s*Kelas\s*\d+.*?\)\s*$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^PAI\s*(?:Kelas\s*)?\d+\s*Bab\s*\d+\s*[:\-\.]\s*", "", cleaned, flags=re.IGNORECASE).strip()

    if not cleaned or len(cleaned) < 5:
        cleaned = meta["clean_topic"]

    max_topic_len = 100 - len(suffix) - 1
    if len(cleaned) > max_topic_len:
        cleaned = cleaned[: max_topic_len - 1].rsplit(" ", 1)[0].rstrip(":,-|")

    return f"{cleaned} {suffix}"


def _download_pdf_cover_from_drive(drive, pdf_file_id: str, dest_path: str) -> bool:
    """
    Mengambil gambar halaman pertama (Cover Buku) resolusi tinggi (=s1200)
    dari file PDF di Google Drive menggunakan thumbnailLink resmi Drive API.
    """
    try:
        info = drive.files().get(fileId=pdf_file_id, fields="id,name,thumbnailLink").execute(num_retries=3)
        thumb_link = info.get("thumbnailLink")
        if not thumb_link:
            return False
        high_res_url = re.sub(r"=s\d+$", "=s1200", thumb_link)
        req = urllib.request.Request(high_res_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            img_bytes = resp.read()
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        if img.width >= 200 and img.height >= 250:
            img.save(dest_path, "JPEG", quality=95)
            return True
    except Exception as e:
        print(f"[COVER] Gagal mengambil thumbnailLink Drive ({pdf_file_id}): {e}")
    return False


def _search_book_cover_on_internet(subject_code: str, subject_full: str, kelas: Optional[int], dest_path: str) -> bool:
    """
    Mencari gambar Cover Buku Siswa resmi di internet (Bing Images) untuk buku
    yang belum memiliki PDF utuh di Google Drive (seperti PAIBP Kelas 1-9, Ushul Fiqh, dll.).
    Memilih gambar berorientasi tegak (portrait book cover) dengan resolusi baik.
    """
    jenjang = ""
    if kelas:
        if kelas <= 6:
            jenjang = f"SD/MI Kelas {kelas}"
        elif kelas <= 9:
            jenjang = f"SMP/MTs Kelas {kelas}"
        else:
            jenjang = f"SMA/MA Kelas {kelas}"

    if subject_code == "PAIBP":
        search_q = f"cover buku siswa Pendidikan Agama Islam dan Budi Pekerti {jenjang} Kurikulum Merdeka kemendikbud"
    else:
        search_q = f"cover buku siswa {subject_full or subject_code} {jenjang} Kurikulum Merdeka Kemenag"

    encoded_q = urllib.parse.quote(search_q)
    url = f"https://www.bing.com/images/search?q={encoded_q}&form=HDRSC2"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        urls = re.findall(r"murl&quot;:&quot;(https?://[^&]+?\.(?:jpg|jpeg|png))&quot;", html, flags=re.IGNORECASE)
        for img_url in urls[:10]:
            try:
                img_req = urllib.request.Request(img_url, headers=headers)
                with urllib.request.urlopen(img_req, timeout=15) as r_img:
                    raw = r_img.read()
                img = Image.open(io.BytesIO(raw)).convert("RGB")
                # Pastikan ukuran layak & proporsi mendekati buku (atau crop tengah jika square marketplace image)
                if img.width >= 260 and img.height >= 320:
                    # Jika gambar hampir persegi (misal 720x720 dengan latar putih di kiri-kanan), potong tepi putih otomatis
                    img = _trim_white_borders(img)
                    img.save(dest_path, "JPEG", quality=95)
                    print(f"[COVER INTERNET] Berhasil mengunduh cover buku dari: {img_url}")
                    return True
            except Exception:
                continue
    except Exception as e:
        print(f"[COVER INTERNET] Gagal mencari cover di internet: {e}")

    return False


def _trim_white_borders(img: Image.Image) -> Image.Image:
    """Memotong bingkai putih polos di kiri/kanan gambar cover buku hasil internet agar pas proporsi buku."""
    w, h = img.size
    if w < 100 or h < 100:
        return img
    px = img.load()
    left = 0
    while left < w // 3:
        col_vals = [px[left, y] for y in range(0, h, 10)]
        if all(r > 242 and g > 242 and b > 242 for (r, g, b) in col_vals):
            left += 1
        else:
            break
    right = w - 1
    while right > (w * 2) // 3:
        col_vals = [px[right, y] for y in range(0, h, 10)]
        if all(r > 242 and g > 242 and b > 242 for (r, g, b) in col_vals):
            right -= 1
        else:
            break
    top = 0
    while top < h // 4:
        row_vals = [px[x, top] for x in range(0, w, 10)]
        if all(r > 242 and g > 242 and b > 242 for (r, g, b) in row_vals):
            top += 1
        else:
            break
    bottom = h - 1
    while bottom > (h * 3) // 4:
        row_vals = [px[x, bottom] for x in range(0, w, 10)]
        if all(r > 242 and g > 242 and b > 242 for (r, g, b) in row_vals):
            bottom -= 1
        else:
            break

    if right - left > 180 and bottom - top > 240:
        return img.crop((left, top, right + 1, bottom + 1))
    return img


def get_book_cover_image(drive, assets_folder_id: str, filename: str, work_dir: str) -> Optional[str]:
    """
    Mendapatkan file gambar Cover Buku untuk diletakkan di sisi kanan Thumbnail:
    1. Cek apakah sudah ada di cache `00_Assets` Google Drive (`cover_<Mapel>_<Kelas>.jpg`).
    2. Cek apakah buku PDF utuhnya ada di 2 folder Google Drive user (`KNOWN_FULL_BOOK_PDF_IDS` atau pencarian langsung di Drive).
    3. Jika belum ada, cari Cover Buku Siswa resmi di internet.
    4. Simpan hasilnya ke `00_Assets` Google Drive agar video bab-bab berikutnya langsung menggunakan cover yang sama & seragam!
    """
    meta = parse_textbook_metadata(filename)
    subject_code = meta["subject_code"] or "PAIBP"
    subject_full = meta["subject_full"] or subject_code
    kelas = meta["kelas"]

    safe_subj = re.sub(r"[^A-Za-z0-9]+", "_", subject_code)
    cache_name = f"cover_{safe_subj}_{kelas or 'umum'}.jpg"
    local_cover_path = os.path.join(work_dir, cache_name)

    # 1. Cek di cache folder 00_Assets Google Drive
    q_cache = f"name = '{cache_name}' and '{assets_folder_id}' in parents and trashed = false"
    res_cache = drive.files().list(q=q_cache, fields="files(id, name)").execute(num_retries=3)
    cached_files = res_cache.get("files", [])
    if cached_files:
        from googleapiclient.http import MediaIoBaseDownload

        req = drive.files().get_media(fileId=cached_files[0]["id"])
        with io.FileIO(local_cover_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, req)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        if os.path.exists(local_cover_path) and os.path.getsize(local_cover_path) > 2000:
            return local_cover_path

    # 2. Cek di daftar PDF Buku Utuh di 2 Folder Google Drive User
    found = False
    if kelas and (subject_code, kelas) in KNOWN_FULL_BOOK_PDF_IDS:
        pdf_id = KNOWN_FULL_BOOK_PDF_IDS[(subject_code, kelas)]
        found = _download_pdf_cover_from_drive(drive, pdf_id, local_cover_path)

    # 2b. Cari juga secara dinamis di Google Drive jika user menambahkan PDF buku baru
    if not found and subject_code and kelas:
        search_terms = f"name contains '{subject_code}' and name contains '{kelas}' and mimeType = 'application/pdf' and trashed = false"
        try:
            dyn_res = drive.files().list(q=search_terms, fields="files(id, name, thumbnailLink)", pageSize=10).execute(num_retries=3)
            for f in dyn_res.get("files", []):
                # Hindari file potongan per-bab ("Bab 1", dll.) agar yang diambil adalah cover buku utama
                if "bab " not in f["name"].lower():
                    if _download_pdf_cover_from_drive(drive, f["id"], local_cover_path):
                        found = True
                        break
        except Exception:
            pass

    # 3. Jika belum ditemukan di Drive (misal PAIBP Kelas 1-9 yang filenya per-Bab, atau Ushul Fiqh), cari di internet
    if not found:
        found = _search_book_cover_on_internet(subject_code, subject_full, kelas, local_cover_path)

    # 4. Unggah ke cache 00_Assets di Google Drive agar bab-bab berikutnya dari buku yang sama memakai cover yang seragam
    if found and os.path.exists(local_cover_path):
        try:
            media = MediaFileUpload(local_cover_path, mimetype="image/jpeg", resumable=False)
            drive.files().create(
                body={"name": cache_name, "parents": [assets_folder_id]},
                media_body=media,
                fields="id",
            ).execute(num_retries=3)
            print(f"[COVER CACHE] Cover '{cache_name}' disimpan ke Google Drive 00_Assets.")
        except Exception:
            pass
        return local_cover_path

    return None


def determine_target_playlist_titles(filename: str, fallback_ai_playlist: str = "Kajian Keluarga Muslim") -> List[str]:
    """
    Menentukan nama-nama Playlist yang tepat untuk sebuah video berdasarkan Mata Pelajaran & Kelasnya:
    - Untuk PAIBP Kelas 1-6: ["PAI SD Kelas X (K13 & Merdeka)", "PAI SD Kelas X"]
    - Untuk PAIBP Kelas 7-9: ["PAI SMP Kelas X (K13 & Merdeka)", "PAI SMP Kelas X"]
    - Untuk PAIBP Kelas 10-12: ["PAI SMA Kelas X (K13 & Merdeka)"]
    - Untuk Mapel buku lain berkelas (misal Fikih 5, Akidah Akhlak 7, SKI 8, Bahasa Arab 6):
      ["<Mapel> Kelas <Kelas> (K13 & Merdeka)"]
    - Untuk Mapel/Kitab tanpa kelas (misal Ushul Fiqh, Ilmu Mawaris, dll.):
      ["Materi <Mapel>"]
    """
    meta = parse_textbook_metadata(filename)
    subject_code = meta["subject_code"]
    kelas = meta["kelas"]

    if subject_code == "PAIBP" and kelas:
        if 1 <= kelas <= 6:
            return [f"PAI SD Kelas {kelas} (K13 & Merdeka)", f"PAI SD Kelas {kelas}"]
        elif 7 <= kelas <= 9:
            return [f"PAI SMP Kelas {kelas} (K13 & Merdeka)", f"PAI SMP Kelas {kelas}"]
        elif 10 <= kelas <= 12:
            return [f"PAI SMA Kelas {kelas} (K13 & Merdeka)"]

    if subject_code and kelas:
        return [f"{subject_code} Kelas {kelas} (K13 & Merdeka)"]

    if subject_code:
        return [f"Kajian & Materi {subject_code}"]

    return [fallback_ai_playlist or "Kajian Keluarga Muslim"]

