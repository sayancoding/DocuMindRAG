package com.documind.gateway_service.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.reactive.function.client.WebClient;

@Configuration
public class GatewayConfig {

    @Value("${service.ingestion.url:http://localhost:8081}")
    private String ingestionServiceUrl;
    @Value("${service.ragCore.url:http://localhost:8082}")
    private String ragCoreServiceUrl;

    @Bean
    public WebClient ingestionServiceClient(){
        return WebClient.builder()
                .baseUrl(ingestionServiceUrl)
                .codecs(config -> config
                        .defaultCodecs()
                        .maxInMemorySize(16 * 1024 * 1024))
                .build();
    }

    @Bean WebClient ragCoreServiceClient(){
        return WebClient.builder()
                .baseUrl(ragCoreServiceUrl)
                .build();
    }
}
