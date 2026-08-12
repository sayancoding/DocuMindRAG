package com.documind.common.events;

import com.documind.common.enums.DocumentStatus;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DocumentIngestedEvent implements Serializable {
    private String documentId;
    private String userId;
    private String fileName;
    private String filePath; // Local disk path or S3 Key
    private Long fileSizeBytes;
    private String contentType;
    private DocumentStatus status;
    private LocalDateTime timestamp;
}
