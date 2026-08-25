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

Portfolio returns are computed from share counts (13F value divided by the price on
the filing date), so a $50M position moves the number fifty times as hard as a $1M
one, and the panel compares the book against the S&P 500 over four windows.

### The data feed

`ogc-refresh.py` fetches everything from Yahoo Finance's public endpoints and writes
`ogc-data.js`, which the page loads by itself. **No API key, no signup, no pip install** —
just the Python that ships with macOS.

```bash
python3 ogc-refresh.py                    # once
python3 ogc-refresh.py --serve --loop 300 # refresh every 5 min, and answer the Refresh button
```

On macOS, double-click `OGC feed.command` instead. The page re-reads the file every
minute while the Cockpit is open, and the **Refresh** button pulls new numbers on demand
from the local refresher.

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
