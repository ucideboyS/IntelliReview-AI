from pydantic import BaseModel, Field


class ReviewResponse(BaseModel):
    readability:     float = Field(..., ge=0, le=10)
    performance:     float = Field(..., ge=0, le=10)
    maintainability: float = Field(..., ge=0, le=10)
    security:        float = Field(..., ge=0, le=10)
    best_practices:  float = Field(..., ge=0, le=10)
    overall_score:   float = Field(..., ge=0, le=10)
    issues:          str
    ai_explanation:  str
    fixed_code:      str