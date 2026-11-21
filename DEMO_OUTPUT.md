# ARGUS-AI Demo Output

## Ingest (SCOUT -> pipeline -> ATLAS + GUARDIAN)
- **bitcoin-treasury-note** (markdown): 1 chunks, category=finance, risk=0 (low)
  - entity: CRYPTO_ADDRESS: 0x742d35Cc6634C0532925a3b844Bc454e4438f44e
  - entity: MONEY: $25,000
  - entity: DATE: 2026-03-14
  - entity: ORG: Northgate Capital
  - entity: ORG: Bloomington Builders Inc
  - entity: PLACE: Indiana
  - entity: PLACE: Bloomington
  - entity: PERSON: Bitcoin Treasury Note
  - entity: PERSON: Evan Shipley
  - entity: PERSON: Marcus Webb
  - entity: PERSON: Sarah Lindqvist
- **court-documents-summary** (text): 1 chunks, category=legal, risk=0 (low)
  - entity: DATE: April 2, 2026
  - entity: DATE: 2026-03-20
  - entity: DATE: March 30, 2026
  - entity: PERSON: Court Documents Summary
  - entity: PERSON: Judge Houghton
  - entity: PERSON: Monroe County
  - entity: PERSON: Attorney Daniel Reyes
  - entity: PERSON: Ryan Porter
- **scam-warning-example** (text): 1 chunks, category=uncategorized, risk=70 (high)

## Search: "bitcoin treasury policy" (ORACLE, hybrid BM25 + semantic)
- [1.0] bitcoin-treasury-note :: # Bitcoin Treasury Note On 2026-03-14, Evan Shipley-Courter met with Marcus Webb from Northgate Capital in Blo...
- [0.1467] scam-warning-example :: Example phishing message kept for risk-scoring reference: URGENT: act now, this is your final notice. Your acc...
- [0.0] court-documents-summary :: Court Documents Summary The custody hearing before Judge Houghton is scheduled for April 2, 2026 in Monroe Cou...

## Search: "court custody hearing documents" (ORACLE, hybrid BM25 + semantic)
- [1.0] court-documents-summary :: Court Documents Summary The custody hearing before Judge Houghton is scheduled for April 2, 2026 in Monroe Cou...
- [0.0852] scam-warning-example :: Example phishing message kept for risk-scoring reference: URGENT: act now, this is your final notice. Your acc...
- [0.0] bitcoin-treasury-note :: # Bitcoin Treasury Note On 2026-03-14, Evan Shipley-Courter met with Marcus Webb from Northgate Capital in Blo...

## Knowledge graph (ATLAS): 19 nodes, 83 relations
