from typing import Any, Dict, List
from src.shared.settings import get_settings
from googleapiclient.discovery import build
from google.auth.exceptions import DefaultCredentialsError
import isodate
from datetime import datetime
import re 
import tiktoken



# Load tiktoken encoding
try:
    encoding = tiktoken.encoding_for_model("text-embedding-3-large")
except KeyError:
# generic BPE used by many OpenAI models
    encoding = tiktoken.get_encoding("cl100k_base")

#get service build to fetch youtube video metadata
def get_youtube_service(api_key):
    """Initializes and returns the YouTube API service object."""
    try:
        return build("youtube", "v3", developerKey=api_key)
    except DefaultCredentialsError:
        print("ERROR: Could not find default credentials. Please set up authentication.")
        return None
    except Exception as e:
        print(f"ERROR: Could not build YouTube service: {e}")
        return None
    
def parse_iso_duration(duration_str):
    """Converts an ISO 8601 duration string (e.g., 'PT1H30M5S') to seconds."""
    try:
        return int(isodate.parse_duration(duration_str).total_seconds())
    except Exception:
        print(f"Warning: Could not parse duration: {duration_str}")
        return 0

def fetch_video_data(service, video_id):
    """
    Fetches all metadata and the description for a video in one API call.
    Returns a tuple: (metadata_dict, raw_description_string)
    """
    try:
        request = service.videos().list(
            part="snippet,contentDetails,statistics",
            id=video_id
        )
        response = request.execute()

        if not response.get("items"):
            print(f"Warning: No video found with ID: {video_id}")
            return None, None

        item = response["items"][0]
        snippet = item["snippet"]
        stats = item["statistics"]
        content = item["contentDetails"]

        # Build the metadata dictionary exactly as requested
        metadata = {
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "video_title": snippet.get("title"),
            "published_at": snippet.get("publishedAt"),
            "duration_sec": parse_iso_duration(content.get("duration")),
            "channel_title": snippet.get("channelTitle"),
            "tags": snippet.get("tags", []), # Use empty list if no tags
            "stats": {
                "viewCount": int(stats.get("viewCount", 0)),
                "likeCount": int(stats.get("likeCount", 0)),
                "commentCount": int(stats.get("commentCount", 0))
            }
        }

        raw_description = snippet.get("description", "")

        return metadata, raw_description

    except Exception as e:
        print(f"ERROR: Failed to fetch data for {video_id}. {e}")
        return None, None
    
def parse_time_to_seconds(time_str):
    """Converts HH:MM:SS or MM:SS or H+:MM:SS to total seconds."""
    parts = time_str.split(':')
    seconds = 0
    try:
        if len(parts) == 3:  # HH:MM:SS
            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:  # MM:SS
            seconds = int(parts[0]) * 60 + int(parts[1])
        return seconds
    except ValueError:
        print(f"Warning: Could not parse time string: {time_str}")
        return 0
    
def parse_chapters_from_description(description_string):
    """
    Parses a raw description string to find and extract chapters.
    This version uses a more robust marker-finding logic.
    """
    chapters = []

    # This regex for the chapter lines is correct and robust
    chapter_regex = re.compile(r"\[?(\d+:\d{2}(?::\d{2})?)\]?\s*(?:-+\s*)?(.*)", re.IGNORECASE)


    timestamp_marker = re.search(
        r"^\s*[\*_]*\s*(Timestamps|Chapters|Contents)\s*[\*_]*",
        description_string,
        re.MULTILINE | re.IGNORECASE
    )

    if not timestamp_marker:
        print(f"Warning: 'Timestamps', 'Chapters', or 'Contents' marker not found in description.")
        return [] # Return empty list if no chapters section

    # Find the end of that *entire line*
    marker_line_end = description_string.find('\n', timestamp_marker.start())

    if marker_line_end == -1:
        # Fallback if "Timestamps" is the very last line
        chapter_section = description_string[timestamp_marker.end():]
    else:
        # Start searching for chapters on the *next line*
        chapter_section = description_string[marker_line_end:]
    # --- END OF UPDATE ---

    for match in chapter_regex.finditer(chapter_section):
        time_str, title = match.groups()
        title = title.strip()

        # Filter out junk lines or sponsor links
        if not title or len(title) < 3 or "http" in title or "www." in title:
            continue

        start_sec = parse_time_to_seconds(time_str)

        chapters.append({
            "start": start_sec,
            "start_str": time_str,
            "title": title
        })

    return chapters

