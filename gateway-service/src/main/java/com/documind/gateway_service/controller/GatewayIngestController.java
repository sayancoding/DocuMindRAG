package com.documind.gateway_service.controller;

import com.documind.gateway_service.dto.QueryRequest;

import lombok.extern.slf4j.Slf4j;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.http.codec.multipart.FilePart;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;

import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import reactor.core.publisher.Sinks;

@RestController
@RequestMapping("/api/gateway")
@CrossOrigin(origins = "*")
@Slf4j
public class GatewayIngestController {

    @Autowired
    private WebClient ragCoreWebClient;

    // Sinks map matching an individual file session to a reactive broadcast channel
    private final Map<String, Sinks.Many<Map<String,Object>>> sessionSinks = new ConcurrentHashMap<>();

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

                    sessionSinks.putIfAbsent(filePart.filename(), Sinks.many().multicast().onBackpressureBuffer());

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

    /**
     * 2. SSE WebFlux Stream Route: Angular opens connection here to stream live events
     */
    @GetMapping(value = "/stream/{fileName}", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<Map<String, Object>>> streamProcessingStatus(@PathVariable String fileName) {
        Sinks.Many<Map<String, Object>> sink = sessionSinks.get(fileName);
        
        if (sink == null) {
            return Flux.empty();
        }

        // Convert our reactive Sink channel directly into a live Flux event output stream
        return sink.asFlux()
                .map(data -> ServerSentEvent.<Map<String, Object>>builder()
                        .event("status-update")
                        .data(data)
                        .build())
                .doOnError(err -> sessionSinks.remove(fileName))
                .doOnCancel(() -> sessionSinks.remove(fileName));
    }

    /**
     * Callback endpoint - Get push update from python about file processing.
     */
    @PostMapping("/status-callback")
    public Mono<Void> handleStatusCallback(@RequestBody Map<String, Object> statusPayload) {
        // Log the received status payload for monitoring
        log.info("## Received status callback: {}", statusPayload);
        String fileName = (String) statusPayload.get("fileName");
        String stage = (String) statusPayload.get("stage");

        Sinks.Many<Map<String, Object>> sink = sessionSinks.get(fileName);
        if(sink != null) {
            sink.tryEmitNext(statusPayload);

            if("completed".equalsIgnoreCase(stage) || "failed".equalsIgnoreCase(stage)) {
                sink.tryEmitComplete();
                sessionSinks.remove(fileName);
            }
        } else {
            log.warn("No active session found for file: {}", fileName);
        }
        

        return Mono.empty();  
    }

    @GetMapping("/health")
    Mono<String> getHealthCheck(){
        return Mono.just("Running :: DocMind Gateway service is working....");
    }
}