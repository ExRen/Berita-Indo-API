"""
api/index.py — Entry point utama untuk Vercel Serverless
==========================================================
PERBAIKAN v2.1:
- Urutan route diperbaiki: /v1/search/all dipindahkan ke ATAS /v1/{source}
  Ini adalah root cause dari error 404 sebelumnya. FastAPI memproses route
  secara berurutan dari atas ke bawah dan berhenti di kecocokan pertama.
  Jika /v1/{source} ditulis lebih dulu, request ke /v1/search/all akan
  dicocokkan sebagai source="search" (yang tidak ada di SOURCES) → 404.
- vercel.json dikembalikan ke "rewrites" (bukan "builds"+"routes")

Urutan route yang benar:
  1. GET /                    ← info root
  2. GET /health              ← health check
  3. GET /v1/sources/list     ← SPESIFIK: harus sebelum wildcard
  4. GET /v1/search/all       ← SPESIFIK: harus sebelum /v1/{source} ← KUNCI PERBAIKAN
  5. GET /v1/{source}         ← WILDCARD: menangkap source manapun
  6. GET /v1/{source}/{category} ← WILDCARD dua segmen
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

# ─── Cache Setup ──────────────────────────────────────────────────────────────
_cache: TTLCache = TTLCache(maxsize=300, ttl=300)
_cache_lock = threading.Lock()

# ─── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Berita Indonesia API",
    description=(
        "Self-hosted REST API berita Indonesia berbasis RSS feed. "
        "Mendukung 14 media besar dengan pencarian fuzzy keyword.\n\n"
        "**Sumber:** CNN ID · CNBC ID · Detik · Kompas · Tempo · Antara · "
        "Republika · OkeZone · Tribun · Bisnis ID · Sindonews · Merdeka · "
        "Kumparan · Suara"
    ),
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER: Parsing dan Normalisasi RSS
# ─────────────────────────────────────────────────────────────────────────────

def _clean_html(text: str) -> str:
    """Hapus semua tag HTML dari string teks."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _extract_image(entry: dict) -> str | None:
    """
    Coba ambil URL gambar dari berbagai kemungkinan field RSS.
    Urutan pengecekan dari yang paling umum ke yang paling jarang.
    """
    for item in entry.get("media_content", []):
        if item.get("url"):
            return item["url"]

    for enc in entry.get("enclosures", []):
        if enc.get("type", "").startswith("image"):
            return enc.get("url")

    for thumb in entry.get("media_thumbnail", []):
        if thumb.get("url"):
            return thumb["url"]

    raw = entry.get("summary", "") or entry.get("description", "")
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw)
    return match.group(1) if match else None


def _normalize(entry: dict, source_name: str, category: str) -> dict:
    """
    Konversi satu entry feedparser ke format JSON yang seragam.
    Format konsisten ini penting agar MedMon tidak perlu logika
    parsing berbeda untuk tiap media.
    """
    title = _clean_html(entry.get("title", ""))

    raw_summary = (
        entry.get("summary")
        or entry.get("description")
        or (entry.get("content") or [{}])[0].get("value", "")
    )
    snippet = _clean_html(raw_summary)[:300]

    # feedparser menyediakan published_parsed sebagai struct_time Python
    # yang lebih mudah diformat daripada string mentah.
    pub_date = ""
    if entry.get("published_parsed"):
        try:
            pub_date = datetime(*entry["published_parsed"][:6]).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        except Exception:
            pass
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
    Hasil disimpan di TTLCache selama 5 menit untuk mengurangi
    beban ke server media dan mempercepat response.
    """
    cache_key = f"{source_key}:{category}"

    with _cache_lock:
        if cache_key in _cache:
            return _cache[cache_key]

    feed_url = get_feed_url(source_key, category)
    if not feed_url:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Kategori '{category}' tidak ditemukan untuk source '{source_key}'. "
                f"Kategori tersedia: {get_all_categories(source_key)}"
            ),
        )

    source_name = SOURCES[source_key]["name"]

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        }
        resp = httpx.get(
            feed_url, headers=headers, timeout=(5, 20), follow_redirects=True
        )
        resp.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Timeout saat mengambil feed '{source_key}/{category}'.",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Server media mengembalikan HTTP {e.response.status_code}.",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gagal fetch feed: {str(e)}")

    feed = feedparser.parse(resp.text)
    articles = [
        _normalize(entry, source_name, category)
        for entry in feed.entries
        if entry.get("link")
    ]

    with _cache_lock:
        _cache[cache_key] = articles

    return articles


# ─────────────────────────────────────────────────────────────────────────────
#  CORE: Fuzzy Keyword Search
# ─────────────────────────────────────────────────────────────────────────────

def fuzzy_filter(articles: list[dict], query: str, threshold: int = 70) -> list[dict]:
    """
    Filter artikel berdasarkan query dengan tiga strategi bertingkat:
    exact match (skor 100) → fuzzy partial_ratio (skor threshold+).
    Hasil diurutkan dari skor tertinggi ke terendah.
    """
    if not query:
        return articles

    q = query.lower()
    scored = []

    for art in articles:
        text = f"{art.get('title', '')} {art.get('contentSnippet', '')}".lower()

        # Exact match selalu prioritas tertinggi
        if q in text:
            scored.append((art, 100))
            continue

        score = fuzz.partial_ratio(q, text)
        if score >= threshold:
            scored.append((art, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [art for art, _ in scored]


# ─────────────────────────────────────────────────────────────────────────────
#  ENDPOINTS — PERHATIKAN URUTANNYA, INI KUNCI DARI PERBAIKAN
# ─────────────────────────────────────────────────────────────────────────────

# ── 1. Root info ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Info"])
def root():
    """Info API dan daftar semua source. Berguna sebagai health check dasar."""
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
        "version": "2.1.0",
        "docs": "/docs",
        "total_sources": len(SOURCES),
        "sources": sources_info,
    }


# ── 2. Health check ───────────────────────────────────────────────────────────
@app.get("/health", tags=["Info"])
def health():
    """Health check ringan — cukup cek apakah server merespons."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_entries": len(_cache),
    }