def count_tokens(text: str) -> int:
    """
    Count tokens using tiktoken as a proxy for your embedding model's tokenizer.
    Replace with your exact tokenizer if needed.
    """


    text = text or ""
    return len(encoding.encode(text))

def assign_interpolated_timestamps_seconds(
    sentences: List[Dict],
    chunk_start_s: int,
    chunk_end_s: int,
) -> List[Dict]:
    """
    Assign approximate start_s/end_s (INTEGER seconds) to each sentence
    by linearly mapping char offsets onto the chunk time range.
    """
    if not sentences:
        return []

    if chunk_end_s < chunk_start_s:
        raise ValueError("chunk_end_s must be >= chunk_start_s")

    total_chars = sentences[-1]["char_end"]
    duration = chunk_end_s - chunk_start_s

    # Fallback for empty or invalid cases
    if total_chars <= 0 or duration <= 0:
        n = len(sentences)
        for i, s in enumerate(sentences):
            s_start = chunk_start_s + (i / max(1, n)) * duration
            s_end = chunk_start_s + ((i + 1) / max(1, n)) * duration
            s["start_s"] = int(round(s_start))
            s["end_s"] = int(round(s_end))
        return sentences

    # Normal interpolation
    for s in sentences:
        rel_start = s["char_start"] / total_chars
        rel_end = s["char_end"] / total_chars
        rel_start = max(0.0, min(1.0, rel_start))
        rel_end = max(rel_start, min(1.0, rel_end))
        s["start_s"] = int(round(chunk_start_s + rel_start * duration))
        s["end_s"] = int(round(chunk_start_s + rel_end * duration))

    return sentences


from typing import Any, Dict, List

def split_sentences_with_offsets(text: str) -> List[Dict[str, Any]]:
    """
    Split `text` into word-based chunks of `chunk_size` words, tracking character offsets.

    - Each chunk is ~`chunk_size` words (last chunk can be smaller).
    - If the final chunk has < `merge_tail_if_lt` words, merge it into the previous chunk.
    - Offsets are indices into the original `text` (0-based), char_end is exclusive.

    Returns:
    [
      {"text": str, "char_start": int, "char_end": int, "word_count": int},
      ...
    ]
    """
    chunk_size = 150
    merge_tail_if_lt = 50
    if not text or not text.strip():
        return []

    words = text.split()
    chunks: List[Dict[str, Any]] = []

    cursor = 0  # search position in original text

    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunk_text = " ".join(chunk_words)

        # Find this chunk in the original text starting from cursor
        start = text.find(chunk_text, cursor)
        if start == -1:
            # Fallback: progressively relax (handles weird spacing/newlines)
            # Find first word then extend end by searching for last word after it.
            first_w = chunk_words[0]
            start = text.find(first_w, cursor)
            if start == -1:
                # Give up safely; avoid wrong offsets
                break
            # Best-effort end: find last word occurrence after start
            last_w = chunk_words[-1]
            last_pos = text.find(last_w, start)
            if last_pos == -1:
                end = start + len(first_w)
            else:
                end = last_pos + len(last_w)
        else:
            end = start + len(chunk_text)

        chunks.append({
            "text": chunk_text,
            "char_start": start,
            "char_end": end,
            "word_count": len(chunk_words),
        })

        cursor = end
        i += chunk_size

    # Merge tail if it's too small (< merge_tail_if_lt) and there is a previous chunk
    if len(chunks) >= 2 and chunks[-1]["word_count"] < merge_tail_if_lt:
        prev = chunks[-2]
        tail = chunks[-1]

        merged_text = prev["text"] + " " + tail["text"]
        chunks[-2] = {
            "text": merged_text,
            "char_start": prev["char_start"],
            "char_end": tail["char_end"],
            "word_count": prev["word_count"] + tail["word_count"],
        }
        chunks.pop()

    # Debug prints (like your current function)
    for c in chunks:
        print(c)

    return chunks


