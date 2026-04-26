"""
FastAPI application entry point
"""
 


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.database import db
from app.modules.documents_ingestion.routes import router as documents_router
from app.modules.education_research.routes import router as education_router
from app.modules.finance_partnerships_hr.routes import router as finance_public_router
from app.modules.finance_partnerships_hr.routes import router as finance_router
from app.modules.environment_infrastructure.routes import router as environment_router
from app.modules.chatbot_automation.routes import router as chatbot_router

# Initialize FastAPI app
app = FastAPI(
    title="Hack4Ucar AI Modules",
    description="Domain-first AI modules for integrated university management",
    version="0.1.0",
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
app.include_router(documents_router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(education_router, prefix="/api/v1/education", tags=["education"])
app.include_router(finance_router, prefix="/api/v1/finance", tags=["finance"])
app.include_router(finance_public_router, prefix="/api", tags=["finance-reports"])
app.include_router(environment_router, prefix="/api/v1/environment", tags=["environment"])
app.include_router(chatbot_router, prefix="/api/v1/chatbot", tags=["chatbot"])


def dashboard():
    return FileResponse("dashboard.html")
@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    try:
        await db.connect()
        print("[OK] Application startup complete")
    except Exception as e:
        print(f"[ERROR] Startup error: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    await db.disconnect()
    print("[OK] Application shutdown complete")


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
