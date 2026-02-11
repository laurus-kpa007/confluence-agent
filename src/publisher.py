"""Confluence publisher - creates/updates pages via REST API."""
from typing import Optional, List
import httpx


class ConfluencePublisher:
    """Publish content to Confluence."""

    def __init__(self, url: str, username: str, api_token: str):
        self.url = url.rstrip("/")
        self.auth = (username, api_token)

    async def list_spaces(self, limit: int = 50) -> List[dict]:
        """List all accessible spaces."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.url}/rest/api/space",
                params={"limit": limit, "type": "global"},
                auth=self.auth,
            )
            resp.raise_for_status()
            return [
                {"key": s["key"], "name": s["name"], "id": s.get("id")}
                for s in resp.json().get("results", [])
            ]

    async def list_pages(self, space_key: str, parent_id: Optional[str] = None, limit: int = 50) -> List[dict]:
        """List pages in a space, optionally under a parent."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            if parent_id:
                # Get child pages of a specific page
                resp = await client.get(
                    f"{self.url}/rest/api/content/{parent_id}/child/page",
                    params={"limit": limit, "expand": "version"},
                    auth=self.auth,
                )
            else:
                # Get top-level pages in space
                resp = await client.get(
                    f"{self.url}/rest/api/content",
                    params={
                        "spaceKey": space_key,
                        "type": "page",
                        "limit": limit,
                        "expand": "ancestors,version",
                    },
                    auth=self.auth,
                )
            resp.raise_for_status()
            results = resp.json().get("results", [])
            pages = []
            for p in results:
                ancestors = p.get("ancestors", [])
                pages.append({
                    "id": p["id"],
                    "title": p["title"],
                    "parent_id": ancestors[-1]["id"] if ancestors else None,
                    "url": f"{self.url}{p.get('_links', {}).get('webui', '')}",
                })
            return pages

    async def search_pages(self, query: str, space_key: Optional[str] = None, limit: int = 20) -> List[dict]:
        """Search pages by title/content using CQL."""
        cql = f'type=page AND title~"{query}"'
        if space_key:
            cql += f' AND space="{space_key}"'
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.url}/rest/api/content/search",
                params={"cql": cql, "limit": limit},
                auth=self.auth,
            )
            resp.raise_for_status()
            return [
                {
                    "id": p["id"],
                    "title": p["title"],
                    "url": f"{self.url}{p.get('_links', {}).get('webui', '')}",
                }
                for p in resp.json().get("results", [])
            ]

    async def get_page_tree(self, space_key: str, depth: int = 2) -> List[dict]:
        """Get page tree structure for a space."""
        # Get root pages (no ancestors)
        all_pages = await self.list_pages(space_key, limit=100)
        root_pages = [p for p in all_pages if p["parent_id"] is None]

        if depth <= 1:
            return root_pages

        # Get children for each root
        tree = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            for root in root_pages:
                children = await self.list_pages(space_key, parent_id=root["id"])
                tree.append({**root, "children": children})
        return tree

    async def create_page(
        self,
        title: str,
        body: str,
        space_key: str,
        parent_id: Optional[str] = None,
    ) -> dict:
        """Create a new Confluence page."""
        payload = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": body,
                    "representation": "storage",
                }
            },
        }
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.url}/rest/api/content",
                json=payload,
                auth=self.auth,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            result = resp.json()
            return {
                "id": result["id"],
                "title": result["title"],
                "url": f"{self.url}{result['_links']['webui']}",
            }

    async def update_page(
        self,
        page_id: str,
        title: str,
        body: str,
    ) -> dict:
        """Update an existing Confluence page."""
        # Get current version
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.url}/rest/api/content/{page_id}",
                auth=self.auth,
            )
            resp.raise_for_status()
            current = resp.json()
            version = current["version"]["number"] + 1

            # Update
            payload = {
                "type": "page",
                "title": title,
                "body": {
                    "storage": {
                        "value": body,
                        "representation": "storage",
                    }
                },
                "version": {"number": version},
            }
            resp = await client.put(
                f"{self.url}/rest/api/content/{page_id}",
                json=payload,
                auth=self.auth,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            result = resp.json()
            return {
                "id": result["id"],
                "title": result["title"],
                "url": f"{self.url}{result['_links']['webui']}",
            }
