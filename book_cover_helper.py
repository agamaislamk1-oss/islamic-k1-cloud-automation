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

# Daftar Mapel & Normalisasi Kode Judul (Mendukung PAI/Madrasah & Seluruh Cabang Pelajaran Umum)
SUBJECT_PATTERNS = [
    (r"\bpai\s*k13\b", "PAI K13", "Pendidikan Agama Islam K13"),
    (r"\bpaibp\b", "PAIBP", "Pendidikan Agama Islam dan Budi Pekerti"),
    (r"\b(?:pai|pendidikan\s+agama\s+islam)\b", "PAI", "Pendidikan Agama Islam dan Budi Pekerti"),
    (r"\bushul\s*fiq[ih]*\b", "Ushul Fiqh", "Ushul Fiqh"),
    (r"\bfi(?:k|q)ih\b", "Fikih", "Fikih Kemenag"),
    (r"\ba[kq]idah\s*akhlak\b", "Akidah Akhlak", "Akidah Akhlak Kemenag"),
    (r"\b(?:al[-\s]*qur'?an\s*hadit?s?t?|qh)\b", "Al-Quran Hadis", "Al-Qur'an Hadis Kemenag"),
    (r"\b(?:ski|sejarah\s+kebudayaan\s+islam)\b", "SKI", "Sejarah Kebudayaan Islam Kemenag"),
    (r"\bbahasa\s+arab\b", "Bahasa Arab", "Bahasa Arab Kemenag"),
    (r"\bbahasa\s+indonesia\b", "Bahasa Indonesia", "Bahasa Indonesia Kurikulum Merdeka"),
    (r"\bbahasa\s+inggris\b", "Bahasa Inggris", "Bahasa Inggris Kurikulum Merdeka"),
    (r"\b(?:pendidikan\s+pancasila|ppkn|pkn)\b", "Pendidikan Pancasila", "Pendidikan Pancasila Kurikulum Merdeka"),
    (r"\bipas\b", "IPAS", "IPAS Kurikulum Merdeka"),
    (r"\bipa\b", "IPA", "Ilmu Pengetahuan Alam Kurikulum Merdeka"),
    (r"\bips\b", "IPS", "Ilmu Pengetahuan Sosial Kurikulum Merdeka"),
    (r"\b(?:matematika|mtk)\b", "Matematika", "Matematika Kurikulum Merdeka"),
    (r"\binformatika\b", "Informatika", "Informatika Kurikulum Merdeka"),
    (r"\b(?:pjok|penjaskes)\b", "PJOK", "PJOK Kurikulum Merdeka"),
    (r"\bseni\s+(?:budaya|rupa|musik|teater|tari)\b", "Seni Budaya", "Seni Budaya Kurikulum Merdeka"),
    (r"\bprakarya\b", "Prakarya", "Prakarya Kurikulum Merdeka"),
    (r"\bfisika\b", "Fisika", "Fisika Kurikulum Merdeka"),
    (r"\bbiologi\b", "Biologi", "Biologi Kurikulum Merdeka"),
    (r"\bkimia\b", "Kimia", "Kimia Kurikulum Merdeka"),
    (r"\bekonomi\b", "Ekonomi", "Ekonomi Kurikulum Merdeka"),
    (r"\bgeografi\b", "Geografi", "Geografi Kurikulum Merdeka"),
    (r"\bsosiologi\b", "Sosiologi", "Sosiologi Kurikulum Merdeka"),
]

# Kamus Topik Resmi untuk File Video Pembelajaran yang Nama Filenya Hanya Berisi "<Mapel> <Kelas> Bab <N>.mp4" Tanpa Judul Bab
KNOWN_TEXTBOOK_CHAPTER_TOPICS: Dict[Tuple[str, int, int], str] = {
    ("Al-Quran Hadis", 12, 1): "Hidup Sederhana dan Menyantuni Duafa",
    ("Al-Quran Hadis", 12, 2): "Sabar Menghadapi Ujian dan Cobaan",
    ("Al-Quran Hadis", 12, 3): "Melestarikan Lingkungan Hidup",
    ("Al-Quran Hadis", 12, 4): "Seni Dakwah Penuh Hikmah",
    ("Al-Quran Hadis", 12, 5): "Amar Makruf Nahi Munkar",
    ("Al-Quran Hadis", 12, 6): "Musyawarah dan Kepemimpinan Bijak dalam Islam",
    ("Al-Quran Hadis", 12, 7): "Jujur dan Adil Itu Hebat",
    ("SKI", 5, 1): "Upaya Nabi Muhammad Saw. dalam Membina Masyarakat Madinah",
    ("SKI", 5, 2): "Perjanjian Hudaibiyah dan Strategi Damai Rasulullah Saw.",
    ("SKI", 5, 3): "Jejak Dakwah dan Fathu Makkah",
    ("SKI", 5, 4): "Pembersihan Ka'bah dan Fathu Makkah",
    ("SKI", 5, 5): "Pesan Terakhir Rasulullah Saw. di Haji Wada",
    ("SKI", 5, 6): "Kisah Teladan Khalifah Abu Bakar Ash-Shiddiq",
    ("SKI", 5, 7): "Kisah Teladan Khalifah Umar bin Khattab",
    ("SKI", 5, 8): "Kisah Teladan Khalifah Utsman bin Affan",
    ("SKI", 5, 9): "Kisah Teladan Khalifah Ali bin Abi Thalib",
}

