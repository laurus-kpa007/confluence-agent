"""Confluence publisher - creates/updates pages via REST API."""
import logging
from typing import Optional, List
import httpx

logger = logging.getLogger(__name__)


class ConfluencePublisher:
    """Publish content to Confluence."""

    def __init__(self, url: str, username: str, api_token: str, ssl_verify: bool = True, auth_type: str = "basic"):
        self.url = url.rstrip("/")
        self.ssl_verify = ssl_verify
        self.auth_type = auth_type.lower()

        if self.auth_type == "bearer":
            # Confluence Server/Data Center with Personal Access Token (PAT)
            self.auth = None
            self._extra_headers = {
                "Authorization": f"Bearer {api_token}",
                "X-Atlassian-Token": "no-check",
            }
        else:
            # Atlassian Cloud: Basic Auth (email:api_token)
            self.auth = (username, api_token)
            self._extra_headers = {
                "X-Atlassian-Token": "no-check",
            }

        logger.debug("ConfluencePublisher init: url=%s, username=%s, auth_type=%s, ssl_verify=%s",
                      self.url, username, self.auth_type, ssl_verify)

    def _merge_headers(self, headers: Optional[dict] = None) -> dict:
        merged = dict(self._extra_headers)
        if headers:
            merged.update(headers)
        return merged

    def _check_html_response(self, resp: httpx.Response):
        """Detect when Confluence returns HTML login page instead of JSON."""
        content_type = resp.headers.get("content-type", "")
        if "text/html" in content_type and resp.status_code < 400:
            # Confluence Server redirected to login page (auth failure disguised as 200)
            raise ConfluenceAuthError(
                "Confluence가 로그인 페이지를 반환했습니다. "
                "인증 설정을 확인하세요:\n"
                "  - Server/DC 개인 토큰(PAT): CONFLUENCE_AUTH_TYPE=bearer\n"
                "  - Basic Auth가 서버에서 비활성화되었을 수 있습니다"
            )

    async def list_spaces(self, limit: int = 50) -> List[dict]:
        """List all accessible spaces."""
        url = f"{self.url}/rest/api/space"
        logger.debug("GET %s (ssl_verify=%s, auth_type=%s)", url, self.ssl_verify, self.auth_type)
        async with httpx.AsyncClient(timeout=15.0, verify=self.ssl_verify) as client:
            resp = await client.get(
                url,
                params={"limit": limit, "type": "global"},
                auth=self.auth,
                headers=self._merge_headers(),
            )
            logger.debug("list_spaces response: status=%d, content-type=%s",
                         resp.status_code, resp.headers.get("content-type", ""))
            self._check_html_response(resp)
            resp.raise_for_status()
            return [
                {"key": s["key"], "name": s["name"], "id": s.get("id")}
                for s in resp.json().get("results", [])
            ]

    async def list_pages(self, space_key: str, parent_id: Optional[str] = None, limit: int = 50) -> List[dict]:
        """List pages in a space, optionally under a parent."""
        async with httpx.AsyncClient(timeout=15.0, verify=self.ssl_verify) as client:
            if parent_id:
                url = f"{self.url}/rest/api/content/{parent_id}/child/page"
                resp = await client.get(
                    url,
                    params={"limit": limit, "expand": "version"},
                    auth=self.auth,
                    headers=self._merge_headers(),
                )
            else:
                url = f"{self.url}/rest/api/content"
                resp = await client.get(
                    url,
                    params={
                        "spaceKey": space_key,
                        "type": "page",
                        "limit": limit,
                        "expand": "ancestors,version",
                    },
                    auth=self.auth,
                    headers=self._merge_headers(),
                )
            logger.debug("list_pages response: status=%d, url=%s", resp.status_code, url)
            self._check_html_response(resp)
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
        async with httpx.AsyncClient(timeout=15.0, verify=self.ssl_verify) as client:
            resp = await client.get(
                f"{self.url}/rest/api/content/search",
                params={"cql": cql, "limit": limit},
                auth=self.auth,
                headers=self._merge_headers(),
            )
            self._check_html_response(resp)
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
        all_pages = await self.list_pages(space_key, limit=100)
        root_pages = [p for p in all_pages if p["parent_id"] is None]

        if depth <= 1:
            return root_pages

        tree = []
        async with httpx.AsyncClient(timeout=15.0, verify=self.ssl_verify) as client:
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

        logger.debug("Creating page: title=%s, space=%s, parent_id=%s", title, space_key, parent_id)
        async with httpx.AsyncClient(timeout=30.0, verify=self.ssl_verify) as client:
            resp = await client.post(
                f"{self.url}/rest/api/content",
                json=payload,
                auth=self.auth,
                headers=self._merge_headers({"Content-Type": "application/json"}),
            )
            logger.debug("Create page response: status=%d", resp.status_code)
            self._check_html_response(resp)
            resp.raise_for_status()
            result = resp.json()
            logger.info("Page created: id=%s, title=%s", result["id"], result["title"])
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
        logger.debug("Updating page: id=%s, title=%s", page_id, title)
        async with httpx.AsyncClient(timeout=30.0, verify=self.ssl_verify) as client:
            resp = await client.get(
                f"{self.url}/rest/api/content/{page_id}",
                auth=self.auth,
                headers=self._merge_headers(),
            )
            self._check_html_response(resp)
            resp.raise_for_status()
            current = resp.json()
            version = current["version"]["number"] + 1

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
                headers=self._merge_headers({"Content-Type": "application/json"}),
            )
            self._check_html_response(resp)
            resp.raise_for_status()
            result = resp.json()
            return {
                "id": result["id"],
                "title": result["title"],
                "url": f"{self.url}{result['_links']['webui']}",
            }


class ConfluenceAuthError(Exception):
    """Raised when Confluence returns a login page instead of API response."""
    pass
