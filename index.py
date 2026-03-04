"""
api/index.py — Entry point utama untuk Vercel Serverless
==========================================================
Di Vercel, Python ASGI app harus ada di folder `api/` dan
file ini (index.py) akan dipanggil untuk SEMUA request berkat
routing di vercel.json: { "source": "/(.*)", "destination": "/api/index" }

Catatan penting tentang caching di Vercel Serverless:
------------------------------------------------------
Vercel menjalankan setiap fungsi dalam container yang bisa
"dingin" (cold) atau "hangat" (warm). Saat container hangat,
variabel modul (termasuk _cache) tetap hidup di memori dan
TTLCache berfungsi dengan baik. Saat container dingin (baru
dibangunkan setelah idle), cache kosong dan RSS di-fetch ulang.
Ini adalah trade-off yang wajar untuk serverless — tidak ada
solusi sempurna tanpa database eksternal seperti Redis/Upstash.
Untuk MedMon, ini sudah sangat cukup karena request berita
biasanya datang dalam burst (banyak dalam waktu singkat),
sehingga container akan tetap hangat selama sesi scraping.
"""

import re
import threading
from datetime import datetime

import feedparser
import httpx
from cachetools import TTLCache
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from rapidfuzz import fuzz

from feeds_config import SOURCES, get_feed_url, get_all_categories

# ─── Cache Setup ─────────────────────────────────────────────────────────────
# maxsize=300 : simpan maks 300 pasangan source+category sekaligus
# ttl=300     : data kedaluwarsa setelah 5 menit
# Lock diperlukan karena Vercel bisa menjalankan beberapa request
# secara concurrent dalam satu instance yang sama.
_cache: TTLCache = TTLCache(maxsize=300, ttl=300)
_cache_lock = threading.Lock()

# ─── Inisialisasi FastAPI ─────────────────────────────────────────────────────
app = FastAPI(
    title="Berita Indonesia API",
    description=(
        "Self-hosted REST API berita Indonesia berbasis RSS feed. "
        "Mendukung 13 media besar dengan pencarian fuzzy keyword. "
        "Dapat diintegrasikan langsung ke MedMon sebagai sumber berita tambahan.\n\n"
        "**Sumber:** CNN ID · CNBC ID · Detik · Kompas · Tempo · Antara · "
        "Republika · OkeZone · Tribun · Bisnis ID · Sindonews · Merdeka · "
        "Kumparan · Suara"
    ),
    version="2.0.0",
)

# Izinkan akses dari mana saja — wajib agar MedMon (yang mungkin
# berjalan di domain lain) bisa memanggil API ini tanpa error CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER: Parsing dan Normalisasi Data RSS
# ─────────────────────────────────────────────────────────────────────────────

def _clean_html(text: str) -> str:
    """
    Hapus semua tag HTML dari string.
    RSS feed sering menyertakan HTML di dalam field description,
    misalnya <p>teks artikel</p> atau <img src="..."/>.
    """
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _extract_image(entry: dict) -> str | None:
    """
    Coba ambil URL gambar dari berbagai kemungkinan field RSS.
    Setiap media menyimpan gambar di field yang berbeda-beda,
    sehingga kita perlu cek beberapa tempat secara berurutan.
    """
    # media:content — digunakan oleh CNN, Detik, dan banyak media besar
    for item in entry.get("media_content", []):
        if item.get("url"):
            return item["url"]

    # enclosures — format attachment RSS standar
    for enc in entry.get("enclosures", []):
        if enc.get("type", "").startswith("image"):
            return enc.get("url")

    # media:thumbnail — digunakan oleh beberapa feed Google-powered
    for thumb in entry.get("media_thumbnail", []):
        if thumb.get("url"):
            return thumb["url"]

    # Terakhir, coba ekstrak <img src="..."> dari dalam HTML description
    raw = entry.get("summary", "") or entry.get("description", "")
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw)
    return match.group(1) if match else None