def build_windows_with_overlap_seconds(
    sentences: List[Dict[str, Any]],
    max_tokens: int = 1200,
    overlap_tokens: int = 200,
    min_tokens_per_window: int = 800,
) -> List[Dict[str, Any]]:
    """
    Build sentence-level windows with:

    - Each window uses WHOLE sentences only.
    - Hard-ish cap: window token_count <= max_tokens (small violations only if you tweak logic).
    - Forward-only overlap:
        Next window starts with a tail of sentences from the end of the previous window
        whose total tokens ~= overlap_tokens.
    - If the last window is too small (< min_tokens_per_window), merge it into previous.

    Input `sentences` must contain:
        "text": str
        "start_s": float
        "end_s": float

    Returns list of windows:
    {
        "text": str,
        "start_s": float,
        "end_s": float,
        "token_count": int,
        "sentences": [ ... original sentence dicts ... ]
    }
    """
    if not sentences:
        return []

    windows: List[Dict[str, Any]] = []
    current_sents: List[Dict[str, Any]] = []
    current_tokens = 0

    def finalize_window(sents: List[Dict[str, Any]]) -> Dict[str, Any] | None:
        if not sents:
            return None
        text = " ".join(s["text"] for s in sents).strip()
        if not text:
            return None
        return {
            "text": text,
            "start_s": int(sents[0]["start_s"]),
            "end_s": int(sents[-1]["end_s"]),
            "token_count": count_tokens(text),
            "sentences": list(sents),
        }

    for sent in sentences:
        sent_text = sent["text"]
        sent_tokens = count_tokens(sent_text)

        # If adding this sentence would exceed max_tokens,
        # we close the current window and start a new one with overlap.
        if current_sents and (current_tokens + sent_tokens > max_tokens):
            # Close current
            w = finalize_window(current_sents)
            if w:
                windows.append(w)

            # Build overlap from end of previous window (forward-only)
            overlap_sents: List[Dict[str, Any]] = []
            overlap_tok_sum = 0
            for prev in reversed(current_sents):
                t = count_tokens(prev["text"])
                if overlap_tok_sum + t <= overlap_tokens:
                    overlap_sents.insert(0, prev)
                    overlap_tok_sum += t
                else:
                    break

            # New window starts with overlap + this sentence
            current_sents = overlap_sents + [sent]
            current_tokens = sum(count_tokens(s["text"]) for s in current_sents)

        else:
            # Safe to add sentence to current window
            current_sents.append(sent)
            current_tokens += sent_tokens

    # Flush last window
    if current_sents:
        w = finalize_window(current_sents)
        if w:
            windows.append(w)

    # Merge last tiny window into previous one (your rule)
    if len(windows) >= 2:
        last = windows[-1]
        prev = windows[-2]

        if last["token_count"] < min_tokens_per_window:
            merged_sentences = prev["sentences"] + last["sentences"]
            merged_text = " ".join(s["text"] for s in merged_sentences).strip()
            merged = {
                "text": merged_text,
                "start_s": float(prev["start_s"]),
                "end_s": float(last["end_s"]),
                "token_count": count_tokens(merged_text),
                "sentences": merged_sentences,
            }
            windows = windows[:-2] + [merged]

    return windows




