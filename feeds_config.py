"""
feeds_config.py — Konfigurasi RSS Feed Media Indonesia
========================================================
File ini adalah satu-satunya tempat yang perlu diedit jika ingin
menambah media baru atau memperbarui URL RSS yang berubah.
Tidak ada logika di sini, hanya data konfigurasi murni.

Cara menambah media baru:
  1. Cari URL RSS resmi media tersebut (biasanya di footer situs atau /rss)
  2. Tambahkan entry baru di dict SOURCES dengan format yang sama
  3. Deploy ulang — endpoint baru otomatis terbentuk tanpa edit main.py
"""

# Seluruh konfigurasi sumber berita.
# Struktur: { "key_pendek": { "name": "...", "default_category": "...", "feeds": {...} } }
# "key_pendek" inilah yang menjadi URL endpoint, misal key "cnn" → /v1/cnn
SOURCES = {

    # ═══════════════════════════════════════════════════════════════════════
    #  CNN INDONESIA — cnnindonesia.com
    # ═══════════════════════════════════════════════════════════════════════
    "cnn": {
        "name": "CNN Indonesia",
        "default_category": "terbaru",
        "feeds": {
            "terbaru":       "https://www.cnnindonesia.com/rss",
            "nasional":      "https://www.cnnindonesia.com/nasional/rss",
            "internasional": "https://www.cnnindonesia.com/internasional/rss",
            "ekonomi":       "https://www.cnnindonesia.com/ekonomi/rss",
            "olahraga":      "https://www.cnnindonesia.com/olahraga/rss",
            "teknologi":     "https://www.cnnindonesia.com/teknologi/rss",
            "hiburan":       "https://www.cnnindonesia.com/hiburan/rss",
            "gayahidup":     "https://www.cnnindonesia.com/gaya-hidup/rss",
        },
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  CNBC INDONESIA — cnbcindonesia.com
    # ═══════════════════════════════════════════════════════════════════════
    "cnbc": {
        "name": "CNBC Indonesia",
        "default_category": "terbaru",
        "feeds": {
            "terbaru":       "https://www.cnbcindonesia.com/rss",
            "news":          "https://www.cnbcindonesia.com/news/rss",
            "market":        "https://www.cnbcindonesia.com/market/rss",
            "investment":    "https://www.cnbcindonesia.com/investment/rss",
            "entrepreneur":  "https://www.cnbcindonesia.com/entrepreneur/rss",
            "syariah":       "https://www.cnbcindonesia.com/syariah/rss",
            "tech":          "https://www.cnbcindonesia.com/tech/rss",
            "lifestyle":     "https://www.cnbcindonesia.com/lifestyle/rss",
            "opini":         "https://www.cnbcindonesia.com/opini/rss",
        },
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  DETIK — detik.com
    #  Detik adalah media terbesar Indonesia berdasarkan traffic,
    #  menggunakan subdomain terpisah untuk setiap kanal berita.
    # ═══════════════════════════════════════════════════════════════════════
    "detik": {
        "name": "Detik",
        "default_category": "terbaru",
        "feeds": {
            "terbaru":  "https://rss.detik.com/index.php/detikcom",
            "news":     "https://rss.detik.com/index.php/detikNews",
            "finance":  "https://rss.detik.com/index.php/detikFinance",
            "sport":    "https://rss.detik.com/index.php/detikSport",
            "inet":     "https://rss.detik.com/index.php/detikInet",
            "hot":      "https://rss.detik.com/index.php/detikHot",
            "health":   "https://rss.detik.com/index.php/detikHealth",
            "food":     "https://rss.detik.com/index.php/detikFood",
            "oto":      "https://rss.detik.com/index.php/detikOto",
            "travel":   "https://rss.detik.com/index.php/detikTravel",
            "wolipop":  "https://rss.detik.com/index.php/wolipop",
        },
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  KOMPAS — kompas.com
    # ═══════════════════════════════════════════════════════════════════════
    "kompas": {
        "name": "Kompas",
        "default_category": "terbaru",
        "feeds": {
            "terbaru":       "https://rss.kompas.com/rss/news/nasional",
            "nasional":      "https://rss.kompas.com/rss/news/nasional",
            "regional":      "https://rss.kompas.com/rss/news/regional",
            "internasional": "https://rss.kompas.com/rss/news/internasional",
            "money":         "https://rss.kompas.com/rss/money/",
            "olahraga":      "https://rss.kompas.com/rss/bola",
            "tekno":         "https://rss.kompas.com/rss/tekno",
            "properti":      "https://rss.kompas.com/rss/properti",
            "otomotif":      "https://rss.kompas.com/rss/otomotif",
            "lifestyle":     "https://rss.kompas.com/rss/lifestyle",
        },
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  TEMPO — tempo.co
    # ═══════════════════════════════════════════════════════════════════════
    "tempo": {
        "name": "Tempo",
        "default_category": "terbaru",
        "feeds": {
            "terbaru":  "https://rss.tempo.co/",
            "nasional": "https://rss.tempo.co/nasional",
            "bisnis":   "https://rss.tempo.co/bisnis",
            "metro":    "https://rss.tempo.co/metro",
            "dunia":    "https://rss.tempo.co/dunia",
            "bola":     "https://rss.tempo.co/bola",
            "tekno":    "https://rss.tempo.co/tekno",
            "otomotif": "https://rss.tempo.co/otomotif",
            "seleb":    "https://rss.tempo.co/seleb",
            "gaya":     "https://rss.tempo.co/gaya",
            "travel":   "https://rss.tempo.co/travel",
        },
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  ANTARA — antaranews.com
    #  Kantor berita resmi negara — sangat relevan untuk berita BUMN,
    #  kebijakan pemerintah, dan keputusan resmi lembaga negara.
    # ═══════════════════════════════════════════════════════════════════════
    "antara": {
        "name": "Antara News",
        "default_category": "terkini",
        "feeds": {
            "terkini":       "https://www.antaranews.com/rss/terkini.xml",
            "politik":       "https://www.antaranews.com/rss/politik.xml",
            "hukum":         "https://www.antaranews.com/rss/hukum.xml",
            "ekonomi":       "https://www.antaranews.com/rss/ekonomi.xml",
            "olahraga":      "https://www.antaranews.com/rss/olahraga.xml",
            "internasional": "https://www.antaranews.com/rss/internasional.xml",
            "teknologi":     "https://www.antaranews.com/rss/teknologi.xml",
            "humaniora":     "https://www.antaranews.com/rss/humaniora.xml",
        },
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  REPUBLIKA — republika.co.id
    # ═══════════════════════════════════════════════════════════════════════
    "republika": {
        "name": "Republika",
        "default_category": "terbaru",
        "feeds": {
            "terbaru":       "https://www.republika.co.id/rss",
            "nasional":      "https://www.republika.co.id/rss/nasional",
            "internasional": "https://www.republika.co.id/rss/internasional",
            "ekonomi":       "https://www.republika.co.id/rss/ekonomi",
            "olahraga":      "https://www.republika.co.id/rss/olahraga",
            "teknologi":     "https://www.republika.co.id/rss/sci-tech",
            "gaya":          "https://www.republika.co.id/rss/gaya-hidup",
        },
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  OKEZONE — okezone.com
    #  OkeZone menggunakan sistem nomor kode untuk kategorinya
    # ═══════════════════════════════════════════════════════════════════════
    "okezone": {
        "name": "OkeZone",
        "default_category": "terbaru",
        "feeds": {
            "terbaru":   "https://sindikasi.okezone.com/index.php/rss/0/RSS2.0",
            "celebrity": "https://sindikasi.okezone.com/index.php/rss/1/RSS2.0",
            "economy":   "https://sindikasi.okezone.com/index.php/rss/2/RSS2.0",
            "sports":    "https://sindikasi.okezone.com/index.php/rss/6/RSS2.0",
            "techno":    "https://sindikasi.okezone.com/index.php/rss/4/RSS2.0",
            "lifestyle":  "https://sindikasi.okezone.com/index.php/rss/3/RSS2.0",
            "bola":      "https://sindikasi.okezone.com/index.php/rss/5/RSS2.0",
        },
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  TRIBUN — tribunnews.com
    # ═══════════════════════════════════════════════════════════════════════
    "tribun": {
        "name": "Tribun News",
        "default_category": "terbaru",
        "feeds": {
            "terbaru":  "https://www.tribunnews.com/rss",
            "nasional": "https://www.tribunnews.com/rss/nasional",
            "regional": "https://www.tribunnews.com/rss/regional",
            "bisnis":   "https://www.tribunnews.com/rss/bisnis",
            "olahraga": "https://www.tribunnews.com/rss/sport",
            "hiburan":  "https://www.tribunnews.com/rss/seleb",
            "lifestyle": "https://www.tribunnews.com/rss/lifestyle",
            "techno":   "https://www.tribunnews.com/rss/techno",
        },
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  BISNIS INDONESIA — bisnis.com
    #  Media paling komprehensif untuk berita keuangan, pasar modal,
    #  dan BUMN. Sangat relevan untuk MedMon.
    # ═══════════════════════════════════════════════════════════════════════
    "bisnis": {
        "name": "Bisnis Indonesia",
        "default_category": "terbaru",
        "feeds": {
            "terbaru":       "https://rss.bisnis.com/topnews",
            "ekonomi":       "https://rss.bisnis.com/ekonomi-bisnis",
            "keuangan":      "https://rss.bisnis.com/finansial",
            "market":        "https://rss.bisnis.com/pasar-modal",
            "industri":      "https://rss.bisnis.com/industri",
            "teknologi":     "https://rss.bisnis.com/teknologi",
            "internasional": "https://rss.bisnis.com/internasional",
        },
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  SINDONEWS — sindonews.com
    # ═══════════════════════════════════════════════════════════════════════
    "sindonews": {
        "name": "Sindo News",
        "default_category": "terbaru",
        "feeds": {
            "terbaru":       "https://www.sindonews.com/rss/nasional",
            "nasional":      "https://www.sindonews.com/rss/nasional",
            "metro":         "https://www.sindonews.com/rss/metro",
            "ekonomi":       "https://www.sindonews.com/rss/ekbis",
            "internasional": "https://www.sindonews.com/rss/international",
            "olahraga":      "https://www.sindonews.com/rss/sports",
            "tekno":         "https://www.sindonews.com/rss/tekno",
            "edukasi":       "https://www.sindonews.com/rss/edukasi",
        },
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  MERDEKA — merdeka.com
    # ═══════════════════════════════════════════════════════════════════════
    "merdeka": {
        "name": "Merdeka",
        "default_category": "terbaru",
        "feeds": {
            "terbaru":   "https://www.merdeka.com/feed/",
            "dunia":     "https://www.merdeka.com/dunia/rss.xml",
            "olahraga":  "https://www.merdeka.com/olahraga/rss.xml",
            "teknologi": "https://www.merdeka.com/teknologi/rss.xml",
            "sehat":     "https://www.merdeka.com/sehat/rss.xml",
        },
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  KUMPARAN — kumparan.com
    # ═══════════════════════════════════════════════════════════════════════
    "kumparan": {
        "name": "Kumparan",
        "default_category": "terbaru",
        "feeds": {
            "terbaru": "https://kumparan.com/rss",
        },
    },

    # ═══════════════════════════════════════════════════════════════════════
    #  SUARA — suara.com
    # ═══════════════════════════════════════════════════════════════════════
    "suara": {
        "name": "Suara",
        "default_category": "terbaru",
        "feeds": {
            "terbaru":   "https://www.suara.com/rss",
            "bisnis":    "https://www.suara.com/rss/bisnis",
            "bola":      "https://www.suara.com/rss/bola",
            "lifestyle": "https://www.suara.com/rss/lifestyle",
            "tekno":     "https://www.suara.com/rss/tekno",
            "health":    "https://www.suara.com/rss/health",
        },
    },

}


# ─── Helper functions ────────────────────────────────────────────────────────

def get_feed_url(source_key: str, category: str) -> str | None:
    """Ambil URL RSS berdasarkan source key dan nama kategori."""
    src = SOURCES.get(source_key.lower())
    if not src:
        return None
    return src["feeds"].get(category.lower())


def get_all_categories(source_key: str) -> list[str]:
    """Daftar kategori yang tersedia untuk satu source."""
    return list(SOURCES.get(source_key.lower(), {}).get("feeds", {}).keys())
