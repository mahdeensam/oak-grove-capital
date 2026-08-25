# Oak Grove Capital: the 77 companies

A self-contained reference for Oak Grove Capital's Q2 2026 13F, built for someone
who wants to understand what these businesses actually are rather than just read
tickers. Three tabs: the write-ups, a flashcard quiz, and a monitoring cockpit.

**Live site:** https://mahdeensam.github.io/oak-grove-capital/

## The table

- All **98 disclosed lines**: 77 operating companies across 10 sectors, 19 ETFs
  and funds, and the options book, each with position value and what it is.
- **Click a company name** for a plain-English explanation of the business: where
  it came from, how it makes money, and why it sits in this portfolio.
- **Click a main product** for what the thing is, how it works, and how it differs
  from what rivals sell.
- **Underlined jargon is clickable.** A 161-term glossary explains DRAM, HBM, EUV
  lithography, EBITDA, duration, notional, tolling agreements, FFO and the rest,
  in one or two plain sentences, attached automatically wherever a term appears.
- Coloured dots track how well you know each company, from your flashcard history.

## Flashcards

- **775 cards by default, 873 possible**, across nine question types: ticker to
  company, company to product, what is this thing, who buys it, guess the company,
  versus the competition, where it sits, size of the position, and the year behind it.
- Decks for everything, cards you saved, cards you missed before, and cards you
  have not seen, filterable by section, with a count on every filter.
- Progress, saved cards, accuracy, best round and a day streak persist in the
  browser. Leave mid-round and it offers to resume where you stopped.

## Cockpit

A monitoring board for the 77 operating companies: live prices and moves, weight,
fundamentals, multiples, your own target, thesis, thesis breakers and a 100-point
conviction score, plus alerts on your own thresholds.

Five charts sit above the board and answer the obvious questions at a glance:

- **What moved the book today** — each holding's contribution in basis points, which
  add up exactly to the day's return, so you can see what actually did the damage.
- **Best and worst, past year** — the six at each end of a twelve-month price return.
- **Today by sector** — each sector's move, weighted by what you hold in it.
- **Is the money in the winners?** — weight against one-year return for every priced
  name, spaced logarithmically so one enormous winner does not flatten the rest.
- **Near the high, or near the low** — the twelve largest positions placed between
  their 52-week low and high.

Blue is up and red is down: green/red fails colour-vision separation (deuteranopia
ΔE 4.1 against a ≥8 target), while blue/red clears every check in both themes. The
sign is carried by the side of the zero line and the printed value too, so colour is
never the only channel.

Portfolio returns are computed from share counts (13F value divided by the price on
the filing date), so a $50M position moves the number fifty times as hard as a $1M
one, and the panel compares the book against the S&P 500 over four windows.

### The data feed

`ogc-refresh.py` fetches everything from Yahoo Finance's public endpoints and writes
`ogc-data.js`, which the page loads by itself. **No API key, no signup, no pip install** —
just the Python that ships with macOS.

**The published site keeps itself current.** A GitHub Actions workflow
(`.github/workflows/refresh.yml`) runs the same script every 30 minutes while US
markets are open, commits the result, and Pages redeploys. Nothing to install and no
secrets to configure. Press **Run workflow** on the Actions tab to refresh on demand.

To run it against your own copy:

```bash
python3 ogc-refresh.py                    # once
python3 ogc-refresh.py --serve --loop 300 # refresh every 5 min, and answer the Refresh button
```

On macOS, double-click `OGC feed.command` instead. The page re-reads the file every
minute while the Cockpit is open.

### The Refresh button

It fetches, wherever the page is running:

- **On the published site** it pulls live prices straight from the browser. Yahoo's
  spark endpoint answers 20 symbols at a time, so the whole book plus the S&P 500
  arrives in four requests, and it updates price, today's move, 1M, YTD, 1Y and the
  52-week range. Fundamentals and multiples keep coming from the scheduled job.
- **On a local copy** it calls the refresher on `127.0.0.1` for the full set, and falls
  back to the same browser fetch if that is not running.

Browsers cannot call Yahoo directly, because no cross-origin headers come back, so the
in-browser path goes through `r.jina.ai`, a public relay that adds them. No key and no
account; if it is unavailable the page says so and keeps showing the scheduled feed.

A page can't fetch this itself: Yahoo and the SEC send no cross-origin headers, so no
browser is allowed to call them from any origin. A script on your machine has no such
limit. The `ogc-data.js` committed here is a snapshot; the page shows how old it is.

## Notes

- One HTML file, no dependencies, no build step, and no external network requests.
  Open `index.html` in any browser and it works offline.
- Everything you type — targets, theses, scores, flashcard progress — stays in your
  browser's local storage and is never sent anywhere.
- Follows the viewer's light or dark theme.
- Independent notes compiled from public 13F filings. Not affiliated with or endorsed
  by Oak Grove Capital, and not investment advice.
- A 13F does not show cash, short positions, most directly held bonds and Treasury
  bills, private investments or many derivatives. Absence from this list is not
  evidence the fund does not own it.
- Competitive claims and market data reflect a point in time and are worth
  re-checking against current sources.
