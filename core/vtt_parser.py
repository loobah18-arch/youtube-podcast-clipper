import re
from typing import List, Dict, Any

TIMESTAMP_REGEX = re.compile(r"^(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[.,](\d{3})")
TAG_REGEX = re.compile(r"<[^>]+>")

def timestamp_to_seconds(hours: int, minutes: int, seconds: int, millis: int) -> float:
    """Convert hours, minutes, seconds, milliseconds to total seconds as float."""
    return hours * 3600 + minutes * 60 + seconds + millis / 1000.0

def clean_vtt_text(text: str) -> str:
    """Remove VTT inline timing tags, cue alignments, and normalize whitespace."""
    clean = TAG_REGEX.sub("", text)
    # Remove cue positioning artifacts
    clean = re.sub(r"align:\w+|position:\d+%", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

def parse_vtt(vtt_content: str) -> List[Dict[str, Any]]:
    """
    Parses WebVTT content into deduplicated transcript segments.
    Each segment contains: {'start': float, 'end': float, 'text': str}
    """
    lines = vtt_content.splitlines()
    raw_cues = []
    
    current_start = None
    current_end = None
    current_text_lines = []

    for line in lines:
        line_str = line.strip()
        if not line_str or line_str.startswith("WEBVTT") or line_str.startswith("Kind:") or line_str.startswith("Language:"):
            continue

        match = TIMESTAMP_REGEX.match(line_str)
        if match:
            # Save prior cue if exists
            if current_start is not None and current_text_lines:
                text = clean_vtt_text(" ".join(current_text_lines))
                if text:
                    raw_cues.append({
                        "start": current_start,
                        "end": current_end,
                        "text": text
                    })
            
            # Start new cue
            h1, m1, s1, ms1 = map(int, match.groups()[:4])
            h2, m2, s2, ms2 = map(int, match.groups()[4:])
            current_start = timestamp_to_seconds(h1, m1, s1, ms1)
            current_end = timestamp_to_seconds(h2, m2, s2, ms2)
            current_text_lines = []
        else:
            if current_start is not None:
                cleaned = clean_vtt_text(line_str)
                if cleaned and cleaned not in current_text_lines:
                    current_text_lines.append(cleaned)

    # Flush last cue
    if current_start is not None and current_text_lines:
        text = clean_vtt_text(" ".join(current_text_lines))
        if text:
            raw_cues.append({
                "start": current_start,
                "end": current_end,
                "text": text
            })

    # Deduplicate consecutive overlapping phrases common in YouTube auto-captions
    deduped_segments: List[Dict[str, Any]] = []
    for cue in raw_cues:
        if not deduped_segments:
            deduped_segments.append(cue)
            continue
        
        last = deduped_segments[-1]
        cue_text = cue["text"].strip()
        last_text = last["text"].strip()
        
        # If the new cue text is identical or already contained at the end of last cue
        if cue_text == last_text:
            last["end"] = max(last["end"], cue["end"])
            continue

        # If cue starts with the end of last text, trim overlap
        words_last = last_text.split()
        words_cue = cue_text.split()
        overlap_found = False
        for k in range(min(len(words_last), len(words_cue), 6), 1, -1):
            if words_last[-k:] == words_cue[:k]:
                # Merge into last segment
                merged_text = " ".join(words_last + words_cue[k:])
                last["text"] = merged_text
                last["end"] = max(last["end"], cue["end"])
                overlap_found = True
                break
        
        if not overlap_found:
            deduped_segments.append(cue)

    return deduped_segments