# ── 3. Daftar sumber ── HARUS sebelum wildcard /v1/{source} ──────────────────
@app.get("/v1/sources/list", tags=["Info"])
def list_sources():
    """
    Daftar lengkap semua sumber berita beserta kategori yang tersedia.
    Endpoint ini HARUS didefinisikan sebelum /v1/{source} karena jika tidak,
    FastAPI akan mencocokkan /v1/sources/list sebagai source="sources"
    yang tidak ada di SOURCES dict, menghasilkan 404.
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


# ── 4. Pencarian global ── INI YANG PALING KRITIS, HARUS sebelum /v1/{source} ─
@app.get("/v1/search/all", tags=["Pencarian Global"])
def search_all(
    q: str = Query(..., description="Kata kunci pencarian — wajib diisi"),
    sources: str = Query(
        default=None,
        description=(
            "Sumber yang dicari, pisahkan koma. "
            "Contoh: cnn,detik,tempo. Kosongkan untuk semua sumber."
        ),
    ),
    limit: int = Query(default=30, ge=1, le=200, description="Total artikel maksimal"),
    threshold: int = Query(
        default=70, ge=50, le=100,
        description="Sensitivitas fuzzy: 50=longgar, 100=exact only"
    ),
):
    """
    Cari berita dari SEMUA media sekaligus dalam satu request.
    Ini endpoint paling penting untuk MedMon.

    PENTING — mengapa endpoint ini harus di atas /v1/{source}:
    FastAPI memproses route dari atas ke bawah dan berhenti di
    kecocokan pertama. Jika /v1/{source} ada lebih dulu, request ke
    /v1/search/all akan dicocokkan sebagai source="search" → 404.
    Dengan meletakkan endpoint spesifik ini di atas route wildcard,
    FastAPI akan mencocokkannya dengan benar sebelum mencoba wildcard.

    Contoh penggunaan:
    - /v1/search/all?q=PT+ASABRI
    - /v1/search/all?q=korupsi&sources=kompas,tempo,antara
    - /v1/search/all?q=BUMN&limit=50&threshold=80
    """
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

    for key in source_list:
        default_cat = SOURCES[key].get("default_category", "terbaru")
        try:
            articles = fetch_feed(key, default_cat)
            all_articles.extend(articles)
        except HTTPException as e:
            errors.append({"source": key, "error": e.detail})
        except Exception as e:
            errors.append({"source": key, "error": str(e)})

    filtered = fuzzy_filter(all_articles, q, threshold=threshold)

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
    if errors:
        result["warnings"] = errors

    return result


# ── 5. Berita per sumber ── Wildcard, tangkap source manapun ─────────────────
@app.get("/v1/{source}", tags=["Berita per Sumber"])
def get_by_source(
    source: str,
    search: str = Query(default=None, description="Kata kunci pencarian fuzzy"),
    limit: int = Query(default=20, ge=1, le=100, description="Jumlah maksimal artikel"),
    category: str = Query(default=None, description="Nama kategori spesifik"),
):
    """
    Ambil berita terbaru dari satu sumber media.
    Contoh: /v1/cnn, /v1/detik?category=finance, /v1/tempo?search=ASABRI
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


# ── 6. Berita per sumber + kategori ── Wildcard dua segmen ───────────────────
@app.get("/v1/{source}/{category}", tags=["Berita per Kategori"])
def get_by_category(
    source: str,
    category: str,
    search: str = Query(default=None, description="Kata kunci pencarian fuzzy"),
    limit: int = Query(default=20, ge=1, le=100, description="Jumlah maksimal artikel"),
):
    """
    Ambil berita dari kombinasi sumber + kategori spesifik.
    Contoh: /v1/antara/hukum, /v1/bisnis/keuangan?search=BUMN
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
