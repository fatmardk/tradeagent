package com.tradeagent.backend.domain;

/** BUSINESS_INPUT — never learned, never hidden inside model code. */
public record BusinessRules(
        double operationalCost,
        double riskBuffer,
        double requiredProfit,     // absolute TRY
        Double requiredMargin) {   // fraction of market value, alternative

    public double profitFor(double marketValue) {
        return requiredMargin != null ? marketValue * requiredMargin
                                      : requiredProfit;
    }
}
