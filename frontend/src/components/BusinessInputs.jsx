/** BUSINESS_INPUT parameters — never learned values. */
export default function BusinessInputs({
  opCost, riskBuffer, profitMode, profitValue,
  onOpCost, onRiskBuffer, onProfitMode, onProfitValue,
}) {
  const num = (v) => (v === '' ? '' : Number(v));
  return (
    <div className="card">
      <h2>Business Assumptions</h2>
      <div className="grid">
        <div className="field">
          <label>Operational Cost (TRY)</label>
          <input type="number" min="0" value={opCost}
                 onChange={(e) => onOpCost(num(e.target.value))} />
        </div>
        <div className="field">
          <label>Risk Buffer (TRY)</label>
          <input type="number" min="0" value={riskBuffer}
                 onChange={(e) => onRiskBuffer(num(e.target.value))} />
        </div>
        <div className="field">
          <label>Required Profit</label>
          <div className="radio-row">
            <label>
              <input type="radio" checked={profitMode === 'margin'}
                     onChange={() => onProfitMode('margin')} /> Target margin %
            </label>
            <label>
              <input type="radio" checked={profitMode === 'amount'}
                     onChange={() => onProfitMode('amount')} /> Amount (TRY)
            </label>
          </div>
          <input
            type="number" min="0" value={profitValue}
            placeholder={profitMode === 'margin' ? 'e.g. 15' : 'e.g. 5000'}
            onChange={(e) => onProfitValue(num(e.target.value))}
          />
        </div>
      </div>
    </div>
  );
}
