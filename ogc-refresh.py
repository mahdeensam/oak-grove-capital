#!/usr/bin/env python3
"""
OGC cockpit refresher.

Pulls prices, returns, fundamentals and valuation for every company in the
dashboard and writes ogc-data.js next to it. No API key, no signup, no pip
install: it uses Yahoo Finance's public endpoints and Python's standard library.

    python3 ogc-refresh.py              # refresh once
    python3 ogc-refresh.py --loop 300   # keep refreshing every 5 minutes
    python3 ogc-refresh.py --only NVDA,MU

The dashboard picks the file up on its own: open oak-grove-77-companies.html
and the Cockpit tab reloads ogc-data.js every minute while it is on screen.

Why a script rather than the page fetching directly: Yahoo and SEC send no
CORS headers, so a browser page is not allowed to call them from any origin.
A local script has no such restriction.
"""
import json, re, os, sys, time, threading, urllib.request, urllib.error, http.cookiejar
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
# the dashboard is index.html when published, and keeps its long name locally
PAGE = next((os.path.join(HERE, n) for n in ("oak-grove-77-companies.html", "index.html")
             if os.path.exists(os.path.join(HERE, n))), os.path.join(HERE, "index.html"))
OUT  = os.path.join(HERE, "ogc-data.js")
UA   = "Mozilla/5.0"   # Yahoo hands out a crumb to a plain agent with a clean cookie jar
# tickers the dashboard spells differently from Yahoo
ALIAS = {"BRK.B": "BRK-B"}

def new_opener():
    o = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    o.addheaders = [("User-Agent", UA), ("Accept", "application/json,text/plain,*/*")]
    return o


opener = new_opener()


def get(url, tries=3, pause=0.8):
    for i in range(tries):
        try:
            with opener.open(url, timeout=25) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 429) and i < tries - 1:
                time.sleep(pause * (i + 2))
                continue
            return None
        except Exception:
            if i < tries - 1:
                time.sleep(pause)
                continue
            return None
    return None


def crumb():
    """A crumb only comes back for a session that starts clean, so retry from scratch."""
    global opener
    for i in range(4):
        opener = new_opener()
        try:
            opener.open("https://fc.yahoo.com", timeout=20).read()
        except Exception:
            pass
        try:
            with opener.open("https://query2.finance.yahoo.com/v1/test/getcrumb", timeout=20) as r:
                c = r.read().decode().strip()
            if c and len(c) < 32 and "<" not in c:
                return c
        except Exception:
            pass
        time.sleep(2 + 2 * i)
    return ""


def as_of_from_page():
    """The 13F position date the dashboard states, so weights can be rebuilt from it."""
    src = open(PAGE, encoding="utf-8").read()
    m = re.search(r"holdings as of ([A-Z][a-z]+) (\d{1,2}), (\d{4})", src)
    if not m:
        return "2026-06-30"
    months = {"January":1, "February":2, "March":3, "April":4, "May":5, "June":6, "July":7,
              "August":8, "September":9, "October":10, "November":11, "December":12}
    return "%s-%02d-%02d" % (m.group(3), months.get(m.group(1), 6), int(m.group(2)))


def tickers_from_page():
    """Read the company list straight out of the dashboard so the two never drift."""
    src = open(PAGE, encoding="utf-8").read()
    i = src.index("const ROWS = [")
    rows = json.loads(src[src.index("[", i):src.index("];", i) + 1])
    j = src.find("ROWS.push.apply(ROWS, ")
    if j > 0:
        rows += json.loads(src[src.index("[", j):src.index("]);", j) + 1])
    return [r["ticker"] for r in rows if not r.get("kind")]


def raw(node, key):
    v = (node or {}).get(key)
    if isinstance(v, dict):
        v = v.get("raw")
    return v if isinstance(v, (int, float)) else None


def m(v):                       # dollars -> millions
    return round(v / 1e6, 1) if isinstance(v, (int, float)) else None


def pct(v):                     # fraction -> percent
    return round(v * 100, 2) if isinstance(v, (int, float)) else None


def qs(sym, cr, mods):
    u = ("https://query2.finance.yahoo.com/v10/finance/quoteSummary/%s?modules=%s&crumb=%s"
         % (urllib.parse.quote(sym), mods, urllib.parse.quote(cr)))
    j = get(u)
    res = (j or {}).get("quoteSummary", {}).get("result")
    return res[0] if res else None


def summary(sym, cr):
    mods = "price,summaryDetail,defaultKeyStatistics,financialData,calendarEvents"
    return qs(sym, cr, mods)


