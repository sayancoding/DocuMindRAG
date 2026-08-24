package com.documind.gateway_service.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.reactive.function.client.WebClient;

@Configuration
public class GatewayConfig {

    @Value("${rag.core.url:http://localhost:8081}")
    private String ingestionServiceUrl;

    @Bean
    public WebClient ingestionServiceClient(){
        return WebClient.builder()
                .baseUrl(ingestionServiceUrl)
                .codecs(config -> config
                        .defaultCodecs()
                        .maxInMemorySize(16 * 1024 * 1024))
                .build();
    }
}
