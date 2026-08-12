package com.documind.ingestion.service;

import org.springframework.web.multipart.MultipartFile;

public interface StorageService {
    String storeFile(MultipartFile file,String documentId);
}
