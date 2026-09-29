# TradeAgent Frontend — Demo UI

Simple single-page demo for the Hybrid Market Valuation Engine v1
Spring Boot API. The backend is the source of truth — the UI only
sends inputs and renders responses; it never computes prices itself.

## Run

```bash
# 1. backend (repo root -> backend/)
python -m src.ingestion.export_backend   # once, from repo root
cd backend && mvn spring-boot:run        # http://localhost:8080

# 2. frontend
cd frontend
cp .env.example .env                     # VITE_API_BASE_URL=http://localhost:8080
npm install
npm run dev                              # http://localhost:5173
```

## Flow

1. Select **Brand → Model → Storage** (cascading, fed by `GET /api/devices?grade=A`)
2. Repair checkboxes load per model via `GET /api/repair-costs?modelName=…`
   — unsupported repairs are shown disabled as *unavailable*, never invented
3. Business inputs: operational cost, risk buffer, and either
   target margin % or required profit amount
4. **Calculate Acquisition Price** → `POST /api/acquisition/quote`
5. Result cards: market valuation (method badge + evidence: offers,
   sellers, observed date, P25/median/P75), repair cost, business
   assumptions, prominent final price, provenance chips
   (REAL MARKET OBSERVATION / OFFICIAL REPAIR DATA / BUSINESS INPUT)

## Structure

```
src/
  api/client.js          fetch wrappers + ApiError (VITE_API_BASE_URL)
  components/
    DeviceSelector.jsx   cascading brand/model/storage
    RepairSelector.jsx   repair chips w/ KB cost + unavailable state
    BusinessInputs.jsx   op cost / risk / profit mode
    ResultPanel.jsx      valuation, repair, business, price, provenance
    ErrorBanner.jsx      backend/API error display
  App.jsx                state + flow orchestration
  styles.css             minimal dashboard styling
```

## Error handling

- Backend unreachable → "Backend unavailable" banner (ApiError code)
- Backend `{error:{code,message}}` → shown verbatim
- `NO_REPAIR_DATA` → repair shown as unavailable, backend warnings listed
- Negative/empty numeric inputs → calculate button disabled
- Cold-start fallback → amber badge + support-row count, not presented
  as market observation

## Known limitations

- Grade-A segment only (mirrors engine scope)
- Repair KB is Samsung-only; other brands show all repairs unavailable
- No auth, no persistence, no history — demo scope by design
