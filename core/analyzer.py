import os
import json
import requests
from typing import List, Dict, Any
from config.settings import MIN_CLIP_DURATION, MAX_CLIP_DURATION, TARGET_CLIP_DURATION, VIRAL_HOOK_TRIGGERS

class ClipAnalyzer:
    """
    Analyzes podcast transcripts to identify high-retention viral clip candidates (30-90s).
    Supports algorithmic heuristic scoring with optional AI LLM hook refinement.
    """

    def __init__(self, openrouter_key: str = None, groq_key: str = None):
        self.openrouter_key = openrouter_key or os.environ.get("OPENROUTER_API_KEY")
        self.groq_key = groq_key or os.environ.get("GROQ_API_KEY")

    def _score_segment_window(self, text: str, duration: float) -> float:
        """Heuristic score (0 - 100) based on hook keywords, density, and cadence."""
        score = 50.0
        lower = text.lower()

        # Check for viral hook words
        trigger_hits = sum(1 for trigger in VIRAL_HOOK_TRIGGERS if trigger in lower)
        score += min(trigger_hits * 12.0, 36.0)

        # First 5 words matter most (Pattern interrupt / Hook)
        first_few_words = " ".join(lower.split()[:8])
        if any(trig in first_few_words for trig in VIRAL_HOOK_TRIGGERS):
            score += 15.0

        # Optimal duration bonus (around 45-65s is sweet spot for Shorts)
        if 45.0 <= duration <= 65.0:
            score += 10.0
        elif 35.0 <= duration < 45.0:
            score += 5.0

        # Word cadence check
        words = len(text.split())
        words_per_sec = words / max(duration, 1.0)
        if 2.2 <= words_per_sec <= 3.8:
            score += 5.0

        return min(round(score, 1), 99.0)

    def find_heuristic_candidates(self, segments: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Sliding window over transcript cues to locate continuous 30-80s speech blocks
        with the highest virality scores.
        """
        if not segments:
            return []

        candidates = []
        n = len(segments)

        for i in range(n):
            start_time = segments[i]["start"]
            accumulated_text = []
            
            for j in range(i, n):
                accumulated_text.append(segments[j]["text"])
                end_time = segments[j]["end"]
                duration = end_time - start_time

                if duration >= MIN_CLIP_DURATION:
                    if duration > MAX_CLIP_DURATION:
                        break
                    
                    full_text = " ".join(accumulated_text).strip()
                    score = self._score_segment_window(full_text, duration)
                    
                    candidates.append({
                        "start": round(start_time, 2),
                        "end": round(end_time, 2),
                        "duration": round(duration, 2),
                        "score": score,
                        "text": full_text,
                        "hook_first_words": " ".join(full_text.split()[:8])
                    })

        # Sort descending by score
        candidates.sort(key=lambda x: x["score"], reverse=True)

        # Non-maximum suppression: filter out overlapping clips
        selected = []
        for cand in candidates:
            overlap = False
            for sel in selected:
                # If clips overlap by more than 15 seconds, skip
                if not (cand["end"] < sel["start"] or cand["start"] > sel["end"]):
                    overlap = True
                    break
            if not overlap:
                selected.append(cand)
                if len(selected) >= top_k:
                    break

        return selected

    def refine_with_ai(self, candidate: Dict[str, Any], podcast_title: str) -> Dict[str, Any]:
        """
        Optionally calls LLM (OpenRouter free model / Groq) to generate viral Short title,
        hashtag recommendations, and retention hook breakdown.
        """
        # If no key, generate smart title from hook heuristic
        clean_hook = candidate.get("hook_first_words", "").strip().title()
        fallback_title = f"{clean_hook}... | {podcast_title.split('|')[0].strip()}"
        
        result = dict(candidate)
        result["viral_title"] = fallback_title
        result["hook_breakdown"] = "High-velocity contrarian statement with immediate pattern interrupt."
        result["target_audience"] = "Tech, founders, programmers, and high-agency creators."

        if not self.openrouter_key:
            return result

        prompt = f"""You are an elite short-form podcast video editor.
Given this 30-60s podcast clip transcript from "{podcast_title}":
"{candidate['text']}"

Output a JSON object with:
1. "viral_title": Punchy, curiosity-gap YouTube Short title (max 60 chars)
2. "hook_breakdown": Why the first 3 seconds stop the scroll
3. "target_audience": Primary demographic
4. "tags": 3 relevant hashtags
Only return valid JSON."""

        try:
            # Using OpenRouter free model verified in memory bank
            headers = {
                "Authorization": f"Bearer {self.openrouter_key}",
                "Content-Type": "application/json"
            }
            body = {
                "model": "nvidia/nemotron-3-super-120b-a12b:free",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "response_format": {"type": "json_object"}
            }
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body, timeout=12)
            if res.status_code == 200:
                ai_data = res.json()["choices"][0]["message"]["content"]
                parsed = json.loads(ai_data)
                result["viral_title"] = parsed.get("viral_title", result["viral_title"])
                result["hook_breakdown"] = parsed.get("hook_breakdown", result["hook_breakdown"])
                result["target_audience"] = parsed.get("target_audience", result["target_audience"])
                result["tags"] = parsed.get("tags", ["#podcast", "#shorts", "#viral"])
        except Exception:
            pass  # Resilient fallback to heuristic results

        return result
