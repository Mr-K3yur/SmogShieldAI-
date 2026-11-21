from datetime import datetime, timezone
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="System operational status", json_schema_extra={"example": "healthy"})
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    timestamp_utc: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Current server timestamp in UTC"
    )
    environment: str = Field(..., description="Runtime environment")
    gemini_model_configured: str = Field(..., description="Configured Gemini model")