def timeseries(sym, cr):
    """Quarterly EBITDA, revenue and free cash flow. The old statement modules
    still answer but return empty line items, so this is the one that works."""
    now = int(time.time())
    types = "quarterlyEBITDA,quarterlyTotalRevenue,quarterlyFreeCashFlow"
    u = ("https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/%s"
         "?symbol=%s&type=%s&period1=%d&period2=%d&merge=false&crumb=%s"
         % (urllib.parse.quote(sym), urllib.parse.quote(sym), urllib.parse.quote(types),
            now - 5 * 365 * 86400, now, urllib.parse.quote(cr)))
    j = get(u)
    out = {}
    for block in (j or {}).get("timeseries", {}).get("result", []):
        for key, series in block.items():
            if key in ("meta", "timestamp") or not isinstance(series, list):
                continue
            vals = [(v.get("asOfDate"), (v.get("reportedValue") or {}).get("raw"))
                    for v in series if v and (v.get("reportedValue") or {}).get("raw") is not None]
            if vals:
                out[key] = vals
    return out


def chart(sym, rng="1y"):
    u = ("https://query1.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=1d"
         % (urllib.parse.quote(sym), rng))
    j = get(u)
    res = (j or {}).get("chart", {}).get("result")
    return res[0] if res else None


def returns_from_chart(c, as_of=None):
    """1-month, year-to-date and 1-year price returns, the 52-week range, and the
    close on the 13F date, which is what turns a position value into a share count."""
    out = {}
    if not c:
        return out
    ts = c.get("timestamp") or []
    q = ((c.get("indicators") or {}).get("quote") or [{}])[0]
    closes = [x for x in (q.get("close") or []) if x is not None]
    pairs = [(t, v) for t, v in zip(ts, q.get("close") or []) if v is not None]
    if len(pairs) < 5:
        return out
    last_t, last = pairs[-1]
    def ret_from(cutoff):
        earlier = [v for t, v in pairs if t <= cutoff]
        return pct(last / earlier[-1] - 1) if earlier else None
    out["m1"] = ret_from(last_t - 30 * 86400)
    out["y1"] = pct(last / pairs[0][1] - 1)
    jan1 = time.mktime(time.struct_time((time.localtime(last_t).tm_year, 1, 1, 0, 0, 0, 0, 1, -1)))
    out["ytd"] = ret_from(int(jan1))
    out["hi"] = round(max(closes), 2)
    out["lo"] = round(min(closes), 2)
    if as_of:
        cut = time.mktime(time.strptime(as_of, "%Y-%m-%d"))
        on_or_before = [v for t, v in pairs if t <= cut + 86400]
        if on_or_before:
            out["pxq"] = round(on_or_before[-1], 4)
    return out


def yoy(vals):
    """Latest quarter against the same quarter a year earlier."""
    if not vals or len(vals) < 5:
        return None
    now, then = vals[-1][1], vals[-5][1]
    if not then or then <= 0:
        return None
    return pct(now / then - 1)


def one(sym_pair, cr, as_of=None):
    tk, ysym = sym_pair
    s = summary(ysym, cr)
    if not s:
        return tk, None
    p, sd = s.get("price", {}), s.get("summaryDetail", {})
    ks, fd = s.get("defaultKeyStatistics", {}), s.get("financialData", {})
    px = raw(p, "regularMarketPrice")
    rev = raw(fd, "totalRevenue")
    fcf = raw(fd, "freeCashflow")
    cap = raw(p, "marketCap")
    d = {
        "px": round(px, 2) if px else None,
        "prev": round(raw(p, "regularMarketPreviousClose") or 0, 2) or None,
        "rev": m(rev),
        "revg": pct(raw(fd, "revenueGrowth")),
        "ebitda": m(raw(fd, "ebitda")),
        "ebitdag": None,   # filled from the timeseries below
        "ebitdam": pct(raw(fd, "ebitdaMargins")),
        "eps": raw(ks, "trailingEps"),
        "epsg": pct(raw(fd, "earningsGrowth")),
        "fcf": m(fcf),
        "fcfm": pct(fcf / rev) if (fcf and rev) else None,
        "gm": pct(raw(fd, "grossMargins")),
        "om": pct(raw(fd, "operatingMargins")),
        "cash": m(raw(fd, "totalCash")),
        "debt": m(raw(fd, "totalDebt")),
        "pe": round(raw(sd, "trailingPE"), 2) if raw(sd, "trailingPE") else None,
        "fpe": round(raw(ks, "forwardPE"), 2) if raw(ks, "forwardPE") else None,
        "evebitda": round(raw(ks, "enterpriseToEbitda"), 2) if raw(ks, "enterpriseToEbitda") else None,
        "evs": round(raw(ks, "enterpriseToRevenue"), 2) if raw(ks, "enterpriseToRevenue") else None,
        "fcfy": pct(fcf / cap) if (fcf and cap) else None,
        "tgtA": round(raw(fd, "targetMeanPrice"), 2) if raw(fd, "targetMeanPrice") else None,
        "epsE": raw(ks, "forwardEps"),
    }
    ed = ((s.get("calendarEvents") or {}).get("earnings") or {}).get("earningsDate") or []
    if ed:
        fmt = ed[0].get("fmt") if isinstance(ed[0], dict) else None
        if fmt:
            d["earn"] = fmt
    ts = timeseries(ysym, cr)
    d["ebitdag"] = yoy(ts.get("quarterlyEBITDA"))
    if d["revg"] is None:
        d["revg"] = yoy(ts.get("quarterlyTotalRevenue"))
    fq = ts.get("quarterlyFreeCashFlow")
    if fq and len(fq) >= 4 and d.get("fcf") is None:
        d["fcf"] = m(sum(v for _, v in fq[-4:]))
    d.update(returns_from_chart(chart(ysym), as_of))
    return tk, {k: v for k, v in d.items() if v is not None}


