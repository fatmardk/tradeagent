package com.tradeagent.backend.repository;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tradeagent.backend.config.BackendProperties;
import com.tradeagent.backend.domain.RepairObservation;
import jakarta.annotation.PostConstruct;
import org.springframework.stereotype.Repository;

import java.io.IOException;
import java.nio.file.Path;
import java.util.List;

/** File-based impl over data/export/repair_kb.json (canonical export). */
@Repository
public class JsonRepairKbRepository implements RepairKbRepository {

    private final Path file;
    private final ObjectMapper mapper = new ObjectMapper();
    private List<RepairObservation> rows = List.of();

    public JsonRepairKbRepository(BackendProperties props) {
        this.file = Path.of(props.getDataDir()).resolve("repair_kb.json");
    }

    @PostConstruct
    void load() throws IOException {
        rows = mapper.readValue(file.toFile(), new TypeReference<>() {});
    }

    @Override
    public List<RepairObservation> findAll() {
        return rows;
    }
}
