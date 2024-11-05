# main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from database import init_db
from Services.car_router import router as car_router
from Services.customer_router import router as customer_router
from Services.location_router import router as location_router  # New import
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Instadrive API",
    description="""
    API for managing Instadrive's domain services including:
    - Customer management
    - Location management
    - Vehicle fleet management
    - Booking services
    """,
    version="1.0.0",
    debug=True
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler for detailed error messages
@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    logger.error(f"Error processing request: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__}
    )

# Include routers
app.include_router(
    customer_router,
    prefix="/api/customers",
    tags=["customers"]
)

# Add location router
app.include_router(
    location_router,
    prefix="/api/locations",
    tags=["locations"]
)

# Add this in the router section:
app.include_router(
    car_router,
    prefix="/api/cars",
    tags=["cars"]
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise

@app.get("/")
async def root():
    return {
        "message": "Welcome to Instadrive API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")