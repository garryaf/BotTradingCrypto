# Multi-stage: build the Risk Gate engine, ship only the binary (RUST_ENGINE_INTEGRATION_SPEC.md §6.2).
FROM rust:1.97-slim-trixie AS build
WORKDIR /engine
COPY Cargo.toml Cargo.lock ./
COPY src ./src
RUN cargo build --release --locked

FROM debian:trixie-slim
COPY --from=build /engine/target/release/auto-trade-engine /usr/local/bin/engine
USER nobody
EXPOSE 8080
CMD ["engine", "0.0.0.0:8080"]
