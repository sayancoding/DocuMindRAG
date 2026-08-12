# --- STAGE 1: Compilation and Packaging ---
FROM maven:3.9.6-eclipse-temurin-17-alpine AS build-stage

WORKDIR /app

# Copy the pom.xml file first to download project dependencies and leverage caching layers
COPY pom.xml .
RUN mvn dependency:go-offline -B

# Copy the actual application source code layers
COPY src ./src

# Compile and package the microservice into a production jar file, skipping test execution to save time
RUN mvn clean package -DskipTests


# --- STAGE 2: Lightweight Production Runtime ---
FROM eclipse-temurin:17-jre-alpine AS runtime-stage

WORKDIR /app

# # Create a non-privileged system user to execute the app securely inside the container
# RUN addgroup -S appgroup && adduser -S appuser -G appgroup
# USER appuser

# Copy only the compiled runner JAR file from the compilation stage
COPY --from=build-stage /app/target/*.jar app.jar

# Expose Spring Boot's internal gateway gateway port
EXPOSE 8081

# Optimize JVM memory configurations for container workloads
ENTRYPOINT ["java", "-XX:+UseG1GC", "-XX:+ExitOnOutOfMemoryError", "-jar", "app.jar"]