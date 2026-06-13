package com.documind.gateway_service.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.http.codec.multipart.FilePart;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.util.Objects;

@RestController
@RequestMapping("/api/gateway")
@CrossOrigin(origins = "*") // Prepping for your Angular integration later
public class GatewayIngestController {

    @Autowired
    private WebClient ragCoreWebClient;

    @PostMapping(value = "/ingest", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Mono<ResponseEntity<String>> proxyDocumentUpload(@RequestPart("file") MultipartFile file) {

        // 1. Guardrail validation using standard MultipartFile
        if (file.isEmpty() || !Objects.requireNonNull(file.getOriginalFilename()).toLowerCase().endsWith(".pdf")) {
            return Mono.just(ResponseEntity.badRequest().body("Invalid payload. Only PDF files are permitted."));
        }

        // 2. Build the multipart payload using the file's raw resource
        MultipartBodyBuilder bodyBuilder = new MultipartBodyBuilder();
        bodyBuilder.part("file", file.getResource());

        // 3. Post downstream asynchronously to the FastAPI core service
        return ragCoreWebClient.post()
                .uri("/api/v1/ingest/upload")
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(BodyInserters.fromMultipartData(bodyBuilder.build()))
                .retrieve()
                .toEntity(String.class)
                .onErrorResume(error -> Mono.just(
                        ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                                .body("❌ Gateway Routing Failure: " + error.getMessage())
                ));
    }
}