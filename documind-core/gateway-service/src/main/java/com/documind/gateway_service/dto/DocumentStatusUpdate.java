package com.documind.gateway_service.dto;

import lombok.Data;


public record DocumentStatusUpdate(String documentId, String fileName, String path, int progress, String stage, String message) {
}