# Kamus Pelengkap Judul Fashal/Bab Kajian Kitab yang Terpotong di Nama File Asli
KNOWN_KITAB_FASHAL_COMPLETIONS: Dict[Tuple[str, int], Tuple[str, str]] = {
    ("bidayatul hidayah", 1): ("Muqaddimah", "Basmalah & Hamdalah"),
    ("bidayatul hidayah", 2): ("Muqaddimah", "Bahaya Niat Duniawi"),
    ("bidayatul hidayah", 3): ("Muqaddimah", "Keutamaan Menuntut Ilmu"),
    ("bidayatul hidayah", 4): ("Muqaddimah", "Tipu Daya Setan"),
    ("bidayatul hidayah", 5): ("Muqaddimah", "Tiga Golongan Penuntut Ilmu"),
    ("bidayatul hidayah", 6): ("Muqaddimah", "Permulaan Hidayah & Takwa"),
    ("bidayatul hidayah", 7): ("Adab Ketaatan", "Muraqabah Allah Swt"),
    ("bidayatul hidayah", 8): ("Adab Ketaatan", "Adab Bangun Tidur"),
    ("fathul qarib", 1): ("Muqaddimah", "Basmalah"),
    ("fathul qarib", 2): ("Muqaddimah", "Hamdalah"),
    ("fathul qarib", 3): ("Muqaddimah", "Shalawat"),
    ("fathul qarib", 4): ("Muqaddimah", "Tujuan Penulisan Kitab"),
    ("fathul qarib", 5): ("Muqaddimah", "Pembuka Kitab"),
    ("fathul qarib", 6): ("Muqaddimah", "Latar Belakang Kitab"),
    ("fathul qarib", 7): ("Muqaddimah", "Penutup Muqaddimah"),
    ("ahkamith thaharah", 8): ("Macam-Macam Air", ""),
    ("ahkamith thaharah", 9): ("Benda Bernajis", ""),
    ("ahkamith thaharah", 10): ("Bejana dan Peralatan", ""),
    ("ahkamith thaharah", 11): ("Bersiwak", "Hukum & Tata Cara Siwak"),
    ("ahkamith thaharah", 12): ("Wudhu", "Fardhu Wudhu"),
    ("ahkamith thaharah", 13): ("Wudhu", "Sunnah Wudhu"),
    ("ahkamith thaharah", 14): ("Istinja", "Adab & Tata Cara Istinja"),
    ("ahkamith thaharah", 15): ("Pembatal Wudhu", ""),
    ("ahkamith thaharah", 16): ("Mandi Wajib", "Hal yang Mewajibkan Mandi"),
}

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


def parse_kitab_metadata(filename: str, raw_title: str = "") -> Optional[Dict[str, Any]]:
    """
    Mendeteksi dan mengekstrak struktur Kajian Kitab Islami dari nama file atau judul:
    Format standar yang diminta:
    `Bagian Ke (N) - Kitab (X), Bab (Y) - Fashal (Z)` (atau menyesuaikan jika tanpa Fashal / memakai Hadits/Pasal/Maqolah).
    Mendukung berbagai kitab Islami (Bidayatul Hidayah, Fathul Qarib, Ahkamith Thaharah, Riyadhus Shalihin,
    Safinatun Najah, Ta'limul Muta'allim, Al-Hikam, Nashoihul Ibad, Bulughul Maram, Fathul Mu'in, dll.).
    """
    base = os.path.splitext(filename)[0].strip()
    # Hapus akhiran (1), (2), copy
    base = re.sub(r"\s*\(\d+\)\s*$", "", base).strip()
    # Ubah underscore menjadi spasi namun pertahankan pemisah tanda hubung " - "
    base_clean = base.replace("_-_", " - ").replace("_", " ")
    base_clean = re.sub(r"\s+", " ", base_clean).strip()

    combined_probe = f"{base_clean} {raw_title}".lower()
    # Pastikan ini memang video Kajian Kitab (bukan buku paket sekolah PAI/SD/SMP/SMA tentang "Iman kepada Kitab-Kitab Allah")
    if "kitab-kitab allah" in combined_probe or "kitab suci" in combined_probe or "beriman kepada kitab" in combined_probe:
        return None

    has_kitab_keyword = bool(
        re.search(
            r"\b(?:kitab|syarah|bidayatul\s+hidayah|fathul\s+q[ao]rib|ahkamith\s+thaharah|tafsir\s+al[-\s]*munir|mawlid|maulid|barzanji|ja[uw]haratut\s+tauhid|mukhtarul\s+ahadit?s|sh?afwatuz\s+zubad|riyadh?us\s+shalihin|safinatun\s+najah|ta'?lim(?:ul)?\s+muta'?allim|bulughul\s+maram|nashoihul\s+ibad|al[-\s]*hikam|fathul\s+mu'?in|arbain\s+nawawi)\b",
            combined_probe,
            flags=re.IGNORECASE,
        )
    )
    if not has_kitab_keyword:
        return None

    # Jangan tangkap jika merupakan buku pelajaran madrasah berkelas (misal PAIBP 8, Akidah Akhlak 3, Al-Qur'an Hadis 10)
    if re.search(
        r"\b(?:pai|paibp|fikih|fiqih|akidah\s*akhlak|al[-\s]*qur'?an\s*hadit?s?t?|ski|bahasa\s+arab|ipas?|matematika)\s*(?:k13\s*)?\d{1,2}\b",
        base_clean,
        flags=re.IGNORECASE,
    ):
        return None

    # 1. Ekstrak nomor Bagian
    bagian_num: Optional[int] = None
    m_bag = re.search(r"\b(?:bagian|part|episode|ep|kajian)\s*(?:ke[-\s]*)?(\d{1,3})\b", base_clean, flags=re.IGNORECASE)
    if m_bag:
        bagian_num = int(m_bag.group(1))

    # 2. Ekstrak nama Kitab
    kitab_name = ""
    m_kitab = re.search(
        r"\bkitab\s+([A-Za-z0-9\s'’\-]+?)(?=\s*[-,:]?\s*\b(?:bab|fash?al|fasal|hadit?s|pasal|maqolah|hikmah|bagian|bait|nadzom)\b|$)",
        base_clean,
        flags=re.IGNORECASE,
    )
    if m_kitab:
        kitab_name = m_kitab.group(1).strip(" -,:.")
    else:
        for known_k in [
            "Bidayatul Hidayah",
            "Fathul Qarib",
            "Ahkamith Thaharah",
            "Tafsir Al-Munir",
            "Mawlid Al-Barzanji",
            "Jauharatut Tauhid",
            "Mukhtarul Ahadits",
            "Shafwatuz Zubad",
            "Riyadhus Shalihin",
            "Safinatun Najah",
            "Ta'limul Muta'allim",
            "Bulughul Maram",
            "Nashoihul Ibad",
            "Al-Hikam",
            "Fathul Mu'in",
            "Arba'in Nawawi",
        ]:
            if known_k.lower() in combined_probe:
                kitab_name = known_k
                break

    if not kitab_name:
        return None

    # Normalisasi kapitalisasi nama Kitab
    kitab_title = kitab_name.title().replace("Al-", "Al-").replace("Qorib", "Qarib")
    kitab_key = kitab_title.lower()

    # 3. Ekstrak Bab dan Fashal / Sub-bagian
    bab_name = ""
    fashal_label = "Fashal"
    fashal_name = ""

    m_bab = re.search(
        r"\bbab\s+([A-Za-z0-9\s'’\-]+?)(?=\s*[-,:]?\s*\b(?:fash?al|fasal|hadit?s|pasal|maqolah|hikmah)\b|$)",
        base_clean,
        flags=re.IGNORECASE,
    )
    if m_bab:
        bab_name = m_bab.group(1).strip(" -,:.")

    m_fashal = re.search(
        r"\b(fash?al|fasal|hadit?s|pasal|maqolah|hikmah)\b\s*[:\-]?\s*(.*)$",
        base_clean,
        flags=re.IGNORECASE,
    )
    if m_fashal:
        raw_lbl = m_fashal.group(1).strip().lower()
        if raw_lbl.startswith("had"):
            fashal_label = "Hadits"
        elif raw_lbl.startswith("pas"):
            fashal_label = "Pasal"
        elif raw_lbl.startswith("maq"):
            fashal_label = "Maqolah"
        elif raw_lbl.startswith("hik"):
            fashal_label = "Hikmah"
        else:
            fashal_label = "Fashal"
        fashal_name = m_fashal.group(2).strip(" -,:.")

    # 4. Cek di kamus pelengkap jika Bab / Fashal di nama file terpotong (misal "Fashal_Ba", "Fashal_Ke", dll.)
    if bagian_num and (kitab_key, bagian_num) in KNOWN_KITAB_FASHAL_COMPLETIONS:
        known_bab, known_fashal = KNOWN_KITAB_FASHAL_COMPLETIONS[(kitab_key, bagian_num)]
        if known_bab:
            bab_name = known_bab
        if known_fashal:
            fashal_name = known_fashal
        elif not known_fashal:
            fashal_name = ""
            m_fashal = None

    # Jika untuk kitab baru di masa depan kata terakhir Fashal kosong atau terpotong (<= 3 huruf), lengkapi dari raw_title AI
    if m_fashal and (not fashal_name or len(fashal_name.split()[-1]) <= 2):
        cleaned_ai = re.sub(r"\s*#shorts\b.*$", "", raw_title, flags=re.IGNORECASE)
        cleaned_ai = re.sub(r"\s*[\|I]\s*.*$", "", cleaned_ai).strip()
        cleaned_ai = re.sub(
            rf"(?i)^.*?(?:{re.escape(kitab_title)}|muqaddimah|mukaddimah)\s*[:\-–,]?\s*",
            "",
            cleaned_ai,
        ).strip()
        if cleaned_ai and len(cleaned_ai) >= 5 and "bagian " not in cleaned_ai.lower():
            fashal_name = cleaned_ai[:45].strip(" -,:.")

    return {
        "bagian": bagian_num,
        "kitab": kitab_title,
        "bab": bab_name,
        "fashal_label": fashal_label,
        "fashal": fashal_name,
        "has_fashal": bool(fashal_name),
    }


