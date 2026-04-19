# Parkly — Sydney parking, live

SUDATA hackathon submission · Theme 3 (Improving Transportation in NSW)

**Parkly** is a live parking availability app that tells you whether you'll find a spot *before* you leave. Every parking location gets a single green/yellow/red status, backed by three data pipelines:

1. **Tracked live** — real-time occupancy from the Transport for NSW Car Park API
2. **Ticket-derived** — inferred from Park'nPay ticket purchases (simulated in demo)
3. **Predicted** — heuristic model based on hour, day, weather, and events

Ranked by a composite score combining availability, commute time, walk distance, price, confidence, and a "busy flag" for historically-busy spots.

---

## Quick start

### Step 1 — Get a TfNSW API key (free, 5 min)
1. Register at [opendata.transport.nsw.gov.au](https://opendata.transport.nsw.gov.au)
2. Log in → Developers → My Account → API Tokens
3. Create a token named "Parkly" — subscribe to the **Car Park API**
4. Copy the token

### Step 2 — Add the key to proxy.py
Open `proxy.py` in a text editor, find line 25:

```python
API_KEY = os.environ.get('TFNSW_API_KEY', 'YOUR_KEY_HERE')
```

Replace `'YOUR_KEY_HERE'` with your actual key, or set it via environment variable:

```bash
export TFNSW_API_KEY="your_actual_key_here"   # macOS / Linux
setx TFNSW_API_KEY "your_actual_key_here"     # Windows
```

### Step 3 — Run the proxy
```bash
python proxy.py
```
You should see:
```
▶ Parkly proxy running on http://localhost:8787
```
Leave this terminal open.

### Step 4 — Open the app
Double-click `parkly.html` — it opens in your default browser.

The top banner will show:
- **✓ TfNSW live data (6/6 facilities · via proxy)** → real live data working
- **✗ TfNSW unreachable · using mock data** → proxy not running or key invalid

---

## How it works

```
┌────────────────────┐   fetch    ┌────────────────────┐   HTTPS    ┌─────────────────┐
│   parkly.html      │◄──────────►│   proxy.py         │◄──────────►│  TfNSW Car Park │
│   (browser)        │  localhost │   (localhost:8787) │  + API key │  API v1         │
│                    │            │                    │            │                 │
│   Renders map,     │            │   Adds API key,    │            │  Returns live   │
│   ranks spots,     │            │   adds CORS        │            │  occupancy data │
│   shows status     │            │   headers          │            │                 │
└────────────────────┘            └────────────────────┘            └─────────────────┘
```

The HTML tries a direct call to TfNSW first. If that fails (it will, due to CORS restrictions on browser-origin requests), it automatically falls back to the local proxy. If the proxy isn't running either, it uses high-quality mock data so the demo still works.

## Data sources used

| Source | Tier | Purpose |
|---|---|---|
| TfNSW Car Park API | Tracked live | Real-time occupancy for 6+ commuter car parks |
| TfNSW Park&Ride Locations | Static | Facility coordinates and capacity |
| Park'nPay ticket data (simulated) | Derived | Street parking availability inference |
| Heuristic prediction model | Predicted | Everywhere without sensor data |
| Historical patterns (hour × day × weather × event) | All tiers | Demand baseline |

## File structure
```
parkly/
├── parkly.html    ← open this in your browser
├── proxy.py       ← run this first
└── README.md      ← you are here
```

## Troubleshooting

**"TfNSW unreachable · using mock data"**
- Is `proxy.py` running in a terminal?
- Did you replace `YOUR_KEY_HERE` with your real API key?
- Check the proxy terminal for error messages

**"API key not set" error**
- Edit `proxy.py` line 25 OR set `TFNSW_API_KEY` env variable
- Restart `python proxy.py` after changing

**Port 8787 already in use**
- Edit `proxy.py` line 26 to change `PORT = 8787` to something else
- Update `parkly.html` `PROXY_URL` to match

---

## Judging tick-list

- **Product Design** — one screen, traffic-light statuses, intuitive ranking
- **Data Strategy** — fuses real TfNSW live data + simulated ticket feed + heuristic prediction + demand context
- **Technical Execution** — working proxy, graceful degradation, composite scoring algorithm
- **Commercial Feasibility** — premium tier with discount mechanism built into UI
- **Innovation** — three-tier confidence model with transparent status provenance
- **Pitch** — live updating map with real TfNSW data is the demo moment

Built in one day for the SUDATA x COMM-STEM hackathon, Sydney, April 2026.
