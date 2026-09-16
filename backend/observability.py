import json
import logging
import time

from prometheus_client import Counter, Histogram
from sqlalchemy import event

HTTP_REQUESTS = Counter("shopilot_http_requests", "HTTP requests", ["method", "route", "status"])
HTTP_LATENCY = Histogram("shopilot_http_duration_seconds", "HTTP duration", ["route"])
CACHE = Counter("shopilot_cache", "Cache operations", ["outcome"])
MCP_CALLS = Counter("shopilot_mcp_calls", "MCP calls", ["agent", "tool", "outcome"])
MCP_LATENCY = Histogram("shopilot_mcp_duration_seconds", "MCP tool latency", ["tool"])
WORKFLOWS = Histogram("shopilot_workflow_duration_seconds", "Workflow duration", ["kind", "status"])
RETRIEVAL = Histogram("shopilot_retrieval_duration_seconds", "Retrieval latency")
EVENTS = Counter("shopilot_events", "Domain event handling", ["type", "outcome"])
DB_LATENCY = Histogram("shopilot_database_duration_seconds", "SQL query duration")


class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps(
            {
                "time": time.time(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
        )


def configure(app, engine):
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    from backend.config import settings

    if settings().otel_exporter_otlp_endpoint:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create({"service.name": "shopilot-api"}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)

    @event.listens_for(engine, "before_cursor_execute")
    def before(conn, cursor, statement, parameters, context, executemany):
        context._shopilot_start = time.perf_counter()

    @event.listens_for(engine, "after_cursor_execute")
    def after(conn, cursor, statement, parameters, context, executemany):
        DB_LATENCY.observe(time.perf_counter() - context._shopilot_start)
