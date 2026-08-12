package com.documind.ingestion.service.impl;

import com.documind.common.exceptions.BusinessException;
import com.documind.ingestion.service.StorageService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;

@Slf4j
@Service
public class LocalStorageServiceImpl implements StorageService {

    @Value("${file.upload-dir:/tmp/documind-uploads}")
    private String uploadDir;

    @Override
    public String storeFile(MultipartFile file, String documentId) {
        try{
            Path rootPath = Paths.get(uploadDir);
            if(!Files.exists(rootPath)){
                Files.createDirectories(rootPath);
                log.info("Root dir is created :: "+ rootPath);
            }
            String originalFilename = file.getOriginalFilename();
            String fileExtension = "";
            if (originalFilename != null && originalFilename.contains(".")) {
                fileExtension = originalFilename.substring(originalFilename.lastIndexOf("."));
            }

            String newFileName = documentId + fileExtension;
            Path targetLocation = rootPath.resolve(newFileName);

            Files.copy(file.getInputStream(), targetLocation, StandardCopyOption.REPLACE_EXISTING);

            return targetLocation.toAbsolutePath().toString();
        }
        catch (IOException ex){
            throw new BusinessException("Failed to store file on disk: " + ex.getMessage(), "FILE_STORE_ERROR");
        }
    }
}
