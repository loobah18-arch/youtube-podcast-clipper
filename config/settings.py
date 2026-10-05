import os

# Temporary directory handling (safely fall back to $TMPDIR in Termux)
TMP_DIR = os.environ.get("TMPDIR", "/data/data/com.termux/files/usr/tmp" if os.path.exists("/data/data/com.termux/files/usr/tmp") else "/tmp")

# Clip generation constraints
MIN_CLIP_DURATION = 30   # Minimum clip length in seconds
MAX_CLIP_DURATION = 90   # Maximum clip length in seconds (optimal for Shorts < 60s, up to 90s)
TARGET_CLIP_DURATION = 60

# Viral hook keywords for heuristic weighting
VIRAL_HOOK_TRIGGERS = [
    "decades", "secret", "never", "always", "mistake", "truth", "money",
    "future", "die", "kill", "insane", "crazy", "billion", "shocking",
    "stop doing", "the problem is", "nobody talks about", "biggest lie",
    "changed my life", "ai will", "don't believe", "warning", "advice"
]

# Cloud workflow dispatch defaults
DEFAULT_CLOUD_WORKFLOW = "render_podcast_clips.yml"
DEFAULT_GITHUB_REPO = "loobah18-arch/youtube-podcast-clipper"
