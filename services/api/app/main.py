import asyncio
import hashlib
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app import deletion, jobs
from app.api import claims, collaborations, demo, health, opportunities, purchases, runs, uploads
from app.collaboration import ledger
from app.config import Settings
from app.db import database
from app.deletion_runtime import DeletionRuntime
from app.diwali import api as diwali_api
from app.diwali import persistence as diwali_persistence
from app.models import (
    AgentRun,
    Product,
    Purchase,
)
from app.p1 import api as p1_api
from app.p1 import monitoring
from app.providers.receipt import FixtureReceiptExtractor
from app.telemetry import initialize_telemetry


def create_app(database_url=None):
    settings = Settings()
    initialize_telemetry(settings.sentry_dsn, settings.sentry_environment)
    engine, factory = database(database_url or settings.database_url)
    ledger.migrate(engine)
    deletion_runtime = DeletionRuntime(engine, factory)

    @asynccontextmanager
    async def worker_lifespan(app):
        diwali_persistence.setup_schema(engine)
        if settings.p1_enabled:
            monitoring.setup_schema(engine)
        deletion_runtime.reconcile()
        with factory() as s:
            jobs.recover(s)
            diwali_persistence.recover_interrupted(s)
            ledger.recover_interrupted(s)
            for run in s.scalars(select(AgentRun).where(AgentRun.status.in_(["queued", "running"]))):
                if jobs.recoverable(run):
                    continue
                run.status = "partial"
                run.payload = run.payload | {
                    "warnings": ["Run interrupted by server restart; start a new run."]
                }
            s.commit()
        stopped = asyncio.Event()
        app.state.job_task = asyncio.create_task(jobs.work_loop(factory, settings, stopped))
        app.state.p1_watch_task = None
        if settings.p1_enabled:
            monitoring.setup_schema(engine)
            with factory.begin() as session:
                monitoring.recover_interrupted(session, datetime.now(UTC))
            if settings.p1_monitor_enabled and settings.cpsc_live_enabled:
                app.state.p1_watch_task = asyncio.create_task(monitoring.watch_loop(
                    factory, stopped, poll_seconds=settings.p1_monitor_poll_seconds))
        try:
            yield
        finally:
            stopped.set()
            app.state.job_task.cancel()
            try:
                await app.state.job_task
            except asyncio.CancelledError:
                pass
            task = app.state.p1_watch_task
            if task is not None:
                try:
                    await asyncio.wait_for(task, timeout=5)
                except (TimeoutError, asyncio.CancelledError):
                    task.cancel()
            engine.dispose()

    @asynccontextmanager
    async def lifespan(app):
        with jobs.worker_lock(engine):
            deletion_runtime.initialize()
            with deletion_runtime.owner():
                async with worker_lifespan(app):
                    yield

    app = FastAPI(title="Sueperman", lifespan=lifespan)
    app.state.deletion_runtime = deletion_runtime
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Idempotency-Key"],
    )

    @app.middleware("http")
    async def restrict_mutations(request, call_next):
        origin = request.headers.get("origin")
        if request.method == "POST" and origin and origin != settings.frontend_origin:
            return JSONResponse(
                status_code=403,
                content={
                    "code": "ORIGIN_REJECTED",
                    "message": "Request origin is not allowed",
                    "trace_id": str(uuid4()),
                },
            )
        try:
            deletion_runtime.reconcile()
        except deletion.DeletionJournalError as exc:
            return JSONResponse(status_code=503, content={"code": "DELETION_HISTORY_UNAVAILABLE", "message": str(exc)})
        return await call_next(request)

    @app.exception_handler(deletion.DeletionJournalError)
    async def deletion_error(request, exc):
        return JSONResponse(status_code=503, content={"code": "DELETION_HISTORY_UNAVAILABLE", "message": str(exc)})

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": str(exc.status_code), "message": str(exc.detail), "trace_id": str(uuid4())},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse(
            status_code=422,
            content={
                "code": "INVALID_INPUT",
                "message": "Invalid input; check required fields and formats.",
                "trace_id": str(uuid4()),
            },
        )

    def get(s, model, identifier):
        entity = s.get(model, identifier)
        if entity is None:
            raise HTTPException(404, "Resource not found")
        return entity

    def import_products(s, content, demo=False, extracted=None, source_type="csv", row_indices=None):
        products = extracted if extracted is not None else FixtureReceiptExtractor().extract(content)
        digest = hashlib.sha256(content).hexdigest()
        purchases, ids = [], []
        for i, p in enumerate(products):
            row_index = row_indices[i] if row_indices is not None else i
            key = f"{'demo' if demo else source_type}:{digest}:{row_index}"
            purchase = s.scalar(select(Purchase).where(Purchase.import_key == key))
            if purchase is None:
                purchase = Purchase(
                    import_key=key,
                    demo=demo,
                    payload={
                        "merchant": p.merchant,
                        "order_date": p.date_purchased.isoformat() if p.date_purchased else None,
                        "source_type": "demo" if demo else source_type,
                        "order_reference_redacted": p.order_reference_redacted,
                        **({"import_facts": p.model_dump(mode="json"), "import_count": len(products)}
                           if source_type in {"image", "pdf"} and not demo else {}),
                    },
                )
                s.add(purchase)
                s.flush()
                product = Product(
                    purchase_id=purchase.id,
                    demo=demo,
                    model_number=p.model_number,
                    upc=p.upc,
                    payload={
                        "product": p.model_dump(mode="json"),
                        "purchase_id": purchase.id,
                        "source_type": "demo" if demo else source_type,
                    },
                )
                s.add(product)
                s.flush()
            else:
                product = s.scalar(select(Product).where(Product.purchase_id == purchase.id, Product.payload["superseded"].as_boolean().is_not(True)))
            purchases.append(purchase.id)
            ids.append(product.id)
        s.commit()
        return {"purchase_ids": purchases, "product_ids": ids, "parse_warnings": []}

    health.register(app, factory, settings)
    demo.register(app, factory, settings, import_products)
    uploads.register(app, factory, settings, import_products)
    purchases.register(app, factory, deletion_runtime)
    runs.register(app, factory, settings, get)
    opportunities.register(app, factory, get)
    claims.register(app, factory, get, settings=settings)
    collaborations.register(app, factory, settings, get)
    diwali_api.register(app, factory, settings, get, import_products)
    p1_api.register(app, factory, settings, get)

    return app


app = create_app()
