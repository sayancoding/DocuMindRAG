package com.documind.gateway_service.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.reactive.function.client.WebClient;

@Configuration
public class GatewayConfig {

    @Value("${rag.core.url:http://localhost:8080}")
    private String ragCoreUrl;

    @Bean
    public WebClient ragCoreWebClient(){
        return WebClient.builder()
                .baseUrl(ragCoreUrl)
                .codecs(config -> config
                        .defaultCodecs()
                        .maxInMemorySize(16 * 1024 * 1024))
                .build();
    }
}
