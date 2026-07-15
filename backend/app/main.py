"""WhereIsMyMoneyGoing - FastAPI Application."""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, get_engine, auto_migrate_columns
from app.routers import transactions, analytics, upload, categories, classification, auth, insights, budgets, ai_summary, jobs
from app.models import User, Transaction, Category, BankStatement, ClassificationRule, Budget, LearnedRule, ClassificationJob

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    logger.info(f"Starting WhereIsMyMoneyGoing API (env={settings.ENVIRONMENT})")

    # Run all blocking DB operations in a thread to avoid blocking the event loop
    await asyncio.to_thread(_init_database)

    # Pre-load ML model in background (don't block startup)
    async def _preload_ml_model():
        try:
            from app.services.classification.ml_classifier import get_pipeline
            await asyncio.to_thread(get_pipeline)
            logger.info("ML model pre-loaded successfully")
        except Exception as e:
            logger.warning("ML model pre-load failed (will retry on first use): %s", e)

    asyncio.create_task(_preload_ml_model())

    yield

    logger.info("Shutting down WhereIsMyMoneyGoing API")


def _init_database():
    """Create tables and seed categories (runs in a thread)."""
    try:
        engine = get_engine()
        # Auto-migrate: add any missing columns to existing tables
        auto_migrate_columns(engine)
        # Create any new tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables and schema ensured")
        _seed_default_categories()
    except Exception as e:
        logger.error(f"Database initialization error: {e}")


def _seed_default_categories():
    """Seed default system categories, adding any missing ones."""
    from app.core.database import get_session_local

    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        default_categories = [
            {"name": "Food & Dining", "icon": "🍽️", "color": "#FF6B6B"},
            {"name": "Groceries", "icon": "🛒", "color": "#4ECDC4"},
            {"name": "Transportation", "icon": "🚗", "color": "#45B7D1"},
            {"name": "Utilities", "icon": "💡", "color": "#96CEB4"},
            {"name": "Entertainment", "icon": "🎬", "color": "#FFEAA7"},
            {"name": "Shopping", "icon": "🛍️", "color": "#DDA0DD"},
            {"name": "Healthcare", "icon": "🏥", "color": "#98D8C8"},
            {"name": "Education", "icon": "📚", "color": "#F7DC6F"},
            {"name": "Rent & Housing", "icon": "🏠", "color": "#BB8FCE"},
            {"name": "Insurance", "icon": "🛡️", "color": "#85C1E9"},
            {"name": "Investments", "icon": "📈", "color": "#82E0AA"},
            {"name": "Income", "icon": "💰", "color": "#22C55E"},
            {"name": "Salary", "icon": "💵", "color": "#2ECC71"},
            {"name": "Transfers", "icon": "🔄", "color": "#AED6F1"},
            {"name": "EMI & Loans", "icon": "🏦", "color": "#F1948A"},
            {"name": "Subscriptions", "icon": "📱", "color": "#D7BDE2"},
            {"name": "Travel", "icon": "✈️", "color": "#F0B27A"},
            {"name": "Uncategorized", "icon": "❓", "color": "#9CA3AF"},
            {"name": "Other", "icon": "📋", "color": "#D5DBDB"},
        ]

        existing_names = {
            row[0] for row in db.query(Category.name).filter(Category.is_system == True).all()
        }

        added = 0
        for cat_data in default_categories:
            if cat_data["name"] not in existing_names:
                category = Category(
                    name=cat_data["name"],
                    icon=cat_data["icon"],
                    color=cat_data["color"],
                    is_system=True,
                    user_id=None,
                )
                db.add(category)
                added += 1

        if added > 0:
            db.commit()
            logger.info(f"Seeded {added} new default categories")
    except Exception as e:
        logger.error(f"Error seeding categories: {e}")
        db.rollback()
    finally:
        db.close()


app = FastAPI(
    title="WhereIsMyMoneyGoing",
    description="Personal finance tracker - analyze your bank statements and track spending",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(classification.router, prefix="/api/v1/classify")
app.include_router(insights.router, prefix="/api/v1")
app.include_router(budgets.router, prefix="/api/v1")
app.include_router(ai_summary.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/health/ml")
def ml_health():
    """ML model health check - reports whether the model is loaded in memory."""
    from app.services.classification.ml_classifier import _pipeline_singleton
    return {
        "model_loaded": _pipeline_singleton is not None,
        "model": "valhalla/distilbart-mnli-12-3" if _pipeline_singleton else None,
    }


@app.get("/")
def root():
    """Root endpoint with API info."""
    return {
        "app": "WhereIsMyMoneyGoing",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
