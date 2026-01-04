"""ECHR (European Court of Human Rights) Case Law Service.

This service provides access to ECHR case law through:
1. ECHR Open Data API (https://echr-opendata.eu/api/v1/)
2. Local SQLite cache for offline access and reduced API calls

Features:
- Async HTTP client for API requests
- Two-level caching (in-memory LRU + SQLite persistent)
- Bulk sync for initial database population
- Incremental monthly sync for updates
"""

import asyncio
import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.models.echr_models import (
    ECHRCase,
    ECHRCaseSummary,
    ECHRConclusion,
    ECHRDocument,
    ECHRSearchRequest,
    ECHRSearchResponse,
    ECHRStatsResponse,
    ECHRSubjectClassification,
    ECHRSyncStatus,
)

logger = logging.getLogger(__name__)

# API Configuration
ECHR_API_BASE_URL = "https://echr-opendata.eu/api/v1"
DEFAULT_TIMEOUT = 30.0
DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 1000

# Cache Configuration
CACHE_DIR = Path(os.getenv("ECHR_CACHE_DIR", "data/echr_cache"))
CACHE_DB_PATH = CACHE_DIR / "echr_cases.db"
MEMORY_CACHE_SIZE = 500  # Number of cases to keep in memory

# Sync Configuration
SYNC_BATCH_SIZE = 500
SYNC_DELAY_BETWEEN_BATCHES = 1.0  # seconds


class ECHRServiceError(Exception):
    """Base exception for ECHR service errors."""

    pass


