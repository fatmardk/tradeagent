package com.tradeagent.backend.repository;

import com.tradeagent.backend.domain.RepairObservation;

import java.util.List;

/** Canonical repair_cost_observation rows. Replaceable by a PostgreSQL impl. */
public interface RepairKbRepository {

    List<RepairObservation> findAll();
}
