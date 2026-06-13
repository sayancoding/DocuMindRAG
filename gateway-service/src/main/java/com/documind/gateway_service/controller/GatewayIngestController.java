package com.documind.gateway_service.controller;

import com.documind.gateway_service.dto.QueryRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.http.codec.multipart.FilePart;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

@RestController
@RequestMapping("/api/gateway")
@CrossOrigin(origins = "*")
public class GatewayIngestController {

    @Autowired
    private WebClient ragCoreWebClient;

    @PostMapping(value = "/ingest", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Mono<ResponseEntity<String>> proxyDocumentUpload(@RequestPart("file") Mono<FilePart> filePartMono) {

        return filePartMono
                // 1. Intercept the file part reactively
                .flatMap(filePart -> {
                    // Guardrail: Validate file extension
                    if (!filePart.filename().toLowerCase().endsWith(".pdf")) {
                        return Mono.just(ResponseEntity.badRequest().body("Invalid payload. Only PDF files are permitted."));
                    }

                    // 2. Build the multipart payload using WebFlux-safe elements
                    MultipartBodyBuilder bodyBuilder = new MultipartBodyBuilder();
                    bodyBuilder.part("file", filePart);

                    // 3. Post downstream to the FastAPI core service
                    return ragCoreWebClient.post()
                            .uri("/api/v1/ingest/upload")
                            .contentType(MediaType.MULTIPART_FORM_DATA)
                            .body(BodyInserters.fromMultipartData(bodyBuilder.build()))
                            .retrieve()
                            .toEntity(String.class);
                })
                // 4. Exception fallback handling if FastAPI is down
                .onErrorResume(error -> Mono.just(
                        ResponseEntity.status(500)
                                .body("❌ Gateway Routing Failure: Downstream AI Core is unreachable. Details: " + error.getMessage())
                ));
    }

    @PostMapping(value = "/query", consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    public Mono<ResponseEntity<String>> proxyDocumentQuery(@RequestBody QueryRequest queryPayload) {

        // Input Guardrail Validation
        if (queryPayload.getQuery() == null || queryPayload.getQuery().trim().isEmpty()) {
            return Mono.just(ResponseEntity.badRequest().body("{\"error\": \"Query text cannot be empty.\"}"));
        }

        // Forward JSON payload directly to FastAPI's query engine endpoint
        return ragCoreWebClient.post()
                .uri("/api/v1/query")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(queryPayload)
                .retrieve()
                .toEntity(String.class)
                .onErrorResume(error -> Mono.just(
                        ResponseEntity.status(500)
                                .body("{\"error\": \"❌ Gateway Query Failure: Downstream AI Core is unreachable. Details: " + error.getMessage() + "\"}")
                ));
    }

    @GetMapping("/health")
    Mono<String> getHealthCheck(){
        return Mono.just("Running :: DocMind Gateway service is working....");
    }
}