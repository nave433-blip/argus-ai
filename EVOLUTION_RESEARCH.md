# ARGUS Evolution Research — Crypto Trend Bot Improvement Cycle

Generated: 2026-11-21T20:43:21+0000

Method: ARGUS SCOUT (robots.txt respected, >=1s delay, plain User-Agent ARGUS-AI Scout/0.5, GET only, no auth, no circumvention). Refusals recorded as-is.

## Scrape table

| Source | URL | Result | Chars / Why |
|---|---|---|---|
| Binance Academy - Moving Averages | https://academy.binance.com/en/articles/what-are-moving-averages | fetched | 0 chars |
| Binance Academy - RSI | https://academy.binance.com/en/articles/relative-strength-index-explained | fetched | 0 chars |
| Binance Academy - Risk Management | https://academy.binance.com/en/articles/risk-management-in-crypto-trading | fetched | 0 chars |
| Kraken Learn - Technical Analysis | https://www.kraken.com/learn/trading/technical-analysis-crypto-trading | refused/failed |  robots.txt disallows |
| Kraken Learn - Dollar Cost Averaging | https://www.kraken.com/learn/dollar-cost-averaging | refused/failed |  robots.txt disallows |
| Coinbase Learn - Crypto Trading Basics | https://www.coinbase.com/learn/crypto-trading | refused/failed |  Remote end closed connection without response |
| Coinbase Learn - What is volatility | https://www.coinbase.com/learn/crypto-basics/what-is-volatility | refused/failed |  Remote end closed connection without response |
| arXiv API - momentum crash | https://export.arxiv.org/api/query?search_query=all:%22momentum+crash%22&start=0&max_results=5 | refused/failed |  robots.txt disallows |
| arXiv API - regime switching trend following | https://export.arxiv.org/api/query?search_query=all:%22regime+switching%22+AND+all:%22trend+following%22&start=0&max_results=5 | refused/failed |  robots.txt disallows |
| arXiv API - volatility targeting | https://export.arxiv.org/api/query?search_query=all:%22volatility+targeting%22&start=0&max_results=5 | refused/failed |  robots.txt disallows |
| arXiv API - ATR trailing stop chandelier | https://export.arxiv.org/api/query?search_query=all:%22average+true+range%22+AND+all:%22trailing+stop%22&start=0&max_results=5 | refused/failed |  robots.txt disallows |
| arXiv API - trend following momentum | https://export.arxiv.org/api/query?search_query=all:%22time+series+momentum%22&start=0&max_results=5 | refused/failed |  robots.txt disallows |
| SSRN - Momentum Crashes abstract | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2486270 | refused/failed |  robots.txt disallows |
| GitHub README - freqtrade | https://raw.githubusercontent.com/freqtrade/freqtrade/develop/README.md | fetched | 12271 chars |
| GitHub README - jesse | https://raw.githubusercontent.com/jesse-ai/jesse/master/README.md | fetched | 12561 chars |
| GitHub README - backtrader | https://raw.githubusercontent.com/mementum/backtrader/master/README.rst | fetched | 5056 chars |
| GitHub README - vectorbt | https://raw.githubusercontent.com/polakowo/vectorbt/master/README.md | fetched | 15825 chars |
| Freqtrade docs - strategy customization | https://www.freqtrade.io/en/stable/strategy-customization/ | refused/failed |  robots.txt disallows |
| Freqtrade docs - stoploss / trailing | https://www.freqtrade.io/en/stable/stoploss/ | refused/failed |  robots.txt disallows |
| Jesse docs - strategies | https://docs.jesse.trade/docs/strategies/ | refused/failed |  robots.txt disallows |
| Quantpedia - Trend Following | https://quantpedia.com/strategies/trend-following-effect-in-stocks/ | fetched | 17057 chars |
| arXiv abstract - Momentum-Gated / momentum crashes (2604.09060) | https://arxiv.org/abs/2604.09060 | fetched | 5487 chars |
| arXiv HTML - Regime-Switching Jump Model (2402.05272) | https://arxiv.org/html/2402.05272v2 | fetched | 66664 chars |
| AlgoGP - Chandelier Exit guide | https://www.algogp.com/library/technical-indicators/chandelier-exit-guide | fetched | 16146 chars |
| JournalPlus - ATR Trailing Stop strategy | https://journalplus.co/strategies/atr-trailing-stop-strategy/ | refused/failed | 302 HTTP Error 302: The HTTP server returned a redirect error that would lead to an infinite loop.
The last 30x er |
| Freqtrade raw docs - stoploss | https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/stoploss.md | fetched | 14009 chars |
| Freqtrade raw docs - strategy customization | https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/strategy-customization.md | fetched | 61463 chars |
| Freqtrade raw docs - protections | https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/includes/protections.md | fetched | 9122 chars |
| VectorBT raw docs - portfolio | https://raw.githubusercontent.com/polakowo/vectorbt/master/docs/source/portfolio.md | refused/failed | 404 HTTP Error 404: Not Found |