# Kamus Pelengkap Nama File Asli yang Terpotong pada 24 Upload Awal (384..418)
EARLY_TRUNCATED_KITAB_TITLES: Dict[Tuple[str, int], str] = {
    ("bidayatul hidayah", 1): "Bagian 1, Kitab Bidayatul Hidayah, Bab Muqaddimah, Fashal Basmalah & Hamdalah",
    ("bidayatul hidayah", 2): "Bagian 2, Kitab Bidayatul Hidayah, Bab Muqaddimah, Fashal Bahaya Niat Duniawi",
    ("bidayatul hidayah", 3): "Bagian 3, Kitab Bidayatul Hidayah, Bab Muqaddimah, Fashal Keutamaan Menuntut Ilmu",
    ("bidayatul hidayah", 4): "Bagian 4, Kitab Bidayatul Hidayah, Bab Muqaddimah, Fashal Tipu Daya Setan",
    ("bidayatul hidayah", 6): "Bagian 6, Kitab Bidayatul Hidayah, Bab Muqaddimah, Fashal Permulaan Hidayah & Takwa",
    ("bidayatul hidayah", 7): "Bagian 7, Kitab Bidayatul Hidayah, Bab Adab Melaksanakan Ketaatan, Fashal Muraqabah Allah Swt",
    ("bidayatul hidayah", 8): "Bagian 8, Kitab Bidayatul Hidayah, Bab Adab Melaksanakan Ketaatan, Fashal Adab Bangun Tidur",
    ("fathul qarib", 1): "Bagian 1, Kitab Fathul Qarib, Bab Muqaddimah, Fashal Basmalah",
    ("fathul qarib", 2): "Bagian 2, Kitab Fathul Qarib, Bab Muqaddimah, Fashal Hamdalah",
    ("fathul qarib", 3): "Bagian 3, Kitab Fathul Qarib, Bab Muqaddimah, Fashal Shalawat",
    ("fathul qarib", 4): "Bagian 4, Kitab Fathul Qarib, Bab Muqaddimah, Fashal Tujuan Penulisan Kitab",
    ("fathul qarib", 5): "Bagian 5, Kitab Fathul Qarib, Bab Muqaddimah, Fashal Pembuka Kitab",
    ("fathul qarib", 6): "Bagian 6, Kitab Fathul Qarib, Bab Muqaddimah, Fashal Latar Belakang Kitab",
    ("fathul qarib", 7): "Bagian 7, Kitab Fathul Qarib, Bab Muqaddimah, Fashal Penutup Muqaddimah",
    ("ahkamith thaharah", 8): "Bagian 8, Kitab Fathul Qarib, Bab Thaharah, Fashal Macam-Macam Air",
    ("ahkamith thaharah", 9): "Bagian 9, Kitab Fathul Qarib, Bab Thaharah, Fashal Benda Bernajis",
    ("ahkamith thaharah", 10): "Bagian 10, Kitab Fathul Qarib, Bab Thaharah, Fashal Bejana dan Peralatan",
    ("ahkamith thaharah", 11): "Bagian 11, Kitab Fathul Qarib, Bab Thaharah, Fashal Hukum & Tata Cara Siwak",
    ("ahkamith thaharah", 12): "Bagian 12, Kitab Fathul Qarib, Bab Thaharah, Fashal Fardhu Wudhu",
    ("ahkamith thaharah", 13): "Bagian 13, Kitab Fathul Qarib, Bab Thaharah, Fashal Sunnah Wudhu",
    ("ahkamith thaharah", 14): "Bagian 14, Kitab Fathul Qarib, Bab Thaharah, Fashal Adab & Tata Cara Istinja",
    ("ahkamith thaharah", 15): "Bagian 15, Kitab Fathul Qarib, Bab Thaharah, Fashal Pembatal Wudhu",
    ("ahkamith thaharah", 16): "Bagian 16, Kitab Fathul Qarib, Bab Thaharah, Fashal Perkara yang Mewajibkan Mandi",
}