def index_returns(sym="^GSPC"):
    """Today, 1 month, year to date and 1 year for the benchmark, so the dashboard
    can show excess return over the same windows it shows for the book."""
    out = {}
    c5 = chart(sym, "5d")
    if c5:
        q = ((c5.get("indicators") or {}).get("quote") or [{}])[0]
        closes = [v for v in (q.get("close") or []) if v is not None]
        if len(closes) >= 2 and closes[-2]:
            out["day"] = round((closes[-1] / closes[-2] - 1) * 100, 2)
    r = returns_from_chart(chart(sym))
    for k in ("m1", "ytd", "y1"):
        if r.get(k) is not None:
            out[k] = r[k]
    return out


def index_day(sym="^GSPC"):
    """Benchmark line: today's move in the S&P 500, from the last two daily closes.
    During a session the final bar is today, so closes[-1] vs closes[-2] is right
    whether or not the market is open."""
    c = chart(sym, "5d")
    if not c:
        return None
    q = ((c.get("indicators") or {}).get("quote") or [{}])[0]
    closes = [v for v in (q.get("close") or []) if v is not None]
    if len(closes) < 2 or not closes[-2]:
        return None
    return round((closes[-1] / closes[-2] - 1) * 100, 2)


def run(only=None):
    tks = tickers_from_page()
    if only:
        want = {t.strip().upper() for t in only.split(",")}
        tks = [t for t in tks if t in want]
    cr = crumb()
    if not cr:
        print("! no Yahoo crumb this time: prices and returns will load, fundamentals may not.")
    pairs = [(t, ALIAS.get(t, t.replace(".", "-"))) for t in tks]
    got, miss = {}, []
    as_of = as_of_from_page()
    with ThreadPoolExecutor(max_workers=6) as ex:
        for tk, d in ex.map(lambda p: one(p, cr, as_of), pairs):
            if d and d.get("px"):
                got[tk] = d
            else:
                miss.append(tk)
    bench = index_returns()
    payload = {"t": int(time.time() * 1000), "src": "Yahoo Finance", "n": len(got),
               "asOf": as_of, "spx": bench.get("day"), "bench": bench,
               "missing": miss, "by": got}
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("/* written by ogc-refresh.py - do not edit by hand */\n")
        f.write("window.OGC_AUTO = " + json.dumps(payload, separators=(",", ":")) + ";\n")
    os.replace(tmp, OUT)
    print("%s  %d of %d names -> %s%s" % (time.strftime("%H:%M:%S"), len(got), len(tks),
          os.path.basename(OUT), ("  missing: " + ",".join(miss)) if miss else ""))
    return len(got)


class Handler(BaseHTTPRequestHandler):
    """A one-endpoint server so the dashboard's Refresh button can pull new data
    on demand. Bound to localhost, GET only, and it never reads anything you type."""

    def _send(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/refresh":
            try:
                with LOCK:
                    n = run(ONLY)
                self._send(200, {"ok": True, "n": n, "t": int(time.time() * 1000)})
            except Exception as e:
                self._send(500, {"ok": False, "error": str(e)})
        elif path in ("/status", "/"):
            t = int(os.path.getmtime(OUT) * 1000) if os.path.exists(OUT) else None
            self._send(200, {"ok": True, "file": os.path.basename(OUT), "t": t})
        else:
            self._send(404, {"ok": False, "error": "no such endpoint"})

    def log_message(self, *a):
        pass


LOCK = threading.Lock()
ONLY = None


def serve(port):
    srv = HTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print("listening on http://127.0.0.1:%d  (the dashboard's Refresh button calls /refresh)" % port)


if __name__ == "__main__":
    args = sys.argv[1:]
    only = None
    loop = 0
    port = 0
    if "--only" in args:
        only = args[args.index("--only") + 1]
    if "--loop" in args:
        loop = int(args[args.index("--loop") + 1])
    if "--serve" in args:
        nxt = args.index("--serve") + 1
        port = int(args[nxt]) if nxt < len(args) and args[nxt].isdigit() else 8765
    if not os.path.exists(PAGE):
        sys.exit("cannot find %s next to this script" % os.path.basename(PAGE))
    ONLY = only
    with LOCK:
        run(only)
    if port:
        serve(port)
    if not loop and not port:
        sys.exit(0)
    try:
        while True:
            time.sleep(loop or 3600)
            if loop:
                try:
                    with LOCK:
                        run(only)
                except Exception as e:
                    print("! refresh failed:", e)
    except KeyboardInterrupt:
        print("\nstopped")
