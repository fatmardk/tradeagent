package com.tradeagent.backend.controller;

import com.tradeagent.backend.domain.ValuationResult;
import com.tradeagent.backend.dto.DeviceDto;
import com.tradeagent.backend.dto.ValuationApiResponse;
import com.tradeagent.backend.dto.ValuationRequest;
import com.tradeagent.backend.dto.ValuationResponse;
import com.tradeagent.backend.service.ValuationService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/valuation")
public class ValuationController {

    private final ValuationService valuation;

    public ValuationController(ValuationService valuation) {
        this.valuation = valuation;
    }

    @PostMapping
    public ValuationApiResponse valuate(@Valid @RequestBody
                                        ValuationRequest req) {
        ValuationResult v = valuation.valuate(req.brand(), req.model(),
                req.storageGb());
        return new ValuationApiResponse(
                new DeviceDto(req.brand(), req.model(), req.storageGb(),
                        ValuationService.canonicalVariant(req.brand(),
                                req.model(), req.storageGb())),
                ValuationResponse.from(v));
    }
}