def is_already_valid_kitab_title(title: str) -> bool:
    """
    Mengecek apakah judul di YouTube SUDAH diubah manual oleh pengguna (atau sudah sesuai aturan penamaan kitab):
    - Diawali dengan 'Bagian <Angka>' atau 'Bagian Ke <Angka>'
    - Mengandung kata 'Kitab '
    - Tidak mengandung sisa nama file mentah seperti '(1)', '(2)', '| Kajian & Materi'
    - Tidak berakhir dengan kata terpotong ('Fashal Ba', 'Fashal Ke', 'Fashal Ti', 'Fashal Pe', '- Fashal', 'Melaksanakan Keta')
    Jika sudah sesuai, sistem TIDAK AKAN mengubahnya lagi!
    """
    t = re.sub(r"\s*#shorts\b.*$", "", (title or "").strip(), flags=re.IGNORECASE).strip()
    if not re.match(r"^Bagian\s+(?:Ke[-\s]*)?\d{1,3}\b", t, flags=re.IGNORECASE):
        return False
    if "kitab " not in t.lower():
        return False
    if re.search(r"\(\d+\)|\|\s*Kajian\s*&\s*Materi", t, flags=re.IGNORECASE):
        return False
    if re.search(
        r"(?:Fashal\s+(?:Ba|Ke|Ti|Pe|Tujuan|Pembuka|Penutup)|Melaksanakan(?:\s+Keta)?|[-,]\s*Fashal)\s*$",
        t,
        flags=re.IGNORECASE,
    ):
        return False
    return True


def format_kitab_youtube_title(raw_title: str, filename: str, is_shorts: bool = False) -> Optional[str]:
    """
    Menyusun Judul Video Kajian Kitab sesuai instruksi pengguna:
    1. Jika judul saat ini (`raw_title`) sudah diubah pengguna dan sesuai aturan (`Bagian ... Kitab ...`),
       JANGAN diubah lagi!
    2. Jika belum sesuai, gunakan PERSIS nama file yang diupload (`filename`) tanpa diubah oleh AI
       (hanya membersihkan ekstensi file, angka duplikat `(1)`/`(2)`, serta melengkapi 24 file awal yang namanya sempat terpotong).
    """
    kmeta = parse_kitab_metadata(filename, raw_title)
    if not kmeta:
        return None

    # 1. Jika judul sudah diubah oleh pengguna dan sudah sesuai aturan, jangan diubah lagi!
    if is_already_valid_kitab_title(raw_title):
        clean_existing = raw_title.strip()
        if (is_shorts or "#shorts" in raw_title.lower()) and "#shorts" not in clean_existing.lower():
            max_len = 91
            if len(clean_existing) > max_len:
                clean_existing = clean_existing[:max_len].rsplit(" ", 1)[0].rstrip(",-:")
            return f"{clean_existing} #Shorts"
        return clean_existing[:100]

    # 2. Gunakan nama file yang diupload pengguna apa adanya
    base = os.path.splitext(filename)[0].strip()
    base = re.sub(r"\s*\(\d+\)\s*$", "", base).strip()
    base_clean = base.replace("_-_", " - ").replace("__", " ").replace("_", " ")
    base_clean = re.sub(r"\s+", " ", base_clean).strip(" -.")

    kitab_key = str(kmeta.get("kitab", "")).lower()
    bagian_num = kmeta.get("bagian")

    # Cek apakah merupakan salah satu dari 24 file upload awal yang nama filenya memakai underscore & terpotong (atau Ahkamith Thaharah)
    is_early_truncated = (
        "_" in base
        or "ahkamith thaharah" in base_clean.lower()
        or re.search(r"(?:Fashal\s+(?:Ba|Ke|Ti|Pe)|Melaksanakan(?:\s+Keta)?|[-,]\s*Fashal)\s*$", base_clean, flags=re.IGNORECASE)
    )
    if is_early_truncated and bagian_num and (kitab_key, bagian_num) in EARLY_TRUNCATED_KITAB_TITLES:
        full_kitab_title = EARLY_TRUNCATED_KITAB_TITLES[(kitab_key, bagian_num)]
    else:
        full_kitab_title = base_clean

    max_allowed = 91 if (is_shorts or "#shorts" in raw_title.lower()) else 100

    # Jika nama file sedikit melebihi batas 100 karakter YouTube (misal 101-112 karakter),
    # padatkan pemisah " - " menjadi ", " dan " dan " menjadi " & " agar kalimat tetap 100% UTUH tanpa terpotong!
    if len(full_kitab_title) > max_allowed:
        compact_try = full_kitab_title.replace(" - ", ", ")
        if len(compact_try) > max_allowed:
            compact_try = re.sub(r"\s+dan\s+", " & ", compact_try, flags=re.IGNORECASE)
        full_kitab_title = compact_try

    if len(full_kitab_title) > max_allowed:
        # Pertahankan keterangan "(Bait ...)" atau "Bagian 1/2" jika ada di ujung
        m_tail_bait = re.search(r"(\((?:Bait|Hadits)\s*[\d\-–]+\))\s*$", full_kitab_title, flags=re.IGNORECASE)
        m_tail_bag = re.search(r"\b(Bagian\s+\d+)\s*\([^)]*\)\s*$", full_kitab_title, flags=re.IGNORECASE)
        if m_tail_bag:
            prefix_part = full_kitab_title[: m_tail_bag.start()].strip(" ,-:")
            candidate_bag = f"{prefix_part} {m_tail_bag.group(1)}"
            if len(candidate_bag) <= max_allowed:
                full_kitab_title = candidate_bag
        elif m_tail_bait:
            bait_str = m_tail_bait.group(1)
            avail = max_allowed - len(bait_str) - 1
            head_cut = full_kitab_title[:avail].rsplit(" ", 1)[0].rstrip(" ,-:(")
            while re.search(
                r"\s+(?:dan|&|dengan|setiap|dua|dari|untuk|yang|di|ke|pada|dalam|atau|serta|bagi|wa|min)\s*$",
                head_cut,
                flags=re.IGNORECASE,
            ):
                head_cut = head_cut.rsplit(" ", 1)[0].rstrip(" ,-:(")
            full_kitab_title = f"{head_cut} {bait_str}"

    if len(full_kitab_title) > max_allowed:
        full_kitab_title = full_kitab_title[:max_allowed].rsplit(" ", 1)[0].rstrip(" ,-:(")
        # Jangan pernah biarkan judul berakhir dengan kata sambung menggantung ("dan", "&", "dengan", "wa", "min", dll.)
        while re.search(
            r"\s+(?:dan|&|dengan|setiap|dua|wa|min|dari|untuk|yang|di|ke|pada|dalam|atau|serta|bagi|bagian|tamma|aradallahu|zhahara|baraza|indallahi)\s*$",
            full_kitab_title,
            flags=re.IGNORECASE,
        ):
            full_kitab_title = full_kitab_title.rsplit(" ", 1)[0].rstrip(" ,-:(")

    if is_shorts or "#shorts" in raw_title.lower():
        return f"{full_kitab_title} #Shorts"
    return full_kitab_title


