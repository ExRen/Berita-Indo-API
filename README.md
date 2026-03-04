# Berita Indonesia API — Vercel Edition

REST API berita Indonesia self-hosted yang bisa di-deploy gratis ke Vercel.
Membaca RSS feed langsung dari 13 media besar Indonesia dan menyajikannya
dalam format JSON yang konsisten, lengkap dengan pencarian fuzzy keyword.

---

## Struktur File

```
berita-api/
├── api/
│   ├── index.py          ← FastAPI app (entry point Vercel)
│   └── feeds_config.py   ← Konfigurasi semua RSS feed
├── requirements.txt      ← Dependencies Python
├── vercel.json           ← Routing config untuk Vercel
└── README.md
```

Vercel akan otomatis mendeteksi `api/index.py` sebagai serverless function
dan `vercel.json` sebagai panduan routing-nya.

---

## Cara Deploy ke Vercel

### Prasyarat
- Akun Vercel gratis di vercel.com
- Vercel CLI: `npm install -g vercel`
- Git (opsional, untuk deploy via GitHub)

### Metode 1 — Deploy via CLI (Paling Cepat)

```bash
# 1. Masuk ke folder proyek
cd berita-api

# 2. Login ke Vercel (sekali saja)
vercel login

# 3. Deploy!
vercel --prod
```

Vercel akan bertanya beberapa pertanyaan saat pertama kali:
- "Set up and deploy?" → Y
- "Which scope?" → pilih akun pribadi Anda
- "Link to existing project?" → N (buat baru)
- "Project name?" → bebas, misal: berita-indonesia-api
- "Directory?" → ./ (folder saat ini)
- "Override settings?" → N

Setelah selesai, Vercel akan memberikan URL seperti:
`https://berita-indonesia-api.vercel.app`

### Metode 2 — Deploy via GitHub (Direkomendasikan untuk Production)

```bash
# 1. Buat repository GitHub baru, lalu push kode
git init
git add .
git commit -m "Initial deploy Berita Indonesia API"
git remote add origin https://github.com/username/berita-api.git
git push -u origin main

# 2. Buka vercel.com → "Add New Project" → import dari GitHub
# 3. Pilih repository berita-api
# 4. Klik Deploy — selesai!
```

Keuntungan metode GitHub: setiap kali Anda push commit baru
(misal update URL RSS), Vercel otomatis re-deploy tanpa perlu
menjalankan perintah apapun.

---

## Sumber Berita yang Tersedia

| Key | Media | Kategori Tersedia |
|-----|-------|-------------------|
| `cnn` | CNN Indonesia | terbaru, nasional, internasional, ekonomi, olahraga, teknologi, hiburan |
| `cnbc` | CNBC Indonesia | terbaru, news, market, investment, entrepreneur, syariah, tech |
| `detik` | Detik | terbaru, news, finance, sport, inet, hot, health, food, oto, travel |
| `kompas` | Kompas | terbaru, nasional, regional, internasional, money, olahraga, tekno |
| `tempo` | Tempo | terbaru, nasional, bisnis, metro, dunia, bola, tekno, otomotif |
| `antara` | Antara News | terkini, politik, hukum, ekonomi, olahraga, internasional, teknologi |
| `republika` | Republika | terbaru, nasional, internasional, ekonomi, olahraga, teknologi |
| `okezone` | OkeZone | terbaru, celebrity, economy, sports, techno, lifestyle, bola |
| `tribun` | Tribun News | terbaru, nasional, regional, bisnis, olahraga, hiburan |
| `bisnis` | Bisnis Indonesia | terbaru, ekonomi, keuangan, market, industri, teknologi |
| `sindonews` | Sindo News | terbaru, nasional, metro, ekonomi, internasional, olahraga |
| `merdeka` | Merdeka | terbaru, dunia, olahraga, teknologi, sehat |
| `kumparan` | Kumparan | terbaru |
| `suara` | Suara | terbaru, bisnis, bola, lifestyle, tekno, health |

---

## Dokumentasi API

Setelah deploy, buka: `https://url-anda.vercel.app/docs`
Swagger UI interaktif — semua endpoint bisa dicoba langsung dari browser.

### Endpoint Utama