def _normalize(entry: dict, source_name: str, category: str) -> dict:
    """
    Konversi satu entry feedparser ke format JSON yang seragam.
    Format yang konsisten ini sangat penting agar MedMon tidak perlu
    menulis logika parsing berbeda untuk tiap media.
    """
    title = _clean_html(entry.get("title", ""))

    # Ambil deskripsi singkat dari berbagai kemungkinan field
    raw_summary = (
        entry.get("summary")
        or entry.get("description")
        or (entry.get("content") or [{}])[0].get("value", "")
    )
    snippet = _clean_html(raw_summary)[:300]

    # Normalisasi tanggal: feedparser menyediakan published_parsed
    # sebagai struct_time Python yang lebih mudah diformat.
    pub_date = ""
    if entry.get("published_parsed"):
        try:
            pub_date = datetime(*entry["published_parsed"][:6]).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except Exception:
            pass
    # Fallback ke string mentah jika struct_time tidak tersedia
    if not pub_date:
        pub_date = entry.get("published", entry.get("updated", ""))

    return {
        "title": title,
        "link": entry.get("link", ""),
        "pubDate": pub_date,
        "contentSnippet": snippet,
        "image": _extract_image(entry),
        "source": source_name,
        "category": category,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  CORE: Fetch RSS dengan Cache
# ─────────────────────────────────────────────────────────────────────────────

def fetch_feed(source_key: str, category: str) -> list[dict]:
    """
    Ambil dan parse RSS feed untuk satu pasangan source+category.

    Alur kerjanya:
    1. Cek cache — jika ada dan belum kedaluwarsa, langsung return
    2. Jika tidak ada di cache, fetch RSS via httpx
    3. Parse XML dengan feedparser
    4. Normalisasi setiap entry ke format seragam
    5. Simpan ke cache sebelum return

    Kenapa pakai httpx bukan langsung feedparser.parse(url)?
    Karena feedparser.parse(url) tidak bisa set custom User-Agent,
    dan beberapa media Indonesia memblokir request tanpa User-Agent
    yang terlihat seperti browser nyata.
    """
    cache_key = f"{source_key}:{category}"

    with _cache_lock:
        if cache_key in _cache:
            return _cache[cache_key]

    feed_url = get_feed_url(source_key, category)
    if not feed_url:
        raise HTTPException(
            status_code=404,
            detail=f"Source '{source_key}' dengan kategori '{category}' tidak ditemukan.",
        )

    source_name = SOURCES[source_key]["name"]

    try:
        headers = {
            # User-Agent yang terlihat seperti browser biasa
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        }
        # timeout=(5, 20): 5 detik untuk connect, 20 detik untuk baca data
        # Ini penting di Vercel karena fungsi serverless punya batas waktu eksekusi.
        resp = httpx.get(feed_url, headers=headers, timeout=(5, 20), follow_redirects=True)
        resp.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Timeout saat mengambil feed '{source_key}/{category}'. Coba lagi.",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Server media mengembalikan HTTP {e.response.status_code}.",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gagal fetch feed: {str(e)}")

    # Parse konten XML yang sudah di-fetch
    feed = feedparser.parse(resp.text)

    articles = [
        _normalize(entry, source_name, category)
        for entry in feed.entries
        if entry.get("link")  # Abaikan entry tanpa URL — tidak bisa dipakai
    ]

    with _cache_lock:
        _cache[cache_key] = articles

    return articles


# ─────────────────────────────────────────────────────────────────────────────
#  CORE: Fuzzy Keyword Search
# ─────────────────────────────────────────────────────────────────────────────

def fuzzy_filter(articles: list[dict], query: str, threshold: int = 70) -> list[dict]:
    """
    Filter daftar artikel berdasarkan query menggunakan fuzzy matching.

    Mengapa fuzzy dan bukan exact match biasa?
    Karena pengguna mungkin ketik "asabri" sementara judul artikel
    menyebutnya "PT ASABRI (Persero)" atau "Asabri Tbk". Exact match
    akan melewatkan semua variasi itu. Dengan partial_ratio dari
    rapidfuzz, kita mencari apakah query ada sebagai substring fuzzy
    di dalam teks yang lebih panjang.

    threshold=70: nilai 0-100. 70 adalah keseimbangan yang baik
    antara "tidak terlalu ketat" dan "tidak terlalu longgar".
    Naikkan ke 85-90 untuk pencarian yang lebih presisi.
    """
    if not query:
        return articles

    q = query.lower()
    scored = []

    for art in articles:
        # Gabungkan judul + snippet sebagai teks yang dicari
        text = f"{art.get('title', '')} {art.get('contentSnippet', '')}".lower()

        # Exact match selalu menang dengan skor 100
        if q in text:
            scored.append((art, 100))
            continue

        # Fuzzy match sebagai jaring pengaman
        score = fuzz.partial_ratio(q, text)
        if score >= threshold:
            scored.append((art, score))

    # Urutkan dari skor tertinggi ke terendah
    scored.sort(key=lambda x: x[1], reverse=True)
    return [art for art, _ in scored]


# ─────────────────────────────────────────────────────────────────────────────
#  ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
def root():
    """
    Halaman info utama. Bisa digunakan sebagai health check — jika
    endpoint ini merespons, berarti API berjalan dengan baik.
    """
    sources_info = {
        key: {
            "name": cfg["name"],
            "categories": list(cfg["feeds"].keys()),
            "sample_endpoint": f"/v1/{key}",
        }
        for key, cfg in SOURCES.items()
    }
    return {
        "status": "ok",
        "message": "Berita Indonesia API — Vercel Edition",
        "version": "2.0.0",
        "docs": "/docs",
        "total_sources": len(SOURCES),
        "sources": sources_info,
    }


@app.get("/health", tags=["Info"])
def health():
    """Health check ringan untuk monitoring uptime."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_entries": len(_cache),
    }


@app.get("/v1/sources/list", tags=["Info"])
def list_sources():
    """
    Daftar lengkap semua sumber berita dan kategori yang tersedia.
    Berguna sebagai referensi sebelum memanggil endpoint spesifik.
    """
    return {
        "status": "ok",
        "total_sources": len(SOURCES),
        "sources": [
            {
                "key": key,
                "name": cfg["name"],
                "default_category": cfg.get("default_category", "terbaru"),
                "categories": list(cfg["feeds"].keys()),
            }
            for key, cfg in SOURCES.items()
        ],
    }


@app.get("/v1/{source}", tags=["Berita per Sumber"])
def get_by_source(
    source: str,
    search: str = Query(default=None, description="Kata kunci pencarian fuzzy pada judul"),
    limit: int = Query(default=20, ge=1, le=100, description="Jumlah maksimal artikel"),
    category: str = Query(default=None, description="Nama kategori spesifik"),
):
    """
    Ambil berita terbaru dari satu sumber media.

    Jika `category` tidak diisi, akan menggunakan kategori default
    sumber tersebut (biasanya 'terbaru' atau 'terkini').

    Contoh penggunaan:
    - `/v1/cnn` → semua berita terbaru CNN Indonesia
    - `/v1/detik?category=finance&limit=10` → 10 berita finance Detik
    - `/v1/tempo?search=ASABRI` → berita Tempo tentang ASABRI
    """
    source = source.lower()
    if source not in SOURCES:
        raise HTTPException(
            status_code=404,
            detail=f"Source '{source}' tidak ditemukan. Tersedia: {list(SOURCES.keys())}",
        )

    cat = (category or SOURCES[source].get("default_category", "terbaru")).lower()
    articles = fetch_feed(source, cat)

    if search:
        articles = fuzzy_filter(articles, search)

    return {
        "status": "ok",
        "source": SOURCES[source]["name"],
        "category": cat,
        "total": len(articles[:limit]),
        "data": articles[:limit],
    }


@app.get("/v1/{source}/{category}", tags=["Berita per Kategori"])
def get_by_category(
    source: str,
    category: str,
    search: str = Query(default=None, description="Kata kunci pencarian fuzzy pada judul"),
    limit: int = Query(default=20, ge=1, le=100, description="Jumlah maksimal artikel"),
):
    """
    Ambil berita dari kombinasi sumber + kategori yang spesifik.

    Contoh:
    - `/v1/antara/hukum` → berita hukum dari Antara
    - `/v1/bisnis/keuangan?search=BUMN&limit=15` → berita keuangan Bisnis ID tentang BUMN
    """
    source = source.lower()
    category = category.lower()

    if source not in SOURCES:
        raise HTTPException(
            status_code=404,
            detail=f"Source '{source}' tidak ditemukan. Tersedia: {list(SOURCES.keys())}",
        )

    articles = fetch_feed(source, category)
    if search:
        articles = fuzzy_filter(articles, search)

    return {
        "status": "ok",
        "source": SOURCES[source]["name"],
        "category": category,
        "total": len(articles[:limit]),
        "data": articles[:limit],
    }


@app.get("/v1/search/all", tags=["Pencarian Global"])
def search_all(
    q: str = Query(..., description="Kata kunci pencarian — wajib diisi"),
    sources: str = Query(
        default=None,
        description=(
            "Sumber yang ingin dicari, pisahkan dengan koma. "
            "Contoh: cnn,detik,tempo. Kosongkan untuk semua sumber."
        ),
    ),
    limit: int = Query(default=30, ge=1, le=200, description="Total artikel maksimal dari semua sumber"),
    threshold: int = Query(
        default=70, ge=50, le=100,
        description="Sensitivitas fuzzy match: 50=longgar, 100=exact only"
    ),
):
    """
    Endpoint paling penting untuk MedMon.

    Mencari berita berdasarkan keyword di SEMUA media sekaligus
    dalam satu request. Hasilnya diurutkan dari yang terbaru.

    Cara kerja di balik layar:
    1. Semua sumber di-fetch secara sekuensial (batasan serverless)
    2. Setiap artikel dicek relevansinya dengan fuzzy matching
    3. Hasil digabungkan dan diurutkan berdasarkan tanggal
    4. Response dikirim dengan informasi sumber dan total

    Contoh penggunaan:
    - `/v1/search/all?q=PT+ASABRI` → cari di semua 13 media
    - `/v1/search/all?q=korupsi&sources=kompas,tempo,antara&limit=50`
    - `/v1/search/all?q=BUMN&threshold=85` → pencarian lebih ketat
    """
    # Tentukan daftar sumber yang akan dicari
    if sources:
        source_list = [s.strip().lower() for s in sources.split(",") if s.strip()]
        invalid = [s for s in source_list if s not in SOURCES]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Source tidak valid: {invalid}. Tersedia: {list(SOURCES.keys())}",
            )
    else:
        source_list = list(SOURCES.keys())

    all_articles: list[dict] = []
    errors: list[dict] = []

    # Fetch dari setiap sumber secara berurutan.
    # Di environment serverless, ThreadPoolExecutor tidak direkomendasikan
    # karena bisa melebihi batas memory/thread. Fetch sekuensial lebih aman
    # dan tetap cukup cepat karena cache mengurangi beban network.
    for key in source_list:
        default_cat = SOURCES[key].get("default_category", "terbaru")
        try:
            articles = fetch_feed(key, default_cat)
            all_articles.extend(articles)
        except HTTPException as e:
            # Satu sumber gagal tidak menghentikan seluruh request
            errors.append({"source": key, "error": e.detail})
        except Exception as e:
            errors.append({"source": key, "error": str(e)})

    # Filter berdasarkan keyword
    filtered = fuzzy_filter(all_articles, q, threshold=threshold)

    # Urutkan berdasarkan tanggal terbaru
    def parse_date(art: dict) -> datetime:
        try:
            return datetime.strptime(art.get("pubDate", ""), "%Y-%m-%d %H:%M:%S")
        except Exception:
            return datetime.min

    filtered.sort(key=parse_date, reverse=True)

    result = {
        "status": "ok",
        "query": q,
        "sources_searched": len(source_list),
        "total": len(filtered[:limit]),
        "data": filtered[:limit],
    }

    # Sertakan peringatan jika ada sumber yang gagal, tapi jangan crash
    if errors:
        result["warnings"] = errors

    return result
