package com.documind.ingestion.service;

import com.documind.common.enums.DocumentStatus;
import com.documind.common.events.DocumentIngestedEvent;
import com.documind.common.exceptions.BusinessException;
import com.documind.ingestion.dao.DocumentsDao;
import com.documind.ingestion.dto.DocumentEntity;
import com.documind.ingestion.producer.DocumentEventProducer;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDateTime;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class DocumentIngestionService {

    private final StorageService storageService;
    private final DocumentsDao documentsDao;
    private final DocumentEventProducer eventProducer;

    @Transactional
    public DocumentEntity processDocumentUpload(MultipartFile file, String userId) {
        if (file.isEmpty()) {
            throw new BusinessException("Uploaded file cannot be empty", "INVALID_FILE");
        }

        String documentId = UUID.randomUUID().toString();

        // 1. Store File locally (or S3)
        String storedPath = storageService.storeFile(file, documentId);

        // 2. Persist in Database
        DocumentEntity document = DocumentEntity.builder()
                .id(documentId)
                .userId(userId != null ? userId : "anonymous_user")
                .fileName(file.getOriginalFilename())
                .filePath(storedPath)
                .fileSizeBytes(file.getSize())
                .contentType(file.getContentType())
                .status(DocumentStatus.UPLOADED)
                .build();

        DocumentEntity savedDocument = documentsDao.save(document);

        // 3. Emit Kafka Event for Async Workers
        DocumentIngestedEvent event = DocumentIngestedEvent.builder()
                .documentId(savedDocument.getId())
                .userId(savedDocument.getUserId())
                .fileName(savedDocument.getFileName())
                .filePath(savedDocument.getFilePath())
                .fileSizeBytes(savedDocument.getFileSizeBytes())
                .contentType(savedDocument.getContentType())
                .status(savedDocument.getStatus())
                .timestamp(LocalDateTime.now())
                .build();

        eventProducer.sendDocumentIngestedEvent(event);

        return savedDocument;
    }
}