**`GET /v1/{source}`** — Berita terbaru dari satu media.
```
GET /v1/cnn
GET /v1/detik?search=ASABRI&limit=10
GET /v1/tempo?category=bisnis
```

**`GET /v1/{source}/{category}`** — Berita dari kategori spesifik.
```
GET /v1/antara/hukum
GET /v1/bisnis/keuangan?search=BUMN
```

**`GET /v1/search/all`** — ⭐ Paling penting untuk MedMon.
Mencari di SEMUA media sekaligus dengan satu request.
```
GET /v1/search/all?q=PT+ASABRI
GET /v1/search/all?q=korupsi&sources=kompas,tempo,antara
GET /v1/search/all?q=BUMN&limit=50&threshold=80
```

Parameter `/v1/search/all`:
- `q` *(wajib)*: kata kunci pencarian
- `sources`: media yang dicari, pisahkan koma. Kosong = semua.
- `limit`: jumlah artikel maksimal (default 30, maks 200)
- `threshold`: sensitivitas 50–100 (default 70, makin tinggi makin ketat)

**`GET /v1/sources/list`** — Daftar semua sumber dan kategori.

**`GET /health`** — Health check server.

### Contoh Response

```json
{
    "status": "ok",
    "query": "PT ASABRI",
    "sources_searched": 13,
    "total": 8,
    "data": [
        {
            "title": "PT ASABRI Raih Penghargaan Kinerja Terbaik 2024",
            "link": "https://www.bisnis.com/...",
            "pubDate": "2025-01-15 10:30:00",
            "contentSnippet": "PT ASABRI (Persero) berhasil meraih penghargaan...",
            "image": "https://cdn.bisnis.com/gambar.jpg",
            "source": "Bisnis Indonesia",
            "category": "terbaru"
        }
    ]
}
```

---

## Integrasi ke MedMon (medmon.py)

Setelah API Anda live di Vercel, tambahkan fungsi ini ke `medmon.py`:

```python
import requests

# Ganti dengan URL Vercel Anda setelah deploy
BERITA_API_BASE = "https://berita-indonesia-api.vercel.app"

def scrape_berita_indo_api(keyword: str, max_results: int = 20) -> list:
    """Ambil berita dari Berita Indonesia API (self-hosted di Vercel)."""
    try:
        resp = requests.get(
            f"{BERITA_API_BASE}/v1/search/all",
            params={
                "q": keyword,
                "limit": max_results,
                "threshold": 70
            },
            timeout=25  # Agak panjang karena serverless bisa cold start
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("data", []):
            results.append({
                "title": item["title"],
                "url": item["link"],
                "published date": item["pubDate"],
                "publisher": {"title": item["source"]},
                "description": item["contentSnippet"],
                "source_type": "berita_indo_api",
            })
        return results

    except Exception as e:
        print(f"   [!] Berita Indo API error: {e}")
        return []
```

Kemudian di fungsi `scrape_all_sources()`, tambahkan satu baris:

```python
future_beritaindo = executor.submit(scrape_berita_indo_api, keyword, max_results)
```

---

## Menambah Media Baru

Cukup edit `api/feeds_config.py`, tambahkan entry di dict `SOURCES`:

```python
"mediabaru": {
    "name": "Nama Media Baru",
    "default_category": "terbaru",
    "feeds": {
        "terbaru": "https://mediabaru.com/rss",
        "ekonomi": "https://mediabaru.com/rss/ekonomi",
    },
},
```

Push ke GitHub → Vercel auto-deploy → endpoint `/v1/mediabaru` langsung tersedia.

---

## Catatan Penting tentang Vercel Free Plan

Vercel Free Plan memberikan:
- 100GB bandwidth/bulan
- Fungsi berjalan maks 10 detik per request
- Tidak ada batas jumlah deploy

Untuk penggunaan MedMon yang tidak terus-menerus (scraping on-demand),
Free Plan sudah sangat lebih dari cukup.

Satu hal yang perlu diperhatikan: karena ini serverless, "cold start"
bisa terjadi jika API tidak dipanggil selama beberapa menit. Request
pertama setelah cold start mungkin butuh 2–4 detik lebih lama dari biasanya.
Untuk itu, timeout di `scrape_berita_indo_api()` sudah diset 25 detik.
