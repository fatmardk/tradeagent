package com.tradeagent.backend.repository;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tradeagent.backend.config.BackendProperties;
import com.tradeagent.backend.domain.MarketObservation;
import jakarta.annotation.PostConstruct;
import org.springframework.stereotype.Repository;

import java.io.IOException;
import java.nio.file.Path;
import java.util.List;

/** File-based impl over data/export/market_snapshot.json (canonical export). */
@Repository
public class JsonMarketSnapshotRepository implements MarketSnapshotRepository {

    private final Path file;
    private final ObjectMapper mapper = new ObjectMapper();
    private List<MarketObservation> rows = List.of();

    public JsonMarketSnapshotRepository(BackendProperties props) {
        this.file = Path.of(props.getDataDir())
                        .resolve("market_snapshot.json");
    }

    @PostConstruct
    void load() throws IOException {
        rows = mapper.readValue(file.toFile(),
                new TypeReference<>() {});
    }

    @Override
    public List<MarketObservation> findAll() {
        return rows;
    }
}
