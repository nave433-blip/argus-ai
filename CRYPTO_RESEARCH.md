# ARGUS Crypto Research — corpus for the Crypto Trend Bot

Generated: 2026-11-21T18:30:05+0000  
Method: ARGUS SCOUT (robots.txt respected, >=1s delay, plain client, GET only) fetched the known public seed pages below; the standard ARGUS pipeline (ingest -> chunk -> embed -> entities -> knowledge graph -> classify/risk) processed whatever was reachable. Failures (403/451/robots) are recorded as-is — no circumvention attempted.

## Fetch results

| Seed | URL | Result | Detail |
|------|-----|--------|--------|
| Binance US API docs | https://docs.binance.us/ | 200 OK | 74936 chars of text |
| Binance Vision (public data) | https://data.binance.vision/ | 200 OK | 72 chars of text |
| Binance futures docs — funding rate history | https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History | 200 OK | 0 chars of text |
| alternative.me Fear & Greed | https://alternative.me/crypto/fear-and-greed-index/ | 200 OK | 10363 chars of text |
| mempool.space | https://mempool.space/ | FAILED (n/a) | The read operation timed out |
| mempool.space API docs | https://mempool.space/docs/api/rest | FAILED (n/a) | The read operation timed out |
| CoinDesk | https://www.coindesk.com/ | FAILED (429) | HTTP Error 429: Too Many Requests |
| CoinTelegraph | https://cointelegraph.com/ | FAILED (n/a) | robots.txt disallows |
| TradingView features | https://www.tradingview.com/features/ | 200 OK | 5925 chars of text |
| 3Commas | https://3commas.io/ | FAILED (n/a) | robots.txt disallows |
| SEC — crypto assets topic | https://www.sec.gov/securities-topics/crypto-assets | FAILED (n/a) | robots.txt disallows |
| CFTC — virtual currency risks | https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/understand_risks_of_virtual_currency.html | 200 OK | 8009 chars of text |
| Kraken API docs | https://docs.kraken.com/ | 200 OK | 68791 chars of text |
| Coinbase developer docs | https://docs.cdp.coinbase.com/ | 200 OK | 46269 chars of text |

## Corpus stats

- Documents ingested: 8 of 14 seeds
- Chunks: 200
- Distinct entities: 636
- Knowledge graph: 636 nodes, 73340 relations

## Top entities (by document frequency)

- Market Data (PERSON) — 2 docs
- https://mintlify.com/docs.json (URL) — 2 docs
- Assistant Responses (PERSON) — 2 docs
- support@alternative.me (EMAIL) — 1 docs
- https://alternative.me/crypto/fear-and-greed-index/ (URL) — 1 docs
- https://alternative.me/crypto/fear-and-greed-index.png (URL) — 1 docs
- https://alternative.me/images/fng/crypto-fear-and-greed-index-2020-5-13.png (URL) — 1 docs
- https://api.alternative.me/ (URL) — 1 docs
- https://api.alternative.me/fng/ (URL) — 1 docs
- https://api.alternative.me/fng/?limit=10 (URL) — 1 docs
- https://api.alternative.me/fng/?limit=10&format=csv (URL) — 1 docs
- https://api.alternative.me/fng/?limit=10&format=csv&date_format=us (URL) — 1 docs
- https://api.alternative.me/fng/?limit=2 (URL) — 1 docs
- 05/29/2018 (DATE) — 1 docs
- May 13, 2020 (DATE) — 1 docs
- Greed Source (PERSON) — 1 docs
- Crypto Fear (PERSON) — 1 docs
- Greed Index (PERSON) — 1 docs
- Bitcoin Sentiment (PERSON) — 1 docs
- Find Suitable Software (PERSON) — 1 docs

## Topic mentions

- API: 466
- Kraken: 148
- Coinbase: 132
- SEC: 98
- Binance: 83
- futures: 24
- Bitcoin: 21
- CFTC: 19
- stablecoin: 16
- order book: 16
- Fear & Greed: 10
- fees: 5
- funding rate: 1
- liquidation: 1

## Public API / data endpoints mentioned in the pages

