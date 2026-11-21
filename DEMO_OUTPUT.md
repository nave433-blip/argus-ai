# ARGUS-AI Demo Output

## Ingest (SCOUT -> pipeline -> ATLAS + GUARDIAN)
- **bitcoin-treasury-note** (markdown): 1 chunks, category=finance, risk=0 (low)
  - entity: CRYPTO_ADDRESS: 0x742d35Cc6634C0532925a3b844Bc454e4438f44e
  - entity: MONEY: $25,000
  - entity: DATE: 2026-03-14
  - entity: ORG: Northgate Capital
  - entity: ORG: Bloomington Builders Inc
  - entity: PLACE: Bloomington
  - entity: PLACE: Indiana
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

## Graph RAG ask (ORACLE: hybrid retrieval + 1-hop graph expansion)
- mode: graph-rag (extractive synthesis, citations inline)
- answer: # Bitcoin Treasury Note On 2026-03-14, Evan Shipley-Courter met with Marcus Webb from Northgate Capital in Bloomington, Indiana to discuss a bitcoin treasury policy for small builders. The proposal set a budget of $25,000 in BTC purchases, with wallet address 0x742d35Cc6634C0532925a3b844Bc454e4438f44e noted for the test transfer. Sarah Lindqvist at Bloomington Builders Inc agreed to review the policy before any payment is released. [bitcoin-treasury-note#c0] Example phishing message kept for risk-scoring reference: URGENT: act now, this is your final notice. Your account shows an investment opportunity with guaranteed returns — wire transfer the funds immediately. Do not tell anyone about this message, keep this secret. Send your password and seed phrase to verify before it expires today. [scam-warning-example#c0] Court Documents Summary The custody hearing before Judge Houghton is scheduled for April 2, 2026 in Monroe County. Attorney Daniel Reyes filed the updated case plan on 2026-03-20. The filing covers custody, visitation, and the family support agreement. Centerstone recovery coach Ryan Porter submitted a progress letter for the same case. All documents are due to the court by March 30, 2026, and the hearing will review treatment progress and the case plan. [court-documents-summary#c0] Connected entities from the knowledge graph: $25,000, 0x742d35Cc6634C0532925a3b844Bc454e4438f44e, 2026-03-14, 2026-03-20, April 2, 2026, Attorney Daniel Reyes, Bitcoin Treasury Note, Bloomington.
- citations: bitcoin-treasury-note#c0, scam-warning-example#c0, court-documents-summary#c0
- graph entities in context: $25,000, 0x742d35Cc6634C0532925a3b844Bc454e4438f44e, 2026-03-14, 2026-03-20, April 2, 2026, Attorney Daniel Reyes, Bitcoin Treasury Note, Bloomington, Bloomington Builders Inc, Court Documents Summary
- 1-hop neighbors: $25,000, 0x742d35Cc6634C0532925a3b844Bc454e4438f44e, 2026-03-14, 2026-03-20, April 2, 2026, Attorney Daniel Reyes, Bitcoin Treasury Note, Bloomington, Bloomington Builders Inc, Court Documents Summary
