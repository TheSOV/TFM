import requests
from pprint import pprint
from typing import List, Dict, Optional

def search_dockerhub_images(
    query: str,
    page_size: int = 50,
    max_pages: int = 5,
    official_only: Optional[bool] = None,
    verified_only: Optional[bool] = None,
    sort_by_pulls: bool = True,
) -> List[Dict]:
    """Search Docker Hub repositories.

    Parameters
    ----------
    query : str
        Search term.
    page_size : int, optional
        Results per page (default 50).
    max_pages : int, optional
        Maximum number of pages to fetch (default 5).
    official_only : bool | None, optional
        Filter by *official* flag. If True, return **only** official images.
        If False, return **only** non-official images. If ``None`` (default)
        include both.
    verified_only : bool | None, optional
        Filter by *verified* publisher flag. Behaviour is analogous to
        *official_only*.
    sort_by_pulls : bool, optional
        Sort the final list by ``pulls`` descending (default True).

    Returns
    -------
    List[Dict]
        List of repository dictionaries with keys: ``full_name``,
        ``description``, ``official``, ``verified``, ``stars``, ``pulls``,
        ``updated``.
    """

    all_results: List[Dict] = []

    for page in range(1, max_pages + 1):
        url = (
            "https://hub.docker.com/v2/search/repositories/"
            f"?query={query}&page_size={page_size}&page={page}"
        )
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            print(f"Failed to fetch page {page}: {response.status_code}")
            break

        data = response.json()

        for repo in data.get("results", []):
            owner = repo.get("repo_owner") or repo.get("namespace", "")
            name = repo.get("repo_name") or repo.get("name")
            full_name = f"{owner}/{name}" if owner else name

            info = {
                "full_name": full_name,
                "description": repo.get("short_description")
                or repo.get("description", ""),
                "official": repo.get("is_official", False),
                "verified": repo.get("is_verified", False),
                "stars": repo.get("star_count", 0),
                "pulls": repo.get("pull_count", 0),
                "updated": repo.get("last_updated", ""),
            }

            # Apply filters if set
            if (
                (official_only is None or info["official"] == official_only)
                and (verified_only is None or info["verified"] == verified_only)
            ):
                all_results.append(info)

        # Stop if no next page
        if not data.get("next"):
            break

    # Sort by pulls descending if requested
    if sort_by_pulls:
        all_results.sort(key=lambda x: x["pulls"], reverse=True)

    return all_results


# Example usage
if __name__ == "__main__":
    query = "redis"
    # Get only official images, already sorted by pulls
    results = search_dockerhub_images(query, official_only=True)

    print("\n--- Top Official Images (by pulls) ---")
    for r in results[:10]:  # show top 10
        print(r)
