package com.documind.ingestion.producer;

import com.documind.common.events.DocumentIngestedEvent;
import lombok.AllArgsConstructor;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class DocumentEventProducer {

    private final KafkaTemplate<String, DocumentIngestedEvent> kafkaTemplate;

    @Value("${spring.kafka.topic.document-ingested:document-ingestion-events}")
    private String topicName;

    public void sendDocumentIngestedEvent(DocumentIngestedEvent event) {
        log.info("Publishing DocumentIngestedEvent to topic [{}] for documentId: {}", topicName, event.getDocumentId());
        kafkaTemplate.send(topicName, event.getDocumentId(), event);
    }


}
