"""
FastAPI application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.database import db
# Modules stubs (pas encore implémentés — commentés temporairement)
# from app.modules.documents_ingestion.routes import router as documents_router
# from app.modules.education_research.routes import router as education_router
# from app.modules.finance_partnerships_hr.routes import router as finance_router
# from app.modules.environment_infrastructure.routes import router as environment_router
# from app.modules.chatbot_automation.routes import router as chatbot_router

# Modules actifs
from app.modules.kpis.routes import router as kpi_router
from app.modules.academic.routes import router as academic_router

# Initialize FastAPI app
app = FastAPI(
    title="Hack4Ucar AI Modules",
    description="Domain-first AI modules for integrated university management",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
# app.include_router(documents_router, prefix="/api/v1/documents", tags=["documents"])
# app.include_router(education_router, prefix="/api/v1/education", tags=["education"])
# app.include_router(finance_router, prefix="/api/v1/finance", tags=["finance"])
# app.include_router(environment_router, prefix="/api/v1/environment", tags=["environment"])
# app.include_router(chatbot_router, prefix="/api/v1/chatbot", tags=["chatbot"])
app.include_router(kpi_router, tags=["KPIs"])
app.include_router(academic_router, tags=["Academic AI"])


@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    try:
        await db.connect()
        print("✓ Application startup complete")
    except Exception as e:
        print(f"✗ Startup error: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    await db.disconnect()
    print("✓ Application shutdown complete")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Hack4Ucar AI Modules",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
