"""ECHR Case Law API Routes.

Provides endpoints for accessing European Court of Human Rights case law
from the ECHR Open Data API with local caching.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.models.echr_models import (
    ECHRCase,
    ECHRCaseResponse,
    ECHRCaseSummary,
    ECHRConclusion,
    ECHRDocument,
    ECHRSearchRequest,
    ECHRSearchResponse,
    ECHRStatsResponse,
    ECHRSubjectClassification,
    ECHRSyncStatus,
)
from app.models.schemas import ErrorResponse
from app.services.echr_service import (
    ECHRAPIError,
    ECHRService,
    get_initialized_echr_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/echr",
    tags=["ECHR Case Law"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "ECHR API unavailable"},
    },
)


# ============================================================================
# Case Endpoints
# ============================================================================


@router.get("/cases", response_model=ECHRSearchResponse)
async def list_cases(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    articles: Optional[str] = Query(
        None, description="Filter by Convention articles (comma-separated, e.g., '6,8')"
    ),
    respondent: Optional[str] = Query(
        None, description="Filter by respondent state (e.g., 'TURKEY')"
    ),
    query: Optional[str] = Query(
        None, description="Free text search in case name"
    ),
    importance: Optional[int] = Query(
        None, ge=1, le=4, description="Filter by importance level (1=key, 4=low)"
    ),
    use_cache: bool = Query(
        True, description="Use local cache (faster, may be slightly outdated)"
    ),
):
    """
    List ECHR cases with optional filters.

    Returns a paginated list of case summaries. Use filters to narrow results.

    **Example Request:**
    ```
    GET /api/echr/cases?articles=6&respondent=TURKEY&limit=10
    ```

    **Example Response:**
    ```json
    {
        "cases": [
            {
                "item_id": "001-57574",
                "application_number": "12345/67",
                "case_name": "CASE OF X v. TURKEY",
                "respondent_state": "TUR",
                "judgment_date": "2020-01-15",
                "articles": ["6", "6-1"],
                "importance_level": 2
            }
        ],
        "total": 150,
        "page": 1,
        "limit": 10,
        "has_more": true
    }
    ```
    """
    try:
        service = await get_initialized_echr_service()

        # Parse articles if provided
        article_list = None
        if articles:
            article_list = [a.strip() for a in articles.split(",") if a.strip()]

        if use_cache:
            # Use local cache for faster response
            cases = service.search_cached_cases(
                query=query,
                articles=article_list,
                respondent=respondent,
                limit=limit,
                offset=(page - 1) * limit,
            )
            total = service.get_cached_case_count()
            has_more = (page * limit) < total
        else:
            # Use API search
            request = ECHRSearchRequest(
                query=query,
                articles=article_list,
                respondent=respondent,
                importance=importance,
                page=page,
                limit=limit,
            )
            response = await service.search_cases(request)
            return response

        return ECHRSearchResponse(
            cases=cases,
            total=total,
            page=page,
            limit=limit,
            has_more=has_more,
        )

    except ECHRAPIError as e:
        logger.error("ECHR API error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ECHR API unavailable: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Error listing ECHR cases: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cases",
        ) from e


@router.get("/cases/{item_id}", response_model=ECHRCaseResponse)
async def get_case(
    item_id: str,
    use_cache: bool = Query(True, description="Use cached data if available"),
):
    """
    Get a specific ECHR case by item ID.

    **Example Request:**
    ```
    GET /api/echr/cases/001-57574
    ```

    **Example Response:**
    ```json
    {
        "case": {
            "item_id": "001-57574",
            "application_number": "12345/67",
            "case_name": "CASE OF X v. TURKEY",
            "ecli": "ECLI:CE:ECHR:2020:0115JUD001234567",
            "judgment_date": "2020-01-15",
            "respondent_state": "TUR",
            "articles": ["6", "6-1", "13"],
            "violations": ["6-1"],
            "non_violations": ["13"],
            "conclusion": "Violation of Article 6-1",
            ...
        },
        "status": "success"
    }
    ```
    """
    try:
        service = await get_initialized_echr_service()
        case = await service.get_case(item_id, use_cache=use_cache)

        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case not found: {item_id}",
            )

        return ECHRCaseResponse(case=case, status="success")

    except HTTPException:
        raise
    except ECHRAPIError as e:
        logger.error("ECHR API error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ECHR API unavailable: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Error getting ECHR case %s: %s", item_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve case",
        ) from e


@router.get("/cases/{item_id}/documents", response_model=List[ECHRDocument])
async def get_case_documents(item_id: str):
    """
    Get documents associated with an ECHR case.

    Returns judgment text, decision documents, etc.

    **Example Request:**
    ```
    GET /api/echr/cases/001-57574/documents
    ```
    """
    try:
        service = await get_initialized_echr_service()
        documents = await service.get_case_documents(item_id)
        return documents

    except ECHRAPIError as e:
        logger.error("ECHR API error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ECHR API unavailable: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Error getting documents for case %s: %s", item_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents",
        ) from e


@router.get("/cases/{item_id}/cited", response_model=List[str])
async def get_cited_applications(item_id: str):
    """
    Get application numbers cited by an ECHR case.

    Useful for finding related cases and building case law networks.

    **Example Request:**
    ```
    GET /api/echr/cases/001-57574/cited
    ```

    **Example Response:**
    ```json
    ["12345/67", "23456/78", "34567/89"]
    ```
    """
    try:
        service = await get_initialized_echr_service()
        cited = await service.get_cited_applications(item_id)
        return cited

    except ECHRAPIError as e:
        logger.error("ECHR API error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ECHR API unavailable: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Error getting cited apps for case %s: %s", item_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cited applications",
        ) from e


# ============================================================================
# Search Endpoint
# ============================================================================


@router.post("/search", response_model=ECHRSearchResponse)
async def search_cases(request: ECHRSearchRequest):
    """
    Advanced search for ECHR cases.

    Supports multiple filters and date ranges.

    **Example Request:**
    ```json
    {
        "articles": ["6", "8"],
        "respondent": "FRANCE",
        "date_from": "2020-01-01",
        "date_to": "2023-12-31",
        "violation": true,
        "page": 1,
        "limit": 20
    }
    ```
    """
    try:
        service = await get_initialized_echr_service()
        response = await service.search_cases(request)
        return response

    except ECHRAPIError as e:
        logger.error("ECHR API error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ECHR API unavailable: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Error searching ECHR cases: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search cases",
        ) from e


# ============================================================================
# Metadata Endpoints
# ============================================================================


@router.get("/stats", response_model=ECHRStatsResponse)
async def get_stats():
    """
    Get ECHR database statistics.

    Returns total case count and last update information.

    **Example Response:**
    ```json
    {
        "total_cases": 16096,
        "last_update": "2024-03-01",
        "build_version": "1.0.0"
    }
    ```
    """
    try:
        service = await get_initialized_echr_service()
        stats = await service.get_stats()
        return stats

    except ECHRAPIError as e:
        logger.error("ECHR API error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ECHR API unavailable: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Error getting ECHR stats: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics",
        ) from e


@router.get("/conclusions", response_model=List[ECHRConclusion])
async def get_conclusions():
    """
    Get all ECHR conclusion types.

    Returns list of possible case conclusions (violation, no-violation, etc.).

    **Example Response:**
    ```json
    [
        {
            "id": "1",
            "article": "6",
            "type": "violation",
            "description": "Violation of Article 6"
        }
    ]
    ```
    """
    try:
        service = await get_initialized_echr_service()
        conclusions = await service.get_conclusions()
        return conclusions

    except ECHRAPIError as e:
        logger.error("ECHR API error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ECHR API unavailable: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Error getting conclusions: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conclusions",
        ) from e


@router.get("/classifications", response_model=List[ECHRSubjectClassification])
async def get_classifications():
    """
    Get ECHR subject classifications.

    Returns the thesaurus of legal subject classifications used in ECHR cases.

    **Example Response:**
    ```json
    [
        {
            "id": "1",
            "code": "6-1",
            "name": "Right to a fair trial",
            "description": "Article 6-1 ECHR"
        }
    ]
    ```
    """
    try:
        service = await get_initialized_echr_service()
        classifications = await service.get_subject_classifications()
        return classifications

    except ECHRAPIError as e:
        logger.error("ECHR API error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ECHR API unavailable: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Error getting classifications: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve classifications",
        ) from e


# ============================================================================
# Cache & Sync Endpoints
# ============================================================================


@router.get("/cache/status", response_model=ECHRSyncStatus)
async def get_cache_status():
    """
    Get local cache synchronization status.

    Returns information about the local cache including last sync time
    and number of cached cases.

    **Example Response:**
    ```json
    {
        "last_sync": "2024-03-01T10:00:00Z",
        "total_cases": 16096,
        "cases_synced": 16096,
        "sync_in_progress": false
    }
    ```
    """
    try:
        service = await get_initialized_echr_service()
        status = service.get_sync_status()
        return status

    except Exception as e:
        logger.error("Error getting cache status: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache status",
        ) from e


@router.post("/cache/sync", response_model=ECHRSyncStatus)
async def sync_cache(
    background_tasks: BackgroundTasks,
    full: bool = Query(False, description="Perform full sync (re-download all cases)"),
):
    """
    Trigger cache synchronization with ECHR API.

    This operation runs in the background. Check /cache/status for progress.

    **Parameters:**
    - `full`: If true, clears cache and re-downloads all cases

    **Example Request:**
    ```
    POST /api/echr/cache/sync?full=false
    ```

    **Note:** A full sync may take several hours due to rate limiting.
    """
    try:
        service = await get_initialized_echr_service()

        # Check if sync is already in progress
        current_status = service.get_sync_status()
        if current_status.sync_in_progress:
            return current_status

        # Start sync in background
        background_tasks.add_task(service.sync_database, full)

        return ECHRSyncStatus(
            last_sync=current_status.last_sync,
            total_cases=current_status.total_cases,
            cases_synced=current_status.cases_synced,
            sync_in_progress=True,
        )

    except Exception as e:
        logger.error("Error starting cache sync: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start sync",
        ) from e


@router.delete("/cache")
async def clear_cache(
    item_id: Optional[str] = Query(None, description="Specific case ID to clear"),
):
    """
    Clear the local cache.

    **Parameters:**
    - `item_id`: If provided, only clears that specific case. Otherwise clears all.

    **Example Request:**
    ```
    DELETE /api/echr/cache?item_id=001-57574
    DELETE /api/echr/cache  # Clear all
    ```
    """
    try:
        service = await get_initialized_echr_service()
        service.clear_cache(item_id)

        return {
            "status": "success",
            "message": f"Cache cleared: {item_id or 'all cases'}",
        }

    except Exception as e:
        logger.error("Error clearing cache: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache",
        ) from e


# ============================================================================
# Health Check
# ============================================================================


@router.get("/health")
async def health_check():
    """
    Check ECHR service health.

    Verifies connectivity to ECHR API and local cache status.
    """
    try:
        service = await get_initialized_echr_service()

        # Check API connectivity
        api_healthy = True
        api_version = None
        try:
            api_version = await service.get_api_version()
        except ECHRAPIError:
            api_healthy = False

        # Check cache
        cache_status = service.get_sync_status()

        return {
            "status": "healthy" if api_healthy else "degraded",
            "api": {
                "healthy": api_healthy,
                "version": api_version,
            },
            "cache": {
                "cases_cached": cache_status.cases_synced,
                "last_sync": cache_status.last_sync.isoformat() if cache_status.last_sync else None,
            },
        }

    except Exception as e:
        logger.error("Health check failed: %s", e)
        return {
            "status": "unhealthy",
            "error": str(e),
        }
