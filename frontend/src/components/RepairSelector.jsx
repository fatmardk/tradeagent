const LABELS = {
  screen_module: 'Screen Replacement (module)',
  screen_eco: 'Screen Replacement (eco)',
  frame: 'Frame Replacement',
  frame_eco_screen: 'Frame + Eco Screen',
  outer_screen: 'Outer Screen',
  battery: 'Battery Replacement',
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
          const supported = q.totalCost != null;
          const isSel = selected.includes(q.repairType);
          return (
            <label
              key={q.repairType}
              className={
                'repair-chip' + (isSel ? ' selected' : '') +
                (supported ? '' : ' unavailable')
              }
              title={supported
                ? `${q.lookupMethod} — ${q.sourceId ?? 'REPAIR_KB'}`
                : 'Repair cost unavailable — no reliable KB record'}
            >
              <input
                type="checkbox"
                disabled={!supported}
                checked={isSel && supported}
                onChange={() => supported && onToggle(q.repairType)}
              />
              {LABELS[q.repairType] || q.repairType}
              <span className="cost">
                {supported ? fmt(q.totalCost) : 'unavailable'}
              </span>
            </label>
          );
        })}
      </div>
      <p className="muted" style={{ marginBottom: 0 }}>
        Repair KB coverage: Samsung TR official table only. Unavailable
        repairs cannot be included in the acquisition price.
      </p>
    </div>
  );
}