def determine_kitab_schedule_weekday(filename: str, raw_title: str = "") -> Optional[Tuple[int, str, Optional[int]]]:
    """
    Menentukan hari tayang mingguan khusus (pukul 18.30 WIB) untuk Seri Kajian Kitab:
    - Senin (weekday=0, 18.30 WIB)  : Kitab Bidayatul Hidayah / Tasawuf / Akhlak / Adab
    - Selasa (weekday=1, 18.30 WIB) : Kitab Fathul Qarib / Ahkamith Thaharah / Fikih
    - Rabu (weekday=2, 18.30 WIB)   : Kitab Tafsir al-Munir / Al-Qur'an / Tafsir
    - Kamis (weekday=3, 18.30 WIB)  : Kitab Mawlid al-Barzanji / Sirah / Sejarah / Maulid
    - Jum'at (weekday=4, 18.30 WIB) : Kitab Jauharatut Tauhid / Tauhid / Aqidah
    Mengembalikan tuple (weekday_int_0_to_4, slot_key_str, bagian_num) atau None jika bukan video Kajian Kitab.
    """
    kmeta = parse_kitab_metadata(filename, raw_title)
    if not kmeta:
        return None

    kitab_low = str(kmeta.get("kitab", "")).lower()
    bab_low = str(kmeta.get("bab", "")).lower()
    fashal_low = str(kmeta.get("fashal", "")).lower()
    bagian_num = kmeta.get("bagian")
    blob = f"{filename} {raw_title} {kitab_low} {bab_low} {fashal_low}".lower()

    # 1. Senin (0): Kitab Bidayatul Hidayah / Tasawuf / Akhlak / Adab
    if any(
        k in blob
        for k in (
            "bidayatul hidayah",
            "tasawuf",
            "tasawwuf",
            "ta'lim",
            "talim",
            "muta'allim",
            "mutaallim",
            "al-hikam",
            "nashoihul ibad",
            "minhajul abidin",
            "ihya",
            "riyadhus shalihin",
            "riyadus shalihin",
            "akhlaq",
            "washoya",
        )
    ):
        return (0, "SENIN_TASAWUF_AKHLak", bagian_num)

    # 2. Selasa (1): Kitab Fathul Qarib / Ahkamith Thaharah / Shafwatuz Zubad / Fikih
    if any(
        k in blob
        for k in (
            "fathul qarib",
            "fathul qorib",
            "ahkamith thaharah",
            "shafwatuz zubad",
            "safwatuz zubad",
            "zubad",
            "safinatun najah",
            "fathul mu'in",
            "fathul muin",
            "taqrib",
            "abu syuja",
            "sulamut taufiq",
            "bulughul maram",
            "kifayatul akhyar",
            "mabadi",
            "fikih",
            "fiqih",
            "thaharah",
            "wudhu",
            "shalat",
            "zakat",
        )
    ):
        return (1, "SELASA_FIKIH", bagian_num)

    # 3. Rabu (2): Kitab Tafsir al-Munir / tentang Al-Qur'an
    if any(
        k in blob
        for k in (
            "tafsir al-munir",
            "tafsir munir",
            "al-munir",
            "tafsir",
            "jalalain",
            "ibnu katsir",
            "at-tibyan",
            "tuhfatul athfal",
            "jazariyah",
            "ulumul qur",
            "al-qur'an",
            "al-quran",
            "alquran",
        )
    ):
        return (2, "RABU_TAFSIR_QURAN", bagian_num)

    # 4. Kamis (3): Kitab Mawlid al-Barzanji / tentang Sirah / Sejarah
    if any(
        k in blob
        for k in (
            "barzanji",
            "al-barzanji",
            "mawlid",
            "maulid",
            "sirah",
            "sejarah",
            "nurul yaqin",
            "khulashoh",
            "diba",
            "simthud durar",
            "burdah",
            "syamail",
            "rahiqul makhtum",
            "tarikh",
        )
    ):
        return (3, "KAMIS_SIRAH_SEJARAH", bagian_num)

    # 5. Jum'at (4): Kitab Jauharatut Tauhid / tentang Tauhid / Aqidah
    if any(
        k in blob
        for k in (
            "jauharatut tauhid",
            "jawharatut tauhid",
            "jauharah tauhid",
            "tauhid",
            "aqidah",
            "akidah",
            "aqidatul awam",
            "kifayatul awam",
            "tijan",
            "sanusiyah",
            "ummul barahin",
            "qathrul ghaits",
        )
    ):
        return (4, "JUMAT_TAUHID_AQIDAH", bagian_num)

    # 6. Sabtu (5): Kitab Mukhtarul Ahadits / Hadits Pilihan
    if any(
        k in blob
        for k in (
            "mukhtarul ahadits",
            "mukhtarul ahadis",
            "arbain nawawi",
            "arba'in nawawi",
        )
    ):
        return (5, "SABTU_HADITS", bagian_num)

    # Default untuk kajian kitab adab/umum lainnya -> Senin 18.30 WIB
    return (0, "SENIN_TASAWUF_AKHLak", bagian_num)


