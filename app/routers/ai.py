import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import require_vendor_or_admin
from app.models.user import User
from app.schemas.ai import AIDescriptionGenerateRequest, AIDescriptionGenerateResponse
from app.schemas.common import APIResponse
from app.services.ai import AIService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Assistant & Generation"])


@router.post(
    "/generate-description",
    response_model=APIResponse[AIDescriptionGenerateResponse],
    status_code=status.HTTP_200_OK,
    summary="Generate marketing copy and SEO tags for a product using Gemini Flash",
)
async def generate_product_description(
    req: AIDescriptionGenerateRequest,
    current_user: User = Depends(require_vendor_or_admin),
) -> APIResponse[AIDescriptionGenerateResponse]:
    """
    Empowers merchants to auto-generate engaging short summaries, formatted product
    descriptions, and SEO tags via Google's Gemini Flash model.
    """
    ai_service = AIService()
    try:
        result = await ai_service.generate_product_description(req)
    except (ValueError, RuntimeError) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )

    return APIResponse(
        success=True,
        message=f"Product copy generated successfully via {result.model_used}",
        data=result,
    )

