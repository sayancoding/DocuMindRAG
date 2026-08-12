package com.documind.common.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@AllArgsConstructor
@NoArgsConstructor
@Data
@Builder
public class ErrorResponse {

    private String errorCode;
    private String message;
    private int status;
    private LocalDateTime timestamp;
}