def parse_muawiyah_episode(filename: str, raw_title: str = "") -> Optional[int]:
    """
    Mendeteksi apakah video merupakan bagian dari Seri 'Muawiyah Ibn Abi Sufyan'
    dan mengekstrak nomor episode/bagiannya (1 s/d 30) agar dapat dijadwalkan
    secara berurutan setiap hari selama bulan Ramadhan pukul 05.30 WIB.
    Contoh yang didukung:
    - 'Muawiyah S01E01.mp4' -> 1
    - 'Muawiyah S01E14.mp4' -> 14
    - 'Muawiyah Ibn Abi Sufyan 08.mp4' -> 8
    - 'Muawiyah ibn Abi Sufyan 12.mp4' -> 12
    """
    base = os.path.splitext(filename)[0].strip()
    base = re.sub(r"\s*\(\d+\)\s*$", "", base).strip()
    probe = f"{base} {raw_title}".lower()
    if "muawiyah" not in probe and "mu'awiyah" not in probe:
        return None
    # Pastikan bukan buku paket sekolah berkelas (misal SKI Kelas 7 Bab ...)
    if re.search(r"\b(?:ski|pai|paibp|fikih|akidah|al-qur'?an)\s*(?:kelas\s*)?\d{1,2}\b.*?\bbab\s*\d{1,2}\b", probe):
        return None

    # 1. Pola S01E01 / S1E14
    m_se = re.search(r"\bs\d{1,2}\s*e(\d{1,2})\b", probe, flags=re.IGNORECASE)
    if m_se:
        return max(1, min(30, int(m_se.group(1))))

    # 2. Pola angka setelah nama Muawiyah / Abi Sufyan di nama file
    m_fn = re.search(
        r"(?:mu'?awiyah(?:\s+(?:ibn|bin)\s+abi\s+sufyan)?)\s*(?:bagian|part|episode|ep|seri|ke)?\s*[-_:\s]*(\d{1,2})\b",
        base,
        flags=re.IGNORECASE,
    )
    if m_fn:
        return max(1, min(30, int(m_fn.group(1))))

    # 3. Pola Episode / Bagian / Part di judul
    m_ep = re.search(r"\b(?:episode|ep|bagian|part)\s*(?:ke[-\s]*)?(\d{1,2})\b", probe, flags=re.IGNORECASE)
    if m_ep:
        return max(1, min(30, int(m_ep.group(1))))

    return 1



def _clean_special_underscore_tokens(text: str) -> str:
    """Membersihkan urutan underscore khusus dari nama file agar kembali menjadi tanda baca & apostrof Islami yang rapi."""
    s = text
    s = s.replace("___", " & ")
    s = re.sub(r"(?i)\bAl-Qur_an\b", "Al-Qur'an", s)
    s = re.sub(r"(?i)\bAl-_Alaq\b", "Al-'Alaq", s)
    s = re.sub(r"(?i)\bAl-_A[şs]r\b", "Al-'Asr", s)
    s = re.sub(r"(?i)\bAl-_Adiyat\b", "Al-'Adiyat", s)
    s = re.sub(r"(?i)\bAl-Ma_un\b", "Al-Ma'un", s)
    s = re.sub(r"(?i)\bAl-Qari_ah\b", "Al-Qari'ah", s)
    s = re.sub(r"(?i)\bAl-Mu_min\b", "Al-Mu'min", s)
    s = re.sub(r"(?i)\bAl-Asma_Al-Husna\b", "Al-Asma' Al-Husna", s)
    s = re.sub(r"(?i)\bWadi_ah\b", "Wadi'ah", s)
    s = re.sub(r"(?i)\bIsra__Mikraj\b", "Isra' Mi'raj", s)
    s = re.sub(r"(?i)\bIzh[aā]r_dan_Ikhf[aā]_\b", "Izhar dan Ikhfa'", s)
    s = re.sub(r"(?i)\bIdg[aā]m\b", "Idgham", s)
    s = re.sub(r"(?i)\bIql[aā]b\b", "Iqlab", s)
    s = re.sub(r"(?i)\bSwt_\b", "Swt.", s)
    s = s.replace("__", ": ")
    s = re.sub(r"_+", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" -_.")
    return s


