import { useEffect, useMemo, useState } from 'react';
import { api } from './api/client.js';
import DeviceSelector from './components/DeviceSelector.jsx';
import RepairSelector from './components/RepairSelector.jsx';
import BusinessInputs from './components/BusinessInputs.jsx';
import ResultPanel from './components/ResultPanel.jsx';
import ErrorBanner from './components/ErrorBanner.jsx';

export default function App() {
  const [devices, setDevices] = useState([]);
  const [loadError, setLoadError] = useState(null);

  const [brand, setBrand] = useState('');
  const [model, setModel] = useState('');
  const [storage, setStorage] = useState(null);

  const [repairQuotes, setRepairQuotes] = useState(null);
  const [selectedRepairs, setSelectedRepairs] = useState([]);

  const [opCost, setOpCost] = useState(1500);
  const [riskBuffer, setRiskBuffer] = useState(1000);
  const [profitMode, setProfitMode] = useState('margin');
  const [profitValue, setProfitValue] = useState(15);

  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getDevices({ grade: 'A' })
      .then((d) => setDevices(d.devices))
      .catch((e) => setLoadError(e));
  }, []);

  const brands = useMemo(
    () => [...new Set(devices.map((d) => d.brand))].sort(),
    [devices]);
  const models = useMemo(
    () => [...new Set(devices.filter((d) => d.brand === brand)
                        .map((d) => d.model))].sort(),
    [devices, brand]);
  const storages = useMemo(
    () => [...new Set(devices.filter(
            (d) => d.brand === brand && d.model === model)
          .map((d) => d.storageGb))].sort((a, b) => a - b),
    [devices, brand, model]);

  // load repair options for the chosen model (KB coverage per repair type)
  useEffect(() => {
    setRepairQuotes(null);
    setSelectedRepairs([]);
    if (!model) return;
    api.getRepairCosts({ modelName: model })
      .then((d) => setRepairQuotes(d.quotes))
      .catch(() => setRepairQuotes([]));
  }, [model]);

  const toggleRepair = (t) =>
    setSelectedRepairs((s) =>
      s.includes(t) ? s.filter((x) => x !== t) : [...s, t]);

  const invalidNumbers =
    [opCost, riskBuffer, profitValue].some(
      (v) => v === '' || Number.isNaN(v) || v < 0)
    || (profitMode === 'margin' && profitValue > 100);

  const calculate = async () => {
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const payload = {
        brand, model, storageGb: storage,
        requiredRepairs: selectedRepairs,
        operationalCost: Number(opCost),
        riskBuffer: Number(riskBuffer),
        ...(profitMode === 'margin'
          ? { requiredMargin: Number(profitValue) / 100 }
          : { requiredProfit: Number(profitValue) }),
      };
      setResult(await api.postAcquisitionQuote(payload));
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="header">
        <h1>TradeAgent</h1>
        <p>Used / Refurbished Phone Acquisition Valuation — Hybrid Engine v1</p>
      </div>

      <ErrorBanner error={loadError || error} />

      <DeviceSelector
        brands={brands} models={models} storages={storages}
        brand={brand} model={model} storage={storage}
        onBrand={(b) => { setBrand(b); setModel(''); setStorage(null); }}
        onModel={(m) => { setModel(m); setStorage(null); }}
        onStorage={setStorage}
      />

      <RepairSelector
        quotes={repairQuotes}
        selected={selectedRepairs}
        onToggle={toggleRepair}
      />

      <BusinessInputs
        opCost={opCost} riskBuffer={riskBuffer}
        profitMode={profitMode} profitValue={profitValue}
        onOpCost={setOpCost} onRiskBuffer={setRiskBuffer}
        onProfitMode={setProfitMode} onProfitValue={setProfitValue}
      />

      <div style={{ marginBottom: 24 }}>
        <button className="primary" onClick={calculate}
                disabled={!brand || !model || !storage
                          || invalidNumbers || loading}>
          {loading ? 'Calculating…' : 'Calculate Acquisition Price'}
        </button>
        {invalidNumbers && (
          <span className="muted" style={{ marginLeft: 12 }}>
            Enter valid non-negative numeric values.
          </span>
        )}
      </div>

      <ResultPanel data={result} />
    </div>
  );
}