def split_chunk_if_needed(chunk: Dict[str, Any], parent_id: str) -> List[Dict[str, Any]]:
    """
    For a large chunk:
      - sentence split
      - assign sentence timestamps within [start_seconds, end_seconds]
      - window with overlap
      - produce child chunks linked to parent_id
    """
    text = chunk.get("text", "") or ""
    start_s = int(chunk.get("start_seconds", 0))
    end_s = int(chunk.get("end_seconds", 0))

    sentences = split_sentences_with_offsets(text)
    sentences = assign_interpolated_timestamps_seconds(sentences, start_s, end_s)
    windows = build_windows_with_overlap_seconds(sentences)

    children: List[Dict[str, Any]] = []
    for w in windows:
        children.append({
            "chapter_title": chunk.get("chapter_title"),
            "start_seconds": w["start_s"],
            "end_seconds": w["end_s"],
            "text": w["text"],
            "parent_id": parent_id,
            # if you want to debug lengths, uncomment:
            "token_count": w["token_count"],
        })
    return children

def build_final_json(video_metadata, raw_description, chapters, transcript_lines):
    """
    Assembles the final JSON object by grouping transcript lines into
    chapter-based chunks.
    """

    # --- 1. Calculate end times for each chapter ---
    chapters_with_end_times = []
    if not chapters:
        print(f"Warning: No chapters found. Cannot create chunks.")
    else:
        for i in range(len(chapters)):
            chapter = chapters[i]

            # Get start time and title
            start_sec = chapter["start"]
            title = chapter["title"]

            # Determine end time
            if i + 1 < len(chapters):
                # End time is the start of the next chapter
                end_sec = chapters[i+1]["start"]
            else:
                # End time is the total video duration
                end_sec = video_metadata["duration_sec"]

            chapters_with_end_times.append({
                "start": start_sec,
                "end": end_sec,
                "title": title
            })

    # --- 2. Group transcript lines into chunks ---
    new_chunks: List[Dict[str, Any]] = []
    parents: List[Dict[str, Any]] = []

    for idx , chapter in enumerate(chapters_with_end_times):
        chunk_text_lines = []

        # 3. Find all lines that fall within this chapter's timeframe
        for line in transcript_lines:
            if line["start"] >= chapter["start"] and line["start"] < chapter["end"]:
                chunk_text_lines.append(line["text"])

        # 4. Join the text
        full_chunk_text = " ".join(chunk_text_lines)
        full_chunk_text = re.sub(r'\s+', ' ', full_chunk_text).strip()



        # Only add the chunk if it actually has text
        if full_chunk_text:
            token_count = count_tokens(full_chunk_text)
            data = {
                    "chapter_title": chapter["title"],
                    "start_seconds": chapter["start"],
                    "end_seconds": chapter["end"],
                    "text": full_chunk_text
                }
            if token_count <= 2000: # You can adjust this threshold based on your embedding model's limits

                new_chunks.append(data)
            else:
                safe_title = (chapter.get("title") or "no_title").replace(" ", "_").lower()
                parent_id = f"{safe_title}_{idx}"

                parents.append({
                    "parent_id": parent_id,
                    "chapter_title": chapter.get("title"),
                    "start_seconds": int(chapter.get("start", 0)),
                    "end_seconds": int(chapter.get("end", 0)),
                    "text": full_chunk_text,
                    # "token_count": token_count,  # optional
                })
                children = split_chunk_if_needed(data, parent_id)
                new_chunks.extend(children)


    # --- 5. Assemble the final JSON object ---
    final_output = {
        **video_metadata, # Unpacks all keys: video_id, url, title, stats...
        "description": raw_description,
        "chapters": chapters_with_end_times, # This is the new key
        "chunks": new_chunks, # This is the new key
        "parent_chunks": parents,
        # We no longer need 'chapters' and 'transcript_segments' separately
        "source": "youtube",
        "indexed_at": datetime.now().isoformat()
    }

    return final_output

def chapter_level_chunk(transcript_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    s = get_settings()
    service = get_youtube_service(s.youtube_api)
    video_id = transcript_payload["video_id"]
    metadata, description = fetch_video_data(service, transcript_payload["video_id"])

    if not metadata:
        print(f"Warning: No metadata found for {video_id}.")

    chapters = parse_chapters_from_description(description)
    if not chapters:
        print(f"Warning: No chapters found for {video_id}.")


    # MERGE
    final_json_data = build_final_json(metadata, description, chapters, transcript_payload.get("items", []))
    return final_json_data