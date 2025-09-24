from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from .database import init_db, get_db, engine
from .models import Property
from .schemas import PropertyCreate, PropertyResponse
from .routers import commute, session, chat, stations, auth, pins, explore, hazard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    init_db()
    yield
    logger.info("Shutting down...")
    engine.dispose()


app = FastAPI(
    title="A2A Estate API",
    description="Real Estate Management API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターを登録
app.include_router(auth.router)
app.include_router(commute.router)
app.include_router(session.router)
app.include_router(chat.router)
app.include_router(stations.router)
app.include_router(pins.router)
app.include_router(explore.router)
app.include_router(hazard.router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to A2A Estate API",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }


@app.get("/health")
async def health_check():
    try:
        from sqlalchemy import text
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "environment": os.getenv("ENVIRONMENT", "development")
    }




@app.post("/api/v1/properties", response_model=PropertyResponse, status_code=201)
async def create_property(property: PropertyCreate):
    db = next(get_db())
    try:
        db_property = Property(
            title=property.title,
            description=property.description,
            price=property.price,
            location=property.location,
            bedrooms=property.bedrooms,
            bathrooms=property.bathrooms,
            area_sqft=property.area_sqft,
            property_type=property.property_type,
            status=property.status
        )
        db.add(db_property)
        db.commit()
        db.refresh(db_property)
        return PropertyResponse.from_orm(db_property)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create property: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@app.get("/api/v1/properties", response_model=list[PropertyResponse])
async def list_properties(
    skip: int = 0,
    limit: int = 100,
    property_type: Optional[str] = None,
    status: Optional[str] = None
):
    db = next(get_db())
    try:
        query = db.query(Property)
        if property_type:
            query = query.filter(Property.property_type == property_type)
        if status:
            query = query.filter(Property.status == status)

        properties = query.offset(skip).limit(limit).all()
        return [PropertyResponse.from_orm(p) for p in properties]
    finally:
        db.close()


@app.get("/api/v1/properties/{property_id}", response_model=PropertyResponse)
async def get_property(property_id: int):
    db = next(get_db())
    try:
        property = db.query(Property).filter(Property.id == property_id).first()
        if not property:
            raise HTTPException(status_code=404, detail="Property not found")
        return PropertyResponse.from_orm(property)
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)