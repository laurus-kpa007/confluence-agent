"""YouTube subtitle/transcript adapter."""
import re
import subprocess
import json
from .base import BaseAdapter, SourceContent


class YouTubeAdapter(BaseAdapter):
    name = "youtube"

    _YT_PATTERN = re.compile(
        r"(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)"
    )

    def can_handle(self, source: str) -> bool:
        return bool(self._YT_PATTERN.search(source))

    async def extract(self, source: str) -> SourceContent:
        # Get video info
        info = self._get_info(source)
        title = info.get("title", source)

        # Extract subtitles (prefer manual, fallback to auto)
        text = self._get_subtitles(source)

        return SourceContent(
            text=text,
            title=title,
            source_url=source,
            source_type="youtube",
            metadata={
                "duration": info.get("duration"),
                "channel": info.get("channel"),
                "upload_date": info.get("upload_date"),
            },
        )

    def _get_info(self, url: str) -> dict:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download", url],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return {"title": url}
        return json.loads(result.stdout)

    def _get_subtitles(self, url: str) -> str:
        """Extract subtitles using yt-dlp."""
        import tempfile, os

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "subs")

            # Try auto-subtitles first (most videos have these)
            result = subprocess.run(
                [
                    "yt-dlp",
                    "--write-auto-sub",
                    "--write-sub",
                    "--sub-lang", "ko,en,ja",
                    "--sub-format", "vtt",
                    "--skip-download",
                    "-o", out_path,
                    url,
                ],
                capture_output=True, text=True, timeout=60,
            )

            # Find the subtitle file
            for f in os.listdir(tmpdir):
                if f.endswith(".vtt"):
                    return self._parse_vtt(os.path.join(tmpdir, f))

        raise ValueError(f"No subtitles found for: {url}")

    def _parse_vtt(self, path: str) -> str:
        """Parse VTT subtitle file to plain text."""
        lines = []
        seen = set()
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip timestamps, headers, empty lines
                if not line or "-->" in line or line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
                    continue
                # Remove HTML tags
                clean = re.sub(r"<[^>]+>", "", line)
                if clean and clean not in seen:
                    seen.add(clean)
                    lines.append(clean)
        return "\n".join(lines)