def parse_textbook_metadata(filename: str) -> Dict[str, Any]:
    """
    Mengekstrak informasi Mata Pelajaran, Kelas, Jenjang (Madrasah Ibtidaiyah / Madrasah Tsanawiyah / Madrasah Aliyah / Kelas X),
    Bab, Topik Bersih dari nama file saat diupload, dan Akhiran Judul Seragam.
    Contoh sesuai instruksi pengguna:
    - "Al-Quran Hadis 12 MA Bab 7. Jujur dan Adil Itu Hebat.mp4"
      -> clean_topic: "Jujur dan Adil Itu Hebat",
         uniform_suffix: "I Al-Quran Hadis 12 Madrasah Aliyah I Bab 7"
    - "PAI K13 1 Bab 2. Aku Cinta Al-Qur'an.mp4"
      -> clean_topic: "Aku Cinta Al-Qur'an",
         uniform_suffix: "I PAI K13 Kelas 1 I Bab 2"
    """
    raw_base = os.path.splitext(filename)[0].strip()
    base = _clean_special_underscore_tokens(raw_base)

    subject_code = None
    subject_full = None
    for pattern, code, full_name in SUBJECT_PATTERNS:
        if re.search(pattern, base, flags=re.IGNORECASE):
            subject_code = code
            subject_full = full_name
            break

    kelas_num: Optional[int] = None
    bab_num: Optional[int] = None

    m_kb = re.search(
        r"(?:kelas|kls|pai\s*k13|pai|paibp|fikih|fiqih|ushul\s*fiq[ih]*|a[kq]idah\s*akhlak|al[-\s]*qur'?an\s*hadit?s?t?|qh|ski|sejarah\s+kebudayaan\s+islam|bahasa\s+arab|bahasa\s+indonesia|bahasa\s+inggris|pendidikan\s+pancasila|ppkn|pkn|ipas?|ips|matematika|mtk|informatika|pjok|penjaskes|seni\s+budaya|prakarya|fisika|biologi|kimia|ekonomi|geografi|sosiologi)\s*(?:sd|mi|smp|mts|sma|ma|smk|kelas|kls)?\s*(\d{1,2})\b.*?\bbab\s*(\d{1,2})\b",
        base,
        flags=re.IGNORECASE,
    )
    if m_kb:
        kelas_num = int(m_kb.group(1))
        bab_num = int(m_kb.group(2))
    else:
        m_k = re.search(
            r"\b(?:kelas|kls|pai\s*k13|pai|paibp|fikih|fiqih|a[kq]idah\s*akhlak|al[-\s]*qur'?an\s*hadit?s?t?|ski|bahasa\s+arab|bahasa\s+indonesia|bahasa\s+inggris|pendidikan\s+pancasila|ppkn|ipas?|ips|matematika|mtk|informatika|pjok|fisika|biologi|kimia|ekonomi|geografi|sosiologi)\s*(?:sd|mi|smp|mts|sma|ma|smk|kelas|kls)?\s*(\d{1,2})\b",
            base,
            flags=re.IGNORECASE,
        )
        if m_k:
            kelas_num = int(m_k.group(1))
        m_b = re.search(r"\bbab\s*(\d{1,2})\b", base, flags=re.IGNORECASE)
        if m_b:
            bab_num = int(m_b.group(1))

    if not subject_code:
        m_generic = re.match(
            r"^([A-Za-z\s\-']+?)\s+(?:Kelas\s+)?(\d{1,2})\s*(?:SD|MI|SMP|MTs|SMA|MA|SMK)?\s*[-\.]*\s*Bab\s*(\d{1,2})\b",
            base,
            flags=re.IGNORECASE,
        )
        if m_generic and "bagian" not in m_generic.group(1).lower() and "kitab" not in m_generic.group(1).lower():
            subject_code = m_generic.group(1).strip().title()
            subject_full = subject_code
            kelas_num = int(m_generic.group(2))
            bab_num = int(m_generic.group(3))

    # Deteksi jenjang Madrasah / Sekolah pada nama file sebelum kata "Bab"
    header_part = re.split(r"\bbab\s*\d{1,2}\b", base, maxsplit=1, flags=re.IGNORECASE)[0]
    jenjang_full = ""
    if re.search(r"\b(?:MI|Madrasah\s+Ibtidaiyah)\b", header_part, flags=re.IGNORECASE):
        jenjang_full = "Madrasah Ibtidaiyah"
    elif re.search(r"\b(?:MTs|Madrasah\s+Tsanawiyah)\b", header_part, flags=re.IGNORECASE):
        jenjang_full = "Madrasah Tsanawiyah"
    elif re.search(r"\b(?:MA|Madrasah\s+Aliyah)\b", header_part, flags=re.IGNORECASE):
        jenjang_full = "Madrasah Aliyah"

    # Ekstrak topik yang tertulis setelah "Bab <N>" pada nama file
    has_filename_topic = False
    clean_topic = ""
    if re.search(r"\bbab\s*\d{1,2}\b", base, flags=re.IGNORECASE):
        after_bab = re.sub(
            r"^.*?\bbab\s*\d{1,2}\s*[\.\-:|I]*\s*",
            "",
            base,
            count=1,
            flags=re.IGNORECASE,
        ).strip()
        # Bersihkan jika setelah Bab masih ada sisa akhiran "I Mapel..."
        after_bab = re.sub(r"\s+I\s+(?:PAI|PAIBP|Fikih|Akidah|Al-Qur'?an|SKI).*$", "", after_bab, flags=re.IGNORECASE).strip()
        if after_bab and len(after_bab) >= 3:
            clean_topic = after_bab
            has_filename_topic = True

    if not clean_topic and subject_code and kelas_num and bab_num:
        lookup_subj = "Al-Quran Hadis" if "qur" in subject_code.lower() else subject_code
        if (lookup_subj, kelas_num, bab_num) in KNOWN_TEXTBOOK_CHAPTER_TOPICS:
            clean_topic = KNOWN_TEXTBOOK_CHAPTER_TOPICS[(lookup_subj, kelas_num, bab_num)]
            has_filename_topic = True

    if not clean_topic:
        clean_topic = base

    # Susun akhiran judul seragam sesuai contoh pengguna:
    # - Jika ada MI/MTs/MA: "I Al-Quran Hadis 12 Madrasah Aliyah I Bab 7"
    # - Jika tanpa MI/MTs/MA: "I PAI K13 Kelas 1 I Bab 2" atau "I PAI Kelas 6 I Bab 9"
    if subject_code and kelas_num and bab_num:
        if jenjang_full:
            uniform_suffix = f"I {subject_code} {kelas_num} {jenjang_full} I Bab {bab_num}"
        else:
            uniform_suffix = f"I {subject_code} Kelas {kelas_num} I Bab {bab_num}"
        badge_text = f"{subject_code.upper()} {kelas_num} • BAB {bab_num}"
    elif subject_code and kelas_num:
        if jenjang_full:
            uniform_suffix = f"I {subject_code} {kelas_num} {jenjang_full}"
        else:
            uniform_suffix = f"I {subject_code} Kelas {kelas_num}"
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
        "jenjang_full": jenjang_full,
        "bab": bab_num,
        "clean_topic": clean_topic,
        "has_filename_topic": has_filename_topic,
        "uniform_suffix": uniform_suffix,
        "badge_text": badge_text,
    }


