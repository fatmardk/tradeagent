/** Cascading Brand → Model → Storage selects over GET /api/devices rows. */
export default function DeviceSelector({
  brands, models, storages,
  brand, model, storage,
  onBrand, onModel, onStorage,
}) {
  return (
    <div className="card">
      <h2>Device</h2>
      <div className="grid">
        <div className="field">
          <label>Brand</label>
          <select value={brand} onChange={(e) => onBrand(e.target.value)}>
            <option value="">Select brand…</option>
            {brands.map((b) => <option key={b} value={b}>{b}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Model</label>
          <select value={model} disabled={!brand}
                  onChange={(e) => onModel(e.target.value)}>
            <option value="">Select model…</option>
            {models.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Storage</label>
          <select value={storage ?? ''} disabled={!model}
                  onChange={(e) => onStorage(Number(e.target.value))}>
            <option value="">Select storage…</option>
            {storages.map((s) => (
              <option key={s} value={s}>{s} GB</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
