FROM registry.access.redhat.com/ubi9/openjdk-21-runtime:1.24
WORKDIR /deployments
COPY --chown=185:0 customer-api/target/quarkus-app/lib/ ./lib/
COPY --chown=185:0 customer-api/target/quarkus-app/*.jar ./
COPY --chown=185:0 customer-api/target/quarkus-app/app/ ./app/
COPY --chown=185:0 customer-api/target/quarkus-app/quarkus/ ./quarkus/
ENV HTTP_PORT=8080
EXPOSE 8080
USER 185
ENTRYPOINT ["java", "-jar", "/deployments/quarkus-run.jar"]
