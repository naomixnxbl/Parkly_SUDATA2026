# Parkly — Sydney parking, live

**SUDATA × COMM-STEM Hackathon · Theme 3 — Improving Transportation in NSW**

Parkly tells you whether you'll find a parking spot *before* you leave. Every spot gets a green / yellow / red status, backed by a three-tier confidence model that makes data provenance visible. Real user accounts, real bookings, real data from Transport for NSW.

---

## What's inside

```
Parkly_SUDATA2026/
├── parkly.html                  ← open in browser (the full UI)
├── proxy.py                     ← Terminal 1: relays TfNSW live API
├── backend.py                   ← Terminal 2: user accounts + bookings (Flask + SQLite)
├── requirements.txt             ← Python deps for backend
├── Procfile                     ← for cloud deployment
├── parknride_pois.csv           ← 33 Park & Ride locations (TfNSW static dataset)
├── offstreetparkingdata_7.csv   ← Off-street parking slots in Sydney CBD 
├── parkly.db                    ← created automatically on first run of backend.py
└── README.md                    ← you are here

```

---

## Three-tier confidence model

| Tier | Data source | Confidence | Shown as |
|---|---|---|---|
| **Tracked** | TfNSW Car Park API — live bay counts | 95% | Solid coloured dot |
| **Derived** | Park'nPay ticket data (simulated in demo) | 75% | Ringed dot |
| **Predicted** | Heuristic model — hour × day × weather × event | 50% | Hollow dot |

Every spot on the map carries a visible confidence marker. No other parking app is honest about this.

---

## Datasets used

Four public NSW datasets form the backbone of Parkly:

### 1. TfNSW Car Park API (live)
- **Source:** `https://api.transport.nsw.gov.au/v1/carpark`
- **What it provides:** Real-time bay occupancy for ~23 commuter Park & Rides across Sydney — updated every ~60 seconds
- **How we use it:** Powers the *tracked live* tier. Polled every 60s for 12 active facilities (Gordon, Hornsby, Dee Why, Narrabeen, Mona Vale, Warriewood, Revesby, Sutherland, Leppington, Edmondson Park, West Ryde, Manly Vale)
- **Link:** [opendata.transport.nsw.gov.au/data/dataset/car-park-api](https://opendata.transport.nsw.gov.au/data/dataset/car-park-api)

### 2. Transport Park&Ride Car Park Locations (static)
- **File:** `parknride_pois.csv` (bundled)
- **What it provides:** 33 Park & Ride sites across NSW with TSN, suburb, precise lat/lng
- **How we use it:** Maps live API facility IDs → real coordinates + names. Lets us group facilities into regional destination clusters (Northern Beaches, Hills, Western Sydney, etc.)
- **Link:** [opendata.transport.nsw.gov.au/data/dataset/transport-parkride-car-park-locations](https://opendata.transport.nsw.gov.au/data/dataset/transport-parkride-car-park-locations)

### 3. City of Sydney Off-Street Parking (static, embedded)
- **Source:** City of Sydney via TfNSW Open Data Hub — "Off-Street Parking" dataset
- **What it provides:** 76 commercial parking garages across the Sydney CBD with capacity, operator, address, coordinates. Total: **21,438 bays**
- **How we use it:** Populates the CBD destination with real Wilson (40 lots), Secure (25 lots), InterPark, Metro Parking, and hotel/venue car parks. Availability is predicted (no live feed exists for commercial lots), but every location, name, capacity, and coordinate is from the official source
- **Link:** [opendata.transport.nsw.gov.au/data/dataset/off-street-parking](https://opendata.transport.nsw.gov.au/data/dataset/off-street-parking)

---

## Quick start

### Prerequisites
- Python 3.8+ installed
- TfNSW Open Data API key (free — register at [opendata.transport.nsw.gov.au](https://opendata.transport.nsw.gov.au))

### Step 1 — Install backend dependencies (first time only)
```bash
pip install -r requirements.txt
```
This installs Flask + Flask-CORS.

### Step 2 — Add your TfNSW API key to proxy.py
Open `proxy.py`, find line 25:
```python
API_KEY = os.environ.get('TFNSW_API_KEY', 'YOUR_KEY_HERE')
```
Replace `YOUR_KEY_HERE` with your key, OR set an environment variable:
```bash
setx TFNSW_API_KEY "your_actual_key_here"     # Windows
export TFNSW_API_KEY="your_actual_key_here"   # macOS / Linux
```

### Step 3 — Start both servers (two terminals)

**Terminal 1 — TfNSW proxy:**
```bash
python proxy.py
```
Should print: `▶ Parkly proxy running on http://localhost:8787`

**Terminal 2 — User accounts + bookings backend:**
```bash
python backend.py
```
Should print: `▶ Parkly backend running on http://localhost:8788`

Both need to stay running.

### Step 4 — Open the app
Double-click `parkly.html` (or open with your browser). The top banner should go green:
```
✓ TfNSW live · N/12 facilities · via proxy
```

---

## How the architecture works

```
┌────────────────────┐
│    parkly.html     │ ← the full UI (Leaflet map + ranked list)
│     (browser)      │
└───────┬────────────┘
        │
        ├──── TfNSW live data ────┐
        │                          │
        │                          ▼
        │              ┌───────────────────────┐      ┌──────────────────────┐
        │              │   proxy.py            │─────►│  TfNSW Car Park API  │
        │              │   localhost:8787      │      │  (HTTPS + apikey)    │
        │              │   adds CORS + auth    │      └──────────────────────┘
        │              └───────────────────────┘
        │
        └──── Auth + bookings ────┐
                                   ▼
                    ┌──────────────────────────┐
                    │   backend.py (Flask)     │
                    │   localhost:8788         │──► parkly.db (SQLite)
                    │                          │      ├─ users
                    │   /signup  /login        │      ├─ sessions
                    │   /reserve /bookings     │      └─ bookings
                    │   /bookings/:id/extend   │
                    └──────────────────────────┘
```

**Why three processes?**
- `parkly.html` is static — runs in the browser, no server needed for the UI
- `proxy.py` exists because TfNSW's API blocks browser-origin calls (no CORS headers). Our proxy adds them and keeps the API key server-side so it never leaks to the client
- `backend.py` holds real user accounts, hashed passwords, and booking records in SQLite so data persists across browser refreshes

---

## Scoring algorithm

Every spot gets a composite score combining six factors:

```
Score = availability × 35%
      + commute time × 20%
      + walk distance × 20%
      + price × 15%
      + confidence bonus (+10 for tracked, +7 for derived)
      − busy flag penalty (−8 if historically busy at this hour)
```

Top-scoring spot surfaces as the hero recommendation. Top 8 shown in the sidebar. All spots pinned on the map.

---

## Features

**Map**
- Every parking location pinned across Sydney (40+ in CBD alone)
- Colour-coded by traffic-light status
- Visual confidence encoding (solid / ringed / hollow dots)
- Map view persists when you refresh — only auto-fits when you change destination

**Ranked list (top 8)**
- Sidebar shows the best 8 spots for your destination
- Live tracking updates every 60 seconds
- Click any row → map zooms to that spot

**Controls**
- 9 destination clusters across Sydney
- Arrival hour slider (0–23)
- Day of week (7 chips)
- Weather (sunny / cloudy / rainy)
- Major event toggle (affects CBD + SCG demand)
- Premium toggle (shows Parkly Plus discounted rates)

**Accounts & bookings**
- Sign up / sign in with email + password (stored hashed in SQLite)
- Reserve a bay → creates a real booking with a unique ID (e.g. `PKL-3F7A2C`)
- Booking management modal — see all your active + past bookings
- Extend active booking by 1 hour (price recalculated server-side)
- Cancel active booking
- Live countdown timer on each active booking ("N min left")

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Banner: `TfNSW unreachable` | Is `proxy.py` running? Did you paste your API key? |
| Banner: `No facilities returned` | Likely the key is invalid — rotate it at opendata.transport.nsw.gov.au |
| Sign in: `Failed to fetch` | `backend.py` isn't running — start it in a second terminal |
| `pip install` errors | Try `pip install --user flask flask-cors` |
| Port 8787 in use | Edit `proxy.py` line 26 (`PORT = 8787`) and the `PROXY_URL` in `parkly.html` |
| Port 8788 in use | Edit `backend.py` bottom (`port = 8788`) and the `BACKEND_URL` in `parkly.html` |
| `parkly.db` corrupted | Just delete it — will be recreated on next backend.py run |

---

## Hackathon judging criteria coverage

| Criterion | How Parkly delivers |
|---|---|
| **Product Design** | Single-screen map + list + controls · traffic-light clarity · intuitive confidence tiers |
| **Data Strategy** | Fuses 3 real NSW datasets · three-tier model for gap coverage · transparent provenance |
| **Technical Execution** | Full-stack: browser + proxy + Flask/SQLite backend · working auth · composite scoring algorithm · graceful fallback when APIs fail |
| **Commercial Feasibility** | Three-tier subscription (Basic/Plus/Pro) · premium discount mechanism built into UI · clear partnership playbook with operators |
| **Innovation** | Three-tier confidence model (nobody else does this) · explicit provenance per spot · architecture ready to absorb private operator data as it opens |
| **Pitch** | Live TfNSW feed as the demo moment · real booking flow end-to-end · honest data story |

---

## What's next (roadmap)

**Phase 1 — today** (shipped for hackathon)
- 23 tracked TfNSW Park & Rides
- 76 real CBD commercial lots
- User accounts + booking management
- Full-stack architecture

**Phase 2 — 6 months**
- Pilot partnerships with Wilson / Secure / Care Park for live commercial feeds
- Integrate TfNSW Park'nPay ticket data when it becomes public
- BoM weather integration (real, not simulated)
- Mobile-responsive UI

**Phase 3 — 18 months**
- 1,000+ live tracked lots across Sydney
- Council partnerships for aggregate demand heatmaps
- ML prediction replacing heuristic model
- Expand to Melbourne, Brisbane

---

## Credits

Built April 2026 for the **SUDATA × COMM-STEM Hackathon** at the University of Sydney.

- TfNSW Open Data Hub for the Car Park API and Park&Ride Locations dataset
- City of Sydney for the Off-Street Parking dataset
- OpenStreetMap + CARTO for map tiles
- Leaflet for the map library
