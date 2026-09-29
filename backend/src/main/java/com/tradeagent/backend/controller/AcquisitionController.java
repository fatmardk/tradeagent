package com.tradeagent.backend.controller;

import com.tradeagent.backend.domain.BusinessRules;
import com.tradeagent.backend.dto.AcquisitionRequest;
import com.tradeagent.backend.dto.AcquisitionResponse;
import com.tradeagent.backend.service.AcquisitionService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/acquisition")
public class AcquisitionController {

    private final AcquisitionService acquisition;

    public AcquisitionController(AcquisitionService acquisition) {
        this.acquisition = acquisition;
    }

    @PostMapping("/quote")
    public AcquisitionResponse quote(@Valid @RequestBody
                                     AcquisitionRequest req) {
        BusinessRules rules = new BusinessRules(
                req.operationalCost() == null ? 0.0 : req.operationalCost(),
                req.riskBuffer() == null ? 0.0 : req.riskBuffer(),
                req.requiredProfit() == null ? 0.0 : req.requiredProfit(),
                req.requiredMargin());
        return acquisition.quote(req.brand(), req.model(), req.storageGb(),
                req.requiredRepairs(), rules, req.modelCode(), req.series());
    }
}