def has_uniform_textbook_suffix(title: str) -> bool:
    """Mengecek apakah judul video sudah memiliki akhiran standar `I <Mapel> <Kelas/Jenjang> I Bab <N>`."""
    return bool(
        re.search(
            r"\bI\s+[A-Za-z0-9\s'\-]+?(?:Kelas\s+\d{1,2}|\d{1,2}\s+Madrasah\s+(?:Ibtidaiyah|Tsanawiyah|Aliyah))\s+I\s+Bab\s+\d{1,2}\s*(?:#Shorts)?\s*$",
            title.strip(),
        )
    )


def format_uniform_youtube_title(raw_title: str, filename: str, is_shorts: bool = False) -> str:
    """
    Memastikan Judul YouTube mematuhi aturan penamaan resmi channel Islamic K1:
    1. Jika video Kajian Kitab -> `Bagian Ke (N) - Kitab (X), Bab (Y) - Fashal (Z)`
    2. Jika video Materi Pelajaran (PAI/PAIBP, PAI K13, Al-Quran Hadis, Akidah Akhlak, Fikih, SKI, Bahasa Indonesia, IPAS, Matematika, dll.)
       -> Menggunakan judul topik yang diberikan pada nama file ketika diupload:
          * Contoh 1: `Al-Quran Hadis 12 MA Bab 7. Jujur dan Adil Itu Hebat`
            -> `Jujur dan Adil Itu Hebat I Al-Quran Hadis 12 Madrasah Aliyah I Bab 7`
          * Contoh 2: `PAI K13 1 Bab 2. Aku Cinta Al-Qur'an`
            -> `Aku Cinta Al-Qur'an I PAI K13 Kelas 1 I Bab 2`
    """
    # 1. Cek apakah video Kajian Kitab
    kitab_title = format_kitab_youtube_title(raw_title, filename, is_shorts=is_shorts)
    if kitab_title:
        return kitab_title

    # 2. Cek apakah merupakan Materi Pelajaran dari filename (atau dari raw_title jika filename tidak lengkap)
    meta = parse_textbook_metadata(filename)
    if not meta["uniform_suffix"]:
        meta = parse_textbook_metadata(raw_title)
    suffix = meta["uniform_suffix"]
    if not suffix:
        return raw_title[:100]

    has_shorts_tag = is_shorts or ("#shorts" in raw_title.lower())

    # Sesuai instruksi Poin 7: Gunakan langsung judul topik dari nama file yang diberikan pengguna saat diupload!
    if meta.get("has_filename_topic") and meta.get("clean_topic"):
        cleaned = meta["clean_topic"].strip()
    else:
        cleaned = re.sub(r"\s*#shorts\b.*$", "", raw_title.strip(), flags=re.IGNORECASE).strip()
        cleaned = re.sub(
            r"\s*[\|I]\s*(?:PAI|PAIBP|Fikih|Fiqih|Akidah\s*Akhlak|Al[-\s]*Qur'?an\s*Hadit?s?t?|SKI|Bahasa\s*Arab|Bahasa\s*Indonesia|IPAS?|Matematika|Islamic\s*K1|Materi\s*PAI|Kajian\s*&\s*Mater).*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
        cleaned = re.sub(
            r"^(?:PAI\s*K13|PAI|PAIBP|Fikih|Fiqih|Akidah\s*Akhlak|Al[-\s]*Qur'?an\s*Hadit?s?t?|SKI)\s*(?:Kelas\s*)?\d+\s*(?:SD|MI|SMP|MTs|SMA|MA)?\s*Bab\s*\d+\s*[:\-\.]\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
        if not cleaned or len(cleaned) < 4:
            cleaned = meta["clean_topic"].strip()

    full_suffix = f"{suffix} #Shorts" if has_shorts_tag else suffix
    max_topic_len = 100 - len(full_suffix) - 1
    if len(cleaned) > max_topic_len:
        # Jika topik memiliki penjelasan tambahan dalam kurung (...), ringkas bagian kurungnya terlebih dahulu
        no_paren = re.sub(r"\s*\([^)]*\)\s*", " ", cleaned).strip()
        if len(no_paren) >= 8 and len(no_paren) <= max_topic_len:
            cleaned = no_paren
        else:
            cleaned = cleaned[:max_topic_len].rsplit(" ", 1)[0].rstrip(":,-|(")

    return f"{cleaned} {full_suffix}"


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
    Menentukan nama-nama Playlist yang tepat untuk sebuah video berdasarkan Mata Pelajaran, Kelas, atau Kajian Kitabnya:
    - Untuk Kajian Kitab (misal Bidayatul Hidayah, Fathul Qarib, Ahkamith Thaharah, Riyadhus Shalihin, dll.):
      ["Kajian Kitab <Nama Kitab>"]
    - Untuk PAIBP Kelas 1-6: ["PAI SD Kelas X (K13 & Merdeka)", "PAI SD Kelas X"]
    - Untuk PAIBP Kelas 7-9: ["PAI SMP Kelas X (K13 & Merdeka)", "PAI SMP Kelas X"]
    - Untuk PAIBP Kelas 10-12: ["PAI SMA Kelas X (K13 & Merdeka)"]
    - Untuk Mapel buku lain berkelas (misal Fikih 5, Akidah Akhlak 7, SKI 8, Bahasa Arab 6, Bahasa Indonesia 4, IPAS 5, Matematika 6):
      ["<Mapel> Kelas <Kelas> (K13 & Merdeka)"]
    - Untuk Mapel tanpa kelas (misal Ushul Fiqh, Ilmu Mawaris, dll.):
      ["Kajian & Materi <Mapel>"]
    """
    kmeta = parse_kitab_metadata(filename)
    if kmeta and kmeta.get("kitab"):
        return [f"Kajian Kitab {kmeta['kitab']}"]

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

