import httpx
from typing import List, Dict, Any
from app.core.config import get_settings


settings = get_settings()


async def search_jobs_with_jsearch(
    title: str,
    company: str | None = None,
    industry: str | None = None,
    location: str | None = None,
    num_pages: int = 1,
) -> List[Dict[str, Any]]:
    """Call RapidAPI JSearch to search for jobs.

    This focuses on the core fields you need for the UI.
    """

    if not settings.JSEARCH_API_KEY:
        return []

    base_url = "https://jsearch.p.rapidapi.com/search"

    query_parts: list[str] = []
    if title:
        query_parts.append(title)
    if company:
        query_parts.append(company)
    if industry:
        query_parts.append(industry)

    query = " ".join(query_parts).strip()

    # Ask JSearch for many pages to approach 500+ results when available.
    params = {
        "query": query or "software engineer",
        "page": 1,
        "num_pages": num_pages,
        "country": "us",
    }

    headers = {
        "x-rapidapi-key": settings.JSEARCH_API_KEY,
        "x-rapidapi-host": settings.JSEARCH_API_HOST,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(base_url, headers=headers, params=params)
    except httpx.TimeoutException:
        # Network timeout when calling JSearch; surface as no jobs so the UI
        # can show a friendly error instead of a 500 traceback.
        return []
    except httpx.HTTPError:
        # Any other HTTP client error, also treated as "no jobs".
        return []

    if resp.status_code != 200:
        return []

    data = resp.json()
    results = data.get("data", [])

    jobs: List[Dict[str, Any]] = []
    for item in results:
        jobs.append(
            {
                "id": item.get("job_id"),
                "title": item.get("job_title"),
                "company": item.get("employer_name"),
                "location": item.get("job_city") or item.get("job_country") or "",
                "industry": item.get("job_industry"),
                "url": item.get("job_apply_link") or item.get("job_google_link"),
            }
        )

    return jobs