class ECHRAPIError(ECHRServiceError):
    """Error communicating with ECHR API."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class ECHRCacheError(ECHRServiceError):
    """Error with local cache operations."""

    pass


class ECHRService:
    """Service for accessing ECHR case law from ECHR Open Data API.

    This service provides:
    - Case search and retrieval
    - Document access (judgments, decisions)
    - Classifications and metadata
    - Local caching with SQLite
    - Bulk and incremental sync

    Usage:
        service = ECHRService()
        await service.initialize()

        # Search cases
        results = await service.search_cases(articles=["6"], respondent="TURKEY")

        # Get specific case
        case = await service.get_case("001-57574")

        # Sync database
        await service.sync_database()
    """

    def __init__(
        self,
        base_url: str = ECHR_API_BASE_URL,
        cache_dir: Optional[Path] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """Initialize the ECHR service.

        Args:
            base_url: ECHR Open Data API base URL
            cache_dir: Directory for SQLite cache (default: data/echr_cache)
            timeout: HTTP request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.cache_dir = cache_dir or CACHE_DIR
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._db_initialized = False
        self._sync_in_progress = False
        self._memory_cache: Dict[str, ECHRCase] = {}

    async def initialize(self) -> None:
        """Initialize the service (HTTP client and database)."""
        await self._init_client()
        self._init_database()

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "ECHRService":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    # ========================================================================
    # HTTP Client Management
    # ========================================================================

    async def _init_client(self) -> None:
        """Initialize the async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "ALLMS-ECHR-Client/1.0",
                },
            )

    async def _get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """Make a GET request to the API.

        Args:
            endpoint: API endpoint (e.g., "/cases")
            params: Query parameters

        Returns:
            JSON response data

        Raises:
            ECHRAPIError: If request fails
        """
        await self._init_client()

        try:
            response = await self._client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error("ECHR API error: %s %s", e.response.status_code, e.response.text)
            raise ECHRAPIError(
                f"API request failed: {e.response.status_code}",
                status_code=e.response.status_code,
            )
        except httpx.RequestError as e:
            logger.error("ECHR API request error: %s", e)
            raise ECHRAPIError(f"Request failed: {str(e)}")

    # ========================================================================
    # Database / Cache Management
    # ========================================================================

    def _init_database(self) -> None:
        """Initialize the SQLite cache database."""
        if self._db_initialized:
            return

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        db_path = self.cache_dir / "echr_cases.db"

        with self._get_db_connection() as conn:
            cursor = conn.cursor()

            # Cases table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cases (
                    item_id TEXT PRIMARY KEY,
                    application_number TEXT,
                    case_name TEXT,
                    ecli TEXT,
                    document_type TEXT,
                    importance_level INTEGER,
                    judgment_date TEXT,
                    decision_date TEXT,
                    respondent_state TEXT,
                    articles TEXT,
                    conclusion TEXT,
                    violations TEXT,
                    non_violations TEXT,
                    language TEXT DEFAULT 'ENG',
                    raw_data TEXT,
                    cached_at TEXT,
                    last_updated TEXT
                )
            """)

            # Documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id TEXT,
                    doc_type TEXT,
                    content TEXT,
                    sections TEXT,
                    cached_at TEXT,
                    FOREIGN KEY (item_id) REFERENCES cases(item_id)
                )
            """)

            # Sync metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_appno ON cases(application_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_respondent ON cases(respondent_state)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_judgment_date ON cases(judgment_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_articles ON cases(articles)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_item_id ON documents(item_id)")

            conn.commit()

        self._db_initialized = True
        logger.info("ECHR cache database initialized at %s", db_path)

    @contextmanager
    def _get_db_connection(self):
        """Get a database connection context manager."""
        db_path = self.cache_dir / "echr_cases.db"
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _cache_case(self, case: ECHRCase) -> None:
        """Cache a case to SQLite database."""
        now = datetime.now(timezone.utc).isoformat()

        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO cases
                (item_id, application_number, case_name, ecli, document_type,
                 importance_level, judgment_date, decision_date, respondent_state,
                 articles, conclusion, violations, non_violations, language,
                 raw_data, cached_at, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    case.item_id,
                    case.application_number,
                    case.case_name,
                    case.ecli,
                    case.document_type,
                    case.importance_level,
                    case.judgment_date.isoformat() if case.judgment_date else None,
                    case.decision_date.isoformat() if case.decision_date else None,
                    case.respondent_state,
                    json.dumps(case.articles),
                    case.conclusion,
                    json.dumps(case.violations),
                    json.dumps(case.non_violations),
                    case.language,
                    case.model_dump_json(),
                    now,
                    now,
                ),
            )
            conn.commit()

        # Also update memory cache
        self._memory_cache[case.item_id] = case

        # Limit memory cache size
        if len(self._memory_cache) > MEMORY_CACHE_SIZE:
            # Remove oldest entries
            oldest_keys = list(self._memory_cache.keys())[: len(self._memory_cache) - MEMORY_CACHE_SIZE]
            for key in oldest_keys:
                del self._memory_cache[key]

    def _get_cached_case(self, item_id: str) -> Optional[ECHRCase]:
        """Get a case from cache (memory first, then SQLite)."""
        # Check memory cache first
        if item_id in self._memory_cache:
            return self._memory_cache[item_id]

        # Check SQLite
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT raw_data FROM cases WHERE item_id = ?", (item_id,))
            row = cursor.fetchone()

            if row:
                case = ECHRCase.model_validate_json(row["raw_data"])
                # Add to memory cache
                self._memory_cache[item_id] = case
                return case

        return None

    def clear_cache(self, item_id: Optional[str] = None) -> None:
        """Clear the cache.

        Args:
            item_id: Specific case to clear, or None to clear all
        """
        if item_id:
            # Clear specific case
            self._memory_cache.pop(item_id, None)
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM cases WHERE item_id = ?", (item_id,))
                cursor.execute("DELETE FROM documents WHERE item_id = ?", (item_id,))
                conn.commit()
        else:
            # Clear all
            self._memory_cache.clear()
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM cases")
                cursor.execute("DELETE FROM documents")
                cursor.execute("DELETE FROM sync_metadata")
                conn.commit()

        logger.info("Cache cleared: %s", item_id or "all")

    # ========================================================================
    # API Methods - Cases
    # ========================================================================

    async def get_case(self, item_id: str, use_cache: bool = True) -> Optional[ECHRCase]:
        """Get a specific case by item ID.

        Args:
            item_id: HUDOC item identifier (e.g., "001-57574")
            use_cache: Whether to check cache first

        Returns:
            ECHRCase or None if not found
        """
        # Check cache first
        if use_cache:
            cached = self._get_cached_case(item_id)
            if cached:
                logger.debug("Cache hit for case %s", item_id)
                return cached

        # Fetch from API
        try:
            data = await self._get(f"/cases/{item_id}")
            case = self._parse_case(data)
            self._cache_case(case)
            return case
        except ECHRAPIError as e:
            if e.status_code == 404:
                return None
            raise

    async def get_cases(
        self,
        page: int = 1,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> Tuple[List[ECHRCaseSummary], int]:
        """Get a paginated list of cases.

        Args:
            page: Page number (1-indexed)
            limit: Results per page (max 1000)

        Returns:
            Tuple of (list of case summaries, total count estimate)
        """
        limit = min(limit, MAX_PAGE_LIMIT)
        data = await self._get("/cases", params={"page": page, "limit": limit})

        cases = []
        for item in data if isinstance(data, list) else []:
            summary = self._parse_case_summary(item)
            cases.append(summary)

        # API doesn't return total count, estimate based on page
        total_estimate = len(cases) + (page - 1) * limit
        if len(cases) == limit:
            total_estimate += limit  # There's probably more

        return cases, total_estimate

    async def search_cases(self, request: ECHRSearchRequest) -> ECHRSearchResponse:
        """Search for cases with filters.

        Note: The ECHR Open Data API has limited search capabilities.
        This method fetches cases and filters locally for advanced queries.

        Args:
            request: Search request with filters

        Returns:
            ECHRSearchResponse with matching cases
        """
        # For now, fetch cases and filter locally
        # TODO: Implement more sophisticated search when API supports it
        all_cases = []
        page = 1
        max_pages = 10  # Limit to avoid too many requests

        while page <= max_pages:
            cases, _ = await self.get_cases(page=page, limit=MAX_PAGE_LIMIT)
            if not cases:
                break
            all_cases.extend(cases)
            if len(cases) < MAX_PAGE_LIMIT:
                break
            page += 1

        # Apply filters
        filtered = self._filter_cases(all_cases, request)

        # Paginate results
        start = (request.page - 1) * request.limit
        end = start + request.limit
        page_results = filtered[start:end]

        return ECHRSearchResponse(
            cases=page_results,
            total=len(filtered),
            page=request.page,
            limit=request.limit,
            has_more=end < len(filtered),
        )

    def _filter_cases(
        self, cases: List[ECHRCaseSummary], request: ECHRSearchRequest
    ) -> List[ECHRCaseSummary]:
        """Apply search filters to case list."""
        filtered = cases

        if request.articles:
            filtered = [c for c in filtered if any(a in c.articles for a in request.articles)]

        if request.respondent:
            filtered = [
                c for c in filtered
                if c.respondent_state and request.respondent.upper() in c.respondent_state.upper()
            ]

        if request.date_from:
            filtered = [
                c for c in filtered
                if (c.judgment_date and c.judgment_date >= request.date_from)
                or (c.decision_date and c.decision_date >= request.date_from)
            ]

        if request.date_to:
            filtered = [
                c for c in filtered
                if (c.judgment_date and c.judgment_date <= request.date_to)
                or (c.decision_date and c.decision_date <= request.date_to)
            ]

        if request.importance:
            filtered = [c for c in filtered if c.importance_level == request.importance]

        if request.document_type:
            filtered = [
                c for c in filtered
                if c.document_type and request.document_type.upper() in c.document_type.upper()
            ]

        if request.query:
            query_lower = request.query.lower()
            filtered = [
                c for c in filtered
                if (c.case_name and query_lower in c.case_name.lower())
                or (c.application_number and query_lower in c.application_number)
            ]

        return filtered

    async def get_case_documents(self, item_id: str) -> List[ECHRDocument]:
        """Get documents associated with a case.

        Args:
            item_id: Case item ID

        Returns:
            List of documents
        """
        try:
            data = await self._get(f"/cases/{item_id}/docs")
            documents = []
            for doc_data in data if isinstance(data, list) else []:
                doc = ECHRDocument(
                    doc_type=doc_data.get("doctype", "UNKNOWN"),
                    doc_id=doc_data.get("docid"),
                    language=doc_data.get("languageisocode", "ENG"),
                    content=doc_data.get("content"),
                )
                documents.append(doc)
            return documents
        except ECHRAPIError as e:
            if e.status_code == 404:
                return []
            raise

    async def get_cited_applications(self, item_id: str) -> List[str]:
        """Get application numbers cited by a case.

        Args:
            item_id: Case item ID

        Returns:
            List of cited application numbers
        """
        try:
            data = await self._get(f"/cases/{item_id}/citedapps")
            return data if isinstance(data, list) else []
        except ECHRAPIError as e:
            if e.status_code == 404:
                return []
            raise

    # ========================================================================
    # API Methods - Metadata
    # ========================================================================

    async def get_stats(self) -> ECHRStatsResponse:
        """Get database statistics."""
        data = await self._get("/stats")
        return ECHRStatsResponse(
            total_cases=data.get("total_cases", 0) if isinstance(data, dict) else 0,
            last_update=None,  # Parse from data if available
            build_version=data.get("version") if isinstance(data, dict) else None,
        )

    async def get_conclusions(self) -> List[ECHRConclusion]:
        """Get all conclusion types."""
        data = await self._get("/conclusions")
        conclusions = []
        for item in data if isinstance(data, list) else []:
            conclusions.append(
                ECHRConclusion(
                    id=str(item.get("id", "")),
                    article=item.get("article"),
                    type=item.get("type"),
                    description=item.get("description"),
                )
            )
        return conclusions

    async def get_subject_classifications(self) -> List[ECHRSubjectClassification]:
        """Get subject classification list."""
        data = await self._get("/scl")
        classifications = []
        for item in data if isinstance(data, list) else []:
            classifications.append(
                ECHRSubjectClassification(
                    id=str(item.get("id", "")),
                    code=item.get("code"),
                    name=item.get("name", ""),
                    description=item.get("description"),
                )
            )
        return classifications

    async def get_api_version(self) -> str:
        """Get API version."""
        data = await self._get("/version")
        return data.get("version", "unknown") if isinstance(data, dict) else str(data)

    # ========================================================================
    # Sync Operations
    # ========================================================================

    async def sync_database(self, full: bool = False) -> ECHRSyncStatus:
        """Synchronize local cache with ECHR Open Data API.

        Args:
            full: If True, re-download all cases. If False, only fetch new cases.

        Returns:
            Sync status with statistics
        """
        if self._sync_in_progress:
            return ECHRSyncStatus(
                sync_in_progress=True,
                error="Sync already in progress",
            )

        self._sync_in_progress = True
        start_time = datetime.now(timezone.utc)
        cases_synced = 0
        error_msg = None

        try:
            self._init_database()

            if full:
                self.clear_cache()

            # Get total cases from stats
            stats = await self.get_stats()
            total_cases = stats.total_cases

            logger.info("Starting ECHR sync: %d total cases", total_cases)

            # Fetch cases in batches
            page = 1
            while True:
                cases, _ = await self.get_cases(page=page, limit=SYNC_BATCH_SIZE)
                if not cases:
                    break

                # Fetch and cache full details for each case
                for summary in cases:
                    try:
                        case = await self.get_case(summary.item_id, use_cache=False)
                        if case:
                            cases_synced += 1
                    except ECHRAPIError as e:
                        logger.warning("Failed to fetch case %s: %s", summary.item_id, e)

                logger.info("Synced %d cases (page %d)", cases_synced, page)

                if len(cases) < SYNC_BATCH_SIZE:
                    break

                page += 1
                # Rate limiting
                await asyncio.sleep(SYNC_DELAY_BETWEEN_BATCHES)

            # Update sync metadata
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO sync_metadata (key, value, updated_at)
                    VALUES ('last_sync', ?, ?)
                """,
                    (start_time.isoformat(), datetime.now(timezone.utc).isoformat()),
                )
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO sync_metadata (key, value, updated_at)
                    VALUES ('cases_synced', ?, ?)
                """,
                    (str(cases_synced), datetime.now(timezone.utc).isoformat()),
                )
                conn.commit()

            logger.info("ECHR sync completed: %d cases", cases_synced)

        except Exception as e:
            error_msg = str(e)
            logger.error("ECHR sync failed: %s", e)
        finally:
            self._sync_in_progress = False

        return ECHRSyncStatus(
            last_sync=start_time,
            total_cases=total_cases if "total_cases" in dir() else 0,
            cases_synced=cases_synced,
            sync_in_progress=False,
            error=error_msg,
        )

    def get_sync_status(self) -> ECHRSyncStatus:
        """Get current sync status from cache metadata."""
        self._init_database()

        with self._get_db_connection() as conn:
            cursor = conn.cursor()

            # Get last sync time
            cursor.execute("SELECT value FROM sync_metadata WHERE key = 'last_sync'")
            row = cursor.fetchone()
            last_sync = datetime.fromisoformat(row["value"]) if row else None

            # Get cases count
            cursor.execute("SELECT COUNT(*) as count FROM cases")
            row = cursor.fetchone()
            cases_synced = row["count"] if row else 0

        return ECHRSyncStatus(
            last_sync=last_sync,
            total_cases=cases_synced,
            cases_synced=cases_synced,
            sync_in_progress=self._sync_in_progress,
        )

    # ========================================================================
    # Local Search (cached data)
    # ========================================================================

    def search_cached_cases(
        self,
        query: Optional[str] = None,
        articles: Optional[List[str]] = None,
        respondent: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[ECHRCaseSummary]:
        """Search locally cached cases.

        This searches the SQLite database without making API calls.

        Args:
            query: Free text search (searches case name and application number)
            articles: Filter by Convention articles
            respondent: Filter by respondent state
            limit: Maximum results
            offset: Result offset for pagination

        Returns:
            List of matching case summaries
        """
        self._init_database()

        sql = "SELECT * FROM cases WHERE 1=1"
        params = []

        if query:
            sql += " AND (case_name LIKE ? OR application_number LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])

        if respondent:
            sql += " AND respondent_state LIKE ?"
            params.append(f"%{respondent}%")

        if articles:
            # Search in JSON array
            article_conditions = []
            for article in articles:
                article_conditions.append("articles LIKE ?")
                params.append(f'%"{article}"%')
            sql += f" AND ({' OR '.join(article_conditions)})"

        sql += " ORDER BY judgment_date DESC NULLS LAST LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append(
                ECHRCaseSummary(
                    item_id=row["item_id"],
                    application_number=row["application_number"],
                    case_name=row["case_name"],
                    respondent_state=row["respondent_state"],
                    judgment_date=datetime.fromisoformat(row["judgment_date"]) if row["judgment_date"] else None,
                    decision_date=datetime.fromisoformat(row["decision_date"]) if row["decision_date"] else None,
                    articles=json.loads(row["articles"]) if row["articles"] else [],
                    importance_level=row["importance_level"],
                    document_type=row["document_type"],
                )
            )

        return results

    def get_cached_case_count(self) -> int:
        """Get the number of cases in the local cache."""
        self._init_database()

        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM cases")
            row = cursor.fetchone()
            return row["count"] if row else 0

    # ========================================================================
    # Parsing Helpers
    # ========================================================================

    def _parse_case(self, data: Dict[str, Any]) -> ECHRCase:
        """Parse API response into ECHRCase model."""
        # Handle date parsing
        judgment_date = None
        if data.get("judgementdate"):
            try:
                judgment_date = datetime.fromisoformat(data["judgementdate"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        decision_date = None
        if data.get("decisiondate"):
            try:
                decision_date = datetime.fromisoformat(data["decisiondate"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        # Parse articles (could be string or list)
        articles = data.get("article", [])
        if isinstance(articles, str):
            articles = [a.strip() for a in articles.split(";") if a.strip()]

        # Parse violations/non-violations
        violations = data.get("violation", [])
        if isinstance(violations, str):
            violations = [v.strip() for v in violations.split(";") if v.strip()]

        non_violations = data.get("nonviolation", [])
        if isinstance(non_violations, str):
            non_violations = [v.strip() for v in non_violations.split(";") if v.strip()]

        return ECHRCase(
            item_id=data.get("itemid", data.get("item_id", "")),
            application_number=data.get("appno"),
            ecli=data.get("ecli"),
            case_name=data.get("docname"),
            title=data.get("title"),
            document_type=data.get("doctype"),
            document_type_branch=data.get("doctypebranch"),
            type_description=data.get("typedescription"),
            importance_level=data.get("importance"),
            judgment_date=judgment_date,
            decision_date=decision_date,
            respondent_state=data.get("respondent"),
            articles=articles,
            conclusion=data.get("conclusion"),
            violations=violations,
            non_violations=non_violations,
            language=data.get("languageisocode", "ENG"),
            scl=data.get("scl"),
            separate_opinion=data.get("separateopinion"),
            originating_body=data.get("originatingbody"),
            cached_at=datetime.now(timezone.utc),
        )

    def _parse_case_summary(self, data: Dict[str, Any]) -> ECHRCaseSummary:
        """Parse API response into ECHRCaseSummary model."""
        judgment_date = None
        if data.get("judgementdate"):
            try:
                judgment_date = datetime.fromisoformat(data["judgementdate"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        decision_date = None
        if data.get("decisiondate"):
            try:
                decision_date = datetime.fromisoformat(data["decisiondate"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        articles = data.get("article", [])
        if isinstance(articles, str):
            articles = [a.strip() for a in articles.split(";") if a.strip()]

        return ECHRCaseSummary(
            item_id=data.get("itemid", data.get("item_id", "")),
            application_number=data.get("appno"),
            case_name=data.get("docname"),
            respondent_state=data.get("respondent"),
            judgment_date=judgment_date,
            decision_date=decision_date,
            articles=articles,
            importance_level=data.get("importance"),
            document_type=data.get("doctype"),
        )


# ============================================================================
# Singleton Instance
# ============================================================================

_echr_service: Optional[ECHRService] = None


def get_echr_service() -> ECHRService:
    """Get or create ECHR service singleton."""
    global _echr_service
    if _echr_service is None:
        _echr_service = ECHRService()
    return _echr_service


async def get_initialized_echr_service() -> ECHRService:
    """Get an initialized ECHR service singleton."""
    service = get_echr_service()
    await service.initialize()
    return service
