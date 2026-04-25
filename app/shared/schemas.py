"""
Shared Pydantic models and schemas
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """Base response model"""

    status: str = Field(..., description="Response status")
    message: Optional[str] = Field(None, description="Response message")
    data: Optional[dict] = Field(None, description="Response data")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "data": {},
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""

    status: str = Field(default="error", description="Error status")
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
            }
        }
