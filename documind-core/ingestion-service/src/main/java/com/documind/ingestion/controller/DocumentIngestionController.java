package com.documind.ingestion.controller;

import com.documind.common.dto.ApiResponse;
import com.documind.ingestion.dto.DocumentEntity;
import com.documind.ingestion.service.DocumentIngestionService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/v1/documents")
@RequiredArgsConstructor
public class DocumentIngestionController {

    private final DocumentIngestionService ingestionService;

    @PostMapping("/upload")
    public ResponseEntity<ApiResponse<DocumentEntity>> uploadDocument(
            @RequestParam("file") MultipartFile file,
            @RequestHeader(value = "X-User-Id", required = false) String userId) {

        DocumentEntity savedDoc = ingestionService.processDocumentUpload(file, userId);
        return ResponseEntity.ok(ApiResponse.success(savedDoc, "Document uploaded and ingestion initiated"));
    }
}
