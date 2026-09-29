package com.tradeagent.backend.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "backend")
public class BackendProperties {

    private String dataDir = "../data/export";
    private Valuation valuation = new Valuation();

    public String getDataDir() {
        return dataDir;
    }

    public void setDataDir(String dataDir) {
        this.dataDir = dataDir;
    }

    public Valuation getValuation() {
        return valuation;
    }

    public void setValuation(Valuation valuation) {
        this.valuation = valuation;
    }

    public static class Valuation {
        private int maxObsAgeDays = 45;
        private String asOf = "";
        private String gradeSegment = "A";

        public int getMaxObsAgeDays() {
            return maxObsAgeDays;
        }

        public void setMaxObsAgeDays(int maxObsAgeDays) {
            this.maxObsAgeDays = maxObsAgeDays;
        }

        public String getAsOf() {
            return asOf;
        }

        public void setAsOf(String asOf) {
            this.asOf = asOf;
        }

        public String getGradeSegment() {
            return gradeSegment;
        }

        public void setGradeSegment(String gradeSegment) {
            this.gradeSegment = gradeSegment;
        }
    }
}
