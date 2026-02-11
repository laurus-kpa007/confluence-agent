"""Confluence publisher - creates/updates pages via REST API."""
from typing import Optional
import httpx


class ConfluencePublisher:
    """Publish content to Confluence."""

    def __init__(self, url: str, username: str, api_token: str):
        self.url = url.rstrip("/")
        self.auth = (username, api_token)

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
