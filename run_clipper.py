#!/usr/bin/env python3
import sys
import json
import argparse
from core.fetcher import PodcastFetcher
from core.analyzer import ClipAnalyzer
from core.cloud_dispatcher import CloudDispatcher

def main():
    parser = argparse.ArgumentParser(description="Fetch YouTube podcasts and extract viral clip candidates.")
    parser.add_argument("url", help="YouTube video URL or search query (e.g. 'ytsearch1:huberman lab sleep')")
    parser.add_argument("--top-k", type=int, default=3, help="Number of viral clips to extract (default: 3)")
    parser.add_argument("--out", type=str, default=None, help="Output JSON path for clip specs")
    parser.add_argument("--ai", action="store_true", help="Enable AI LLM title and hook refinement")
    args = parser.parse_args()

    print(f"[*] Step 1: Fetching podcast via Agent Reach path: {args.url}")
    fetcher = PodcastFetcher()
    package = fetcher.fetch_podcast_package(args.url)
    
    meta = package["metadata"]
    segments = package["segments"]
    print(f"[+] Found: {meta['title']} ({meta['channel']})")
    print(f"[+] Retrieved {len(segments)} transcript cues across {round(meta['duration'] / 60, 1)} mins")

    if not segments:
        print("[!] No transcript segments found. Ensure video has captions or use Groq Whisper fallback.")
        sys.exit(1)

    print(f"[*] Step 2: Scoring transcript windows for viral hooks...")
    analyzer = ClipAnalyzer()
    candidates = analyzer.find_heuristic_candidates(segments, top_k=args.top_k)

    dispatcher = CloudDispatcher()
    results = []

    for i, cand in enumerate(candidates, 1):
        if args.ai:
            cand = analyzer.refine_with_ai(cand, meta["title"])
        else:
            cand["viral_title"] = f"{cand['hook_first_words'].title()}... | {meta['channel']}"
            cand["hook_breakdown"] = "High-velocity opening hook with immediate emotional tension."
            cand["target_audience"] = "High-retention mobile audience."

        spec = dispatcher.generate_clip_spec(meta["url"], cand)
        dispatch_cmd = dispatcher.get_dispatch_command(spec)

        print(f"\n--- Clip Candidate #{i} [Score: {cand['score']}/100] ---")
        print(f"Title:    {cand['viral_title']}")
        print(f"Time:     {cand['start']}s -> {cand['end']}s ({cand['duration']}s)")
        print(f"Hook:     \"{cand['hook_first_words']}...\"")
        print(f"Excerpt:  \"{cand['text'][:120]}...\"")
        print(f"Cloud Dispatch: {dispatch_cmd}")

        results.append({
            "clip": cand,
            "spec": spec,
            "dispatch_command": dispatch_cmd
        })

    payload = {
        "metadata": meta,
        "clip_candidates": results
    }

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"\n[+] Saved clip specifications to {args.out}")

    return payload

if __name__ == "__main__":
    main()
