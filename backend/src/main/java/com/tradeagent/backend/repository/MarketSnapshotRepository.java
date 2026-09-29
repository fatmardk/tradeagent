package com.tradeagent.backend.repository;

import com.tradeagent.backend.domain.MarketObservation;

import java.util.List;

/** Canonical market_snapshot rows. Replaceable by a PostgreSQL impl. */
public interface MarketSnapshotRepository {

    List<MarketObservation> findAll();
}
