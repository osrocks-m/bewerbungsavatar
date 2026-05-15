import logging
import os

from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor


_log_handler: logging.Handler | None = None


def configure_telemetry(app, engine) -> None:
    """Set up traces, metrics, and logs — no-op when OTEL_EXPORTER_OTLP_ENDPOINT is unset."""
    global _log_handler
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return

    # Resource reads OTEL_SERVICE_NAME (and other OTEL_RESOURCE_ATTRIBUTES) from env.
    resource = Resource.create()

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter())],
    )
    metrics.set_meter_provider(meter_provider)

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    _log_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)

    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)


def reattach_log_handler() -> None:
    """Re-attach the OTel log handler after uvicorn replaces the root logger's handlers."""
    if _log_handler is None:
        return
    root = logging.getLogger()
    if _log_handler not in root.handlers:
        root.setLevel(logging.INFO)
        root.addHandler(_log_handler)
