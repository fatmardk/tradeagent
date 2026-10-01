const LABELS = {
  screen_module: 'Screen Replacement (module)',
  screen_eco: 'Screen Replacement (eco)',
  outer_screen: 'Outer Screen',
  back_glass: 'Back Glass',
  frame: 'Frame Replacement',
  frame_eco_screen: 'Frame + Eco Screen',
  battery: 'Battery Replacement',
  charging_port: 'Charging Port',
  camera_rear: 'Camera (rear)',
  camera_front: 'Camera (front)',
  earpiece: 'Earpiece',
  speaker: 'Speaker',
  mainboard: 'Mainboard',
  other: 'Other',
};

const QUALITY = {
  ORIGINAL: 'Original',
  SERVICE: 'Service',
  PREMIUM: 'Premium',
  HIGH_QUALITY: 'High Quality',
  REFURBISHED: 'Refurbished',
  PULLED: 'Pulled',
  COMPATIBLE: 'Compatible',
  UNKNOWN: null,
};

const SOURCE_TYPE = {
  OFFICIAL_MANUFACTURER: 'Official Manufacturer',
  AUTHORIZED_SERVICE: 'Authorized Service',
  INDEPENDENT_REPAIR_SERVICE: 'Independent Repair Service',
  PART_SUPPLIER: 'Part Supplier',
};

const fmt = (n) =>
  n == null ? null : '₺' + n.toLocaleString('tr-TR', { maximumFractionDigits: 0 });

/** Repair checkboxes fed by GET /api/repair-costs?modelName=<model>. */
export default function RepairSelector({ quotes, selected, onToggle }) {
  if (!quotes) {
    return (
      <div className="card">
        <h2>Required Repairs</h2>
        <p className="muted">Select a device model to load supported repairs.</p>
      </div>
    );
  }
  return (
    <div className="card">
      <h2>Required Repairs</h2>
      <div className="repair-list">
        {quotes.map((q) => {
          const hasCost = q.totalCost != null;
          const partOnly = q.priceType === 'PART_ONLY';
          const isSel = selected.includes(q.repairType);
          return (
            <label
              key={q.repairType}
              className={
                'repair-chip' + (isSel ? ' selected' : '') +
                (hasCost ? '' : ' unavailable')
              }
              title={hasCost
                ? `${q.lookupMethod} — ${q.sourceName || q.sourceId || 'REPAIR_KB'}`
                : 'Repair cost unavailable — no reliable KB record'}
            >
              <input
                type="checkbox"
                disabled={!hasCost}
                checked={isSel && hasCost}
                onChange={() => hasCost && onToggle(q.repairType)}
              />
              <span className="repair-chip-body">
                <span className="repair-chip-title">
                  {LABELS[q.repairType] || q.repairType}
                </span>
                {hasCost && (
                  <span className="repair-chip-meta">
                    {QUALITY[q.repairQuality] &&
                      <span>{QUALITY[q.repairQuality]} · </span>}
                    <span>{SOURCE_TYPE[q.sourceType] || q.sourceType}</span>
                  </span>
                )}
              </span>
              <span className="cost">
                {hasCost ? (
                  <>
                    {fmt(q.totalCost)}
                    <span className={'price-badge' + (partOnly ? ' part' : '')}>
                      {partOnly ? 'PART ONLY' : 'FULL_REPAIR'}
                    </span>
                    {partOnly && (
                      <span className="muted small">Labor not included</span>
                    )}
                  </>
                ) : 'Repair cost unavailable'}
              </span>
            </label>
          );
        })}
      </div>
      <p className="muted" style={{ marginBottom: 0 }}>
        Repair KB: multi-brand (Apple, Samsung, Xiaomi, Oppo, Realme).
        PART ONLY prices exclude labor — they are never treated as a
        complete repair cost. Unavailable repairs cannot be priced.
      </p>
    </div>
  );
}
