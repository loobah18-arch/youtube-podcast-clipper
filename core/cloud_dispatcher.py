import json
import subprocess
from typing import Dict, Any
from config.settings import DEFAULT_CLOUD_WORKFLOW, DEFAULT_GITHUB_REPO

class CloudDispatcher:
    """
    Prepares clip specifications and orchestrates remote GitHub Actions rendering,
    ensuring zero heavy FFmpeg video processing runs on the physical phone.
    """

    def __init__(self, repo: str = DEFAULT_GITHUB_REPO, workflow: str = DEFAULT_CLOUD_WORKFLOW):
        self.repo = repo
        self.workflow = workflow

    def generate_clip_spec(self, video_url: str, clip: Dict[str, Any]) -> Dict[str, Any]:
        """Builds standardized cloud-ready JSON specification for video rendering."""
        return {
            "source_url": video_url,
            "start_time": clip["start"],
            "end_time": clip["end"],
            "duration": clip["duration"],
            "title": clip.get("viral_title", "Podcast Viral Clip"),
            "aspect_ratio": "9:16",
            "render_preset": "vertical_shorts_karaoke",
            "score": clip.get("score", 85.0)
        }

    def get_dispatch_command(self, clip_spec: Dict[str, Any]) -> str:
        """Returns the exact gh CLI command to trigger cloud rendering."""
        spec_json_str = json.dumps(clip_spec)
        return (
            f"gh workflow run {self.workflow} "
            f"--repo {self.repo} "
            f"-f video_url=\"{clip_spec['source_url']}\" "
            f"-f start_time=\"{clip_spec['start_time']}\" "
            f"-f end_time=\"{clip_spec['end_time']}\" "
            f"-f title=\"{clip_spec['title']}\""
        )

    def dispatch(self, clip_spec: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
        """Dispatches cloud workflow or returns execution preview."""
        cmd_str = self.get_dispatch_command(clip_spec)
        if dry_run:
            return {
                "status": "ready_for_cloud",
                "mode": "dry_run",
                "command": cmd_str,
                "spec": clip_spec
            }

        try:
            cmd = [
                "gh", "workflow", "run", self.workflow,
                "--repo", self.repo,
                "-f", f"video_url={clip_spec['source_url']}",
                "-f", f"start_time={clip_spec['start_time']}",
                "-f", f"end_time={clip_spec['end_time']}",
                "-f", f"title={clip_spec['title']}"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {
                "status": "dispatched",
                "output": res.stdout.strip(),
                "spec": clip_spec
            }
        except subprocess.CalledProcessError as e:
            return {
                "status": "error",
                "error": e.stderr.strip(),
                "spec": clip_spec
            }
