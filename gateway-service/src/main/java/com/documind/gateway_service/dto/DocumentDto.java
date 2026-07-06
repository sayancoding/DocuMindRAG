package com.documind.gateway_service.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class DocumentDto {
    private String id;

    private String file_name;
    private String file_size_bytes;
    private String content_type;
    private String status;
}
