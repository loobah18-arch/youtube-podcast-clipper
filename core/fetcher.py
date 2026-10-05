import os
import glob
import json
import subprocess
from typing import Dict, Any, Optional
from config.settings import TMP_DIR
from core.vtt_parser import parse_vtt

class PodcastFetcher:
    """
    Fetches YouTube podcast metadata and transcripts using the Agent Reach
    lightweight extraction path (no video downloads, minimal memory).
    """

    def __init__(self, tmp_dir: str = TMP_DIR):
        self.tmp_dir = tmp_dir
        os.makedirs(self.tmp_dir, exist_ok=True)

    def fetch_metadata(self, url: str) -> Dict[str, Any]:
        """Fetches video metadata, title, duration, chapters and author via yt-dlp."""
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-playlist",
            url
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        return {
            "id": data.get("id"),
            "title": data.get("title"),
            "channel": data.get("channel"),
            "duration": data.get("duration", 0),
            "view_count": data.get("view_count", 0),
            "thumbnail": data.get("thumbnail"),
            "chapters": data.get("chapters", []),
            "url": f"https://www.youtube.com/watch?v={data.get('id')}"
        }

    def fetch_transcript(self, url: str, video_id: str, lang: str = "en") -> list:
        """
        Fetches transcript / subtitles without downloading video bytes.
        Returns parsed list of deduplicated cue segments.
        """
        out_template = os.path.join(self.tmp_dir, f"sub_{video_id}_%(id)s")
        cmd = [
            "yt-dlp",
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", lang,
            "--skip-download",
            "-o", out_template,
            url
        ]
        
        subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        # Search for generated .vtt files matching the prefix
        pattern = os.path.join(self.tmp_dir, f"sub_{video_id}*.vtt")
        matched = glob.glob(pattern)
        
        if not matched:
            return []

        vtt_file = matched[0]
        try:
            with open(vtt_file, "r", encoding="utf-8") as f:
                content = f.read()
            return parse_vtt(content)
        finally:
            # Clean up temporary subtitle files
            for path in matched:
                try:
                    os.remove(path)
                except OSError:
                    pass

    def fetch_podcast_package(self, url: str) -> Dict[str, Any]:
        """One-stop fetcher returning metadata and clean transcript segments."""
        meta = self.fetch_metadata(url)
        vid_id = meta.get("id")
        segments = self.fetch_transcript(url, vid_id)
        return {
            "metadata": meta,
            "segments_count": len(segments),
            "segments": segments
        }
