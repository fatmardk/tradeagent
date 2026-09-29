const fmt = (n) =>
  n == null ? '—'
            : '₺' + Number(n).toLocaleString('tr-TR',
                  { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const METHOD_BADGE = (m) =>
  m === 'RECENT_MARKET_MEDIAN' ? 'badge'
    : m && m.startsWith('COLD_START') ? 'badge fallback'
    : 'badge none';

const METHOD_TEXT = {
  RECENT_MARKET_MEDIAN: 'Recent market median — real observed offers',
  MARKET_MEDIAN_LOW_COVERAGE: 'Market median — low coverage (single offer/seller)',
  COLD_START_MODEL_MEDIAN: 'Cold-start: same-model median (other storages)',
  COLD_START_BRAND_STORAGE: 'Cold-start: brand + storage median',
  COLD_START_BRAND: 'Cold-start: brand median',
  COLD_START_GLOBAL: 'Cold-start: global median (no brand/model coverage)',
};

export default function ResultPanel({ data }) {
  if (!data) return null;
  const v = data.marketValuation;
  const repair = data.repair;
  const biz = data.business;
  const acq = data.acquisition;
  const price = acq.recommended_max_price;
  const hasPrice = typeof price === 'number';

  return (
    <>
      <div className="final-price">
        <div className="label">Recommended Maximum Acquisition Price</div>
        <div className={'value' + (hasPrice ? '' : ' na')}>
          {hasPrice ? fmt(price) : 'Unavailable — no market value'}
        </div>
      </div>

      {data.warnings?.length > 0 && (
        <div className="card">
          <h2>Warnings</h2>
          <ul className="warn-list">
            {data.warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      )}

      <div className="grid-2">
        <div className="card">
          <h2>Market Valuation</h2>
          <div style={{ marginBottom: 10 }}>
            <span className={METHOD_BADGE(v.valuationMethod)}>
              {v.valuationMethod}
            </span>
            <div className="muted" style={{ marginTop: 6 }}>
              {METHOD_TEXT[v.valuationMethod] || ''}
            </div>
          </div>
          <div className="stat"><span className="k">Expected market value</span>
            <b>{fmt(v.marketValue)}</b></div>
          {v.offerCount != null && (
            <>
              <div className="stat"><span className="k">Offers / sellers</span>
                <span>{v.offerCount} / {v.sellerCount}</span></div>
              <div className="stat"><span className="k">Observed at</span>
                <span>{v.observedAt} ({v.daysSinceObservation}d ago)</span></div>
              <div className="spread" style={{ marginTop: 10 }}>
                <div><b>{fmt(v.marketP25)}</b><span>P25</span></div>
                <div><b>{fmt(v.marketValue)}</b><span>Median</span></div>
                <div><b>{fmt(v.marketP75)}</b><span>P75</span></div>
              </div>
            </>
          )}
          {v.offerCount == null && (
            <div className="muted">No direct market observation —
              estimate from fallback hierarchy
              ({v.supportRows} support rows).</div>
          )}
        </div>

        <div className="card">
          <h2>Repair Cost</h2>
          {repair.quotes.length === 0 && (
            <p className="muted">No repairs selected.</p>)}
          {repair.quotes.map((q) => (
            <div className="stat" key={q.repairType}>
              <span className="k">
                {q.repairType}
                <span className="muted"> · {q.lookupMethod}</span>
              </span>
              <span>{q.totalCost != null ? fmt(q.totalCost)
                                        : 'unavailable'}</span>
            </div>
          ))}
          <div className="stat" style={{ borderTop: '1px solid #eee',
                                         marginTop: 8, paddingTop: 8 }}>
            <span className="k"><b>Expected repair cost</b></span>
            <b>{fmt(repair.expected_cost)}</b>
          </div>
          <div className="muted">Source: {repair.source_type}
            {' · '}Samsung TR official table</div>
        </div>
      </div>

      <div className="card">
        <h2>Business Assumptions</h2>
        <div className="grid">
          <div className="stat"><span className="k">Operational cost</span>
            <span>{fmt(biz.operational_cost)}</span></div>
          <div className="stat"><span className="k">Risk buffer</span>
            <span>{fmt(biz.risk_buffer)}</span></div>
          <div className="stat"><span className="k">Required profit</span>
            <span>{fmt(biz.required_profit)}
              {typeof biz.required_margin === 'number' &&
                ` (${(biz.required_margin * 100).toFixed(1)}% of value)`}</span>
          </div>
        </div>
      </div>

      <div className="card">
        <h2>Explanation / Provenance</h2>
        <div className="provenance">
          <span className="prov-chip obs">
            Market value: {data.explanation.market_value_origin}</span>
          <span className="prov-chip kb">
            Repair: OFFICIAL_REPAIR_DATA
            ({(data.explanation.repair_lookup_methods || []).join(', ')
              || 'n/a'})</span>
          <span className="prov-chip biz">
            Op. cost / risk / profit: BUSINESS_INPUT</span>
        </div>
        <p className="muted" style={{ marginBottom: 0 }}>
          Method: {data.explanation.valuation_method}
          {data.explanation.market_reference_count != null &&
            ` · ${data.explanation.market_reference_count} market references`}
          {data.explanation.repair_cost_source?.length > 0 &&
            ` · repair source: ${data.explanation.repair_cost_source.join(', ')}`}
        </p>
      </div>
    </>
  );
}
