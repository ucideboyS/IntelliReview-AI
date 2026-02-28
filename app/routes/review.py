from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.code_request import CodeRequest
from app.services.github_service import analyze_code_with_fix
from app.database import get_db, ReviewRecord

router = APIRouter()


@router.post("/review-code")
async def review_code(request: CodeRequest, db: Session = Depends(get_db)):
    """
    Analyze submitted code using GitHub Models and persist the result to the database.
    """
    try:
        result = await analyze_code_with_fix(request.code, request.language)

        record = ReviewRecord(
            code=request.code,
            language=request.language,
            quality_score=str(result.get("quality_score", "N/A")),
            issues=str(result.get("issues", "")),
            ai_explanation=str(result.get("ai_explanation", "")),
            fixed_code=str(result.get("fixed_code", ""))
        )
        db.add(record)
        db.commit()

        return result

    except Exception as e:
        return {
            "quality_score": "Error",
            "issues": "An unexpected error occurred.",
            "ai_explanation": str(e),
            "fixed_code": "No fix generated."
        }


@router.get("/reviews")
def get_reviews(db: Session = Depends(get_db)):
    """Return the 20 most recent reviews from the database."""
    records = db.query(ReviewRecord).order_by(ReviewRecord.id.desc()).limit(20).all()
    return [
        {
            "id": r.id,
            "language": r.language,
            "quality_score": r.quality_score,
            "issues": r.issues,
            "ai_explanation": r.ai_explanation,
            "fixed_code": r.fixed_code,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in records
    ]