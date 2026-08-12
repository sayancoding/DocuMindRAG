package com.documind.ingestion.dao;

import com.documind.ingestion.dto.DocumentEntity;
import jakarta.validation.constraints.NotNull;
import org.jspecify.annotations.NonNull;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface DocumentsDao extends JpaRepository<DocumentEntity,String> {
    List<DocumentEntity> findByUserId(String userId);
    Optional<DocumentEntity> findById(@NonNull String id);
}