Fetched: 14/29

## Concrete testable ideas

1. **[exit_rule]** Replace fixed-percentage exits with a Chandelier trailing stop: exit a long when close falls below Highest High(22) - 3 x ATR(22), ratcheting up only. — Source: https://www.algogp.com/library/technical-indicators/chandelier-exit-guide — Prediction: In walk-forward backtest, max drawdown and average loser size fall vs the current exit while average winner grows; falsified if Sharpe and profit factor do not improve out-of-sample at multipliers 2.5, 3.0 and 3.5.
2. **[entry_filter]** Add a Donchian breakout entry variant: enter only on a close at a new 55-day high, paired with the Chandelier (22, 3x ATR) exit. — Source: https://www.algogp.com/library/technical-indicators/chandelier-exit-guide — Prediction: Trade count drops but win/loss ratio and expectancy per trade rise vs the current entry; falsified if total net return after 0.1% fees falls in out-of-sample walk-forward windows.
3. **[sizing]** Size positions by stop distance: position size = 1% of equity divided by the initial Chandelier stop distance, so every trade risks the same 1% of equity. — Source: https://www.algogp.com/library/technical-indicators/chandelier-exit-guide — Prediction: Per-trade risk variance collapses and equity-curve volatility / max drawdown fall at equal or better total return; falsified if return per unit of realised volatility (Sharpe) does not improve in backtest.
4. **[entry_filter]** Test an all-time-high / rolling-high entry: enter when close >= highest close in lookback, exit on a 10-period ATR trailing stop, equal-weight holdings, rebalanced daily. — Source: https://quantpedia.com/strategies/trend-following-effect-in-stocks/ — Prediction: The strategy cuts the left tail vs buy-and-hold: max drawdown improves and Sharpe rises in backtest net of 0.5% round-trip cost assumption scaled to crypto fees; falsified if net Sharpe is below the current bot baseline.
5. **[backtest_validation]** Sweep ATR trailing-stop length 8 to 12 in 0.5 steps and pick a plateau, not a peak: Quantpedia reports no material difference across that range, with looser stops giving slightly higher win rates. — Source: https://quantpedia.com/strategies/trend-following-effect-in-stocks/ — Prediction: Backtest performance is flat across ATR 8-12; if a single sharp optimum appears instead of a plateau, treat it as overfitting and reject that parameter for live use.
6. **[entry_filter]** Gate momentum entries with a volatility-adjusted momentum filter (momentum divided by realised volatility) and de-risk when holdings become highly correlated in a bear regime. — Source: https://arxiv.org/abs/2604.09060 — Prediction: Momentum-crash episodes (worst 5% rolling 7-day strategy returns) become shallower and downside volatility / Sortino improves in a walk-forward backtest vs ungated momentum; falsified if crash depth and Sortino do not improve out-of-sample.
7. **[backtest_validation]** Require walk-forward validation for every parameter change: optimise on a rolling train window, evaluate only on the next unseen window, and promote a change only if out-of-sample alpha persists across windows including a stress period. — Source: https://arxiv.org/abs/2604.09060 — Prediction: Changes promoted under walk-forward retain at least half their in-sample Sharpe improvement out-of-sample; falsified for any change whose out-of-sample Sharpe improvement is zero or negative, which is then reverted.
8. **[regime]** Add a binary regime switch: allocate 100% to the trend strategy when the regime model anticipates bull, and 0% (cash / no new entries) when it anticipates bear, using only return-series risk and return features. — Source: https://arxiv.org/html/2402.05272v2 — Prediction: Volatility and maximum drawdown fall and Sharpe rises vs always-in trading in out-of-sample backtest net of costs and a 1-bar trading delay; falsified if drawdown does not fall or Sharpe does not rise.
9. **[regime]** Make the regime filter persistent: apply a jump-penalty / minimum-dwell rule so a regime must persist for several bars before exposure flips, instead of switching on a single-bar signal. — Source: https://arxiv.org/html/2402.05272v2 — Prediction: Regime flips per month and whipsaw trades fall, and net Sharpe after fees rises vs an unpenalised regime switch; falsified if flip count falls but net return falls more than fees saved.
10. **[exit_rule]** Use offset-activated trailing: keep a static stoploss (e.g. -10%) until profit reaches an offset (e.g. +3%), then trail tightly (e.g. 2% below the highest observed price) and only then. — Source: https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/stoploss.md — Prediction: Fewer winners are stopped out in early noise (higher trade win rate) while locked-in profit per winning trade rises vs always-on trailing; falsified if average net profit per trade does not improve in backtest.
11. **[risk_management]** Add a StoplossGuard circuit breaker: if 4 or more stoplosses occur within 24 candles, pause all new entries for 4 candles. — Source: https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/includes/protections.md — Prediction: Loss clustering is truncated: worst rolling 24-candle loss and max drawdown fall with only a small drop in total trades; falsified if drawdown is unchanged while total return falls materially.
12. **[risk_management]** Add a MaxDrawdown halt: if equity drawdown over a 48-candle lookback exceeds a set cap (freqtrade example 20%; test 10% and 15% for this bot), stop trading for 12 candles. — Source: https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/includes/protections.md — Prediction:  realised maximum drawdown in backtest never exceeds the cap by more than one trade's loss; falsified if backtested max drawdown still breaches the cap plus one average loss.
13. **[risk_management]** Add CooldownPeriod plus LowProfitPairs locks: after any exit, do not re-enter the same pair for 2-5 candles, and lock a pair whose last trades sum to under 2% profit. — Source: https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/includes/protections.md — Prediction: Re-entry churn trades and fees paid fall and net profit factor rises vs no-cooldown trading; falsified if removed trades were net profitable in aggregate in the backtest.
14. **[backtest_validation]** Benchmark every new signal against a dual moving-average cross baseline (fast MA crossing above slow = entry, crossing below = exit) evaluated with realistic 0.1% fees in a vectorised backtest. — Source: https://raw.githubusercontent.com/polakowo/vectorbt/master/README.md — Prediction: A candidate signal is only kept if it beats the dual-MA baseline on Sharpe and profit factor net of 0.1% fees; falsified (candidate rejected) if it wins gross but loses net of fees.
15. **[backtest_validation]** Gate promotion of any new entry rule with a rule-significance test and Monte Carlo reshuffle of trades before paper trading, as in Jesse's research workflow. — Source: https://raw.githubusercontent.com/jesse-ai/jesse/master/README.md — Prediction: Rules that pass significance + Monte Carlo retain positive expectancy in the following paper-trading window more often than rules promoted on raw backtest profit alone; falsified if promoted rules' paper expectancy is zero or negative.
## Honest notes on refusals and empty fetches

- Binance Academy (3 pages): HTTP fetch succeeded but extracted text was 0 chars — the pages are JavaScript app shells with no visible text for SCOUT's plain extractor. Recorded as fetched/empty, NOT used as a source for any idea above.
- Kraken Learn, Coinbase Learn, SSRN, arXiv export API, freqtrade.io docs, jesse docs: refused via robots.txt disallow, connection closed, HTTP 403, or a redirect loop — each recorded in the table above. No spoofed headers, mirrors, or retries were attempted.
- arXiv ideas come from the abstract/HTML pages on arxiv.org (a different, robots-allowed path), not from the disallowed export API.
- JournalPlus ATR page: HTTP 302 redirect loop — recorded as failed, not used.
- VectorBT raw portfolio.md guess: HTTP 404 — recorded; the vectorbt idea uses its fetched README instead.
- All 15 ideas are hypotheses for the bot's backtest/walk-forward harness, not proven results. Each carries a falsifiable prediction; promote none to live parameters without out-of-sample evidence.

Files: script `evolution_research.py`, fetched texts `data/evolution_inbox/`, candidates `data/evolution_candidates.json`, ideas export `../crypto-trend-bot/data/evolution_ideas.json`.