- `/api/v3/acccount` — from https://docs.binance.us/
- `/api/v3/account` — from https://docs.binance.us/
- `/api/v3/account/commission` — from https://docs.binance.us/
- `/api/v3/aggTrades` — from https://docs.binance.us/
- `/api/v3/allOrderList` — from https://docs.binance.us/
- `/api/v3/allOrders` — from https://docs.binance.us/
- `/api/v3/avgPrice` — from https://docs.binance.us/
- `/api/v3/depth` — from https://docs.binance.us/
- `/api/v3/exchangeInfo` — from https://docs.binance.us/
- `/api/v3/historicalTrades` — from https://docs.binance.us/
- `/api/v3/klines` — from https://docs.binance.us/
- `/api/v3/myFilters` — from https://docs.binance.us/
- `/api/v3/myPreventedMatches` — from https://docs.binance.us/
- `/api/v3/myTrades` — from https://docs.binance.us/
- `/api/v3/openOrders` — from https://docs.binance.us/
- `/api/v3/order` — from https://docs.binance.us/
- `/api/v3/order/cancelReplace` — from https://docs.binance.us/
- `/api/v3/order/oco` — from https://docs.binance.us/
- `/api/v3/order/test` — from https://docs.binance.us/
- `/api/v3/ping` — from https://docs.binance.us/
- `/api/v3/ticker` — from https://docs.binance.us/
- `/api/v3/ticker/24hr` — from https://docs.binance.us/
- `/api/v3/ticker/bookTicker` — from https://docs.binance.us/
- `/api/v3/ticker/price` — from https://docs.binance.us/
- `/api/v3/ticker/tradingDay` — from https://docs.binance.us/
- `/api/v3/time` — from https://docs.binance.us/
- `/api/v3/trades` — from https://docs.binance.us/
- `/api/v3/userDataStream` — from https://docs.binance.us/
- `https://api.alternative.me/fng/` — from https://alternative.me/crypto/fear-and-greed-index/
- `https://api.alternative.me/fng/?limit=10` — from https://alternative.me/crypto/fear-and-greed-index/
- `https://api.alternative.me/fng/?limit=10&format=csv` — from https://alternative.me/crypto/fear-and-greed-index/
- `https://api.alternative.me/fng/?limit=10&format=csv&date_format=us` — from https://alternative.me/crypto/fear-and-greed-index/
- `https://api.alternative.me/fng/?limit=2` — from https://alternative.me/crypto/fear-and-greed-index/
- `https://api.binance.us/api/v3/aggTrades?symbol=LTCBTC` — from https://docs.binance.us/
- `https://api.binance.us/api/v3/depth?symbol=LTCBTC` — from https://docs.binance.us/
- `https://api.binance.us/api/v3/exchangeInfo` — from https://docs.binance.us/
- `https://api.binance.us/api/v3/exchangeInfo?permissions=SPOT` — from https://docs.binance.us/
- `https://api.binance.us/api/v3/exchangeInfo?showPermissionSets=false` — from https://docs.binance.us/
- `https://api.binance.us/api/v3/exchangeInfo?symbol=BNBBTC` — from https://docs.binance.us/
- `https://api.binance.us/api/v3/exchangeInfo?symbol=BTCUSD` — from https://docs.binance.us/
- `https://api.binance.us/api/v3/exchangeInfo?symbols=%5B%22BNBBTC%22,%22BTCUSDT%22%5D` — from https://docs.binance.us/
- `https://api.binance.us/api/v3/exchangeInfo?symbols=[` — from https://docs.binance.us/
- `https://api.binance.us/api/v3/historicalTrades?symbol=` — from https://docs.binance.us/
- `https://api.binance.us/api/v3/historicalTrades?symbol=&lt;symbol&gt` — from https://docs.binance.us/
- `https://api.binance.us/api/v3/openOrders?symbol=BTCUSDT&amp;timestamp=1499827319559&amp;signature=c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71` — from https://docs.binance.us/
- `https://api.binance.us/api/v3/openOrders?symbol=BTCUSDT&timestamp=1499827319559&signature=c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71` — from https://docs.binance.us/
- `https://api.binance.us/api/v3/order` — from https://docs.binance.us/
- `https://api.binance.us/api/v3/order?symbol=LTCBTC&amp;side=BUY&amp;type=LIMIT&amp;timeInForce=GTC` — from https://docs.binance.us/
- `https://api.binance.us/api/v3/order?symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC` — from https://docs.binance.us/
- `https://api.binance.us/api/v3/ping` — from https://docs.binance.us/
- `https://api.binance.us/api/v3/time` — from https://docs.binance.us/
- `https://api.binance.us/api/v3/trades?symbol=LTCBTC` — from https://docs.binance.us/
- `https://api.kraken.com/0/private/AddOrder` — from https://docs.kraken.com/
- `https://api.kraken.com/0/private/AddOrder\` — from https://docs.kraken.com/

## Per-document classification / risk

- alternative-me-fear-greed: 19 chunks, 58 entities, category=finance, risk=15 (low)
- binance-futures-docs-funding-rate-history: 1 chunks, 1 entities, category=uncategorized, risk=0 (low)
- binance-us-api-docs: 118 chunks, 361 entities, category=finance, risk=35 (medium)
- binance-vision-public-data: 1 chunks, 6 entities, category=uncategorized, risk=0 (low)
- cftc-virtual-currency-risks: 13 chunks, 56 entities, category=legal, risk=15 (low)
- coinbase-developer-docs: 14 chunks, 82 entities, category=project, risk=40 (medium)
- kraken-api-docs: 24 chunks, 59 entities, category=project, risk=40 (medium)
- tradingview-features: 10 chunks, 16 entities, category=finance, risk=15 (low)

Machine-readable export: `crypto-trend-bot/data/argus_insights.json` (consumed by bot/argus_feed.py).
