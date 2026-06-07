"""Clean and normalize meeting JSON files into a single structured record.

This script is designed for your current data shape:
- meeting-info(2).json
- summary(2).json
- transcript(2).json
- speakers(2).json
- speaker-meta(2).json
- events(2).json

It outputs a cleaned JSON file with:
- normalized meeting metadata
- cleaned transcript turns
- speaker map
- participant role hints
- summary, topics, action items
- basic text cleaning and utility fields

Usage:
    python clean_meeting_jsons.py \
        --meeting-info meeting-info(2).json \
        --summary summary(2).json \
        --transcript transcript(2).json \
        --speakers speakers(2).json \
        --speaker-meta speaker-meta(2).json \
        --events events(2).json \
        --out cleaned_meeting.json

This script is a meeting data cleaner and normalizer 

1. Text Cleaning — normalizes whitespace, fixes em-dashes, removes extra spaces before punctuation, across all text fields.
2. Participant Classification — infers internal vs external attendees by comparing each participant's email domain against the organizer's domain.
3. Transcript Processing — cleans each speaker turn, then merges consecutive turns from the same speaker (within 1 second gap) into larger coherent segments.
4. Stats Generation — counts turn counts per speaker and total speaking time in seconds per speaker.
5. Record Assembly — bundles everything into a single CleanMeetingRecord dataclass and writes it to an output JSON.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------
# Text cleaning helpers
# -----------------------------

def normalize_whitespace(text: Optional[str]) -> str:
    if not text:
        return ""
    text = str(text)
    text = text.replace("\u2014", "-").replace("\u2013", "-")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_sentence(text: Optional[str]) -> str:
    text = normalize_whitespace(text)
    # Remove extra spaces before punctuation
    text = re.sub(r"\s+([?.!,;:])", r"\1", text)
    return text


def clean_name(name: Optional[str]) -> str:
    return normalize_whitespace(name)


def email_domain(email: Optional[str]) -> str:
    if not email or "@" not in email:
        return ""
    return email.split("@", 1)[1].lower().strip()


# -----------------------------
# Data models
# -----------------------------

@dataclass
class CleanSpeakerSegment:
    speaker_name: str
    start_time: float
    end_time: float
    duration: float
    text: str


@dataclass
class CleanEvent:
    participant_name: str
    event_type: str
    time_seconds: float
    timestamp_ms: int


@dataclass
class CleanMeetingRecord:
    meeting_id: str
    title: str
    organizer_email: str
    host_email: str
    start_time: str
    end_time: str
    duration_minutes: float
    participants: List[Dict[str, Any]]
    internal_participants: List[Dict[str, Any]]
    external_participants: List[Dict[str, Any]]
    speaker_map: Dict[str, str]
    transcript_turns: List[Dict[str, Any]]
    transcript_text: str
    summary: str
    topics: List[str]
    action_items: List[str]
    overall_sentiment: Optional[str]
    sentiment_score: Optional[float]
    key_moments: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    stats: Dict[str, Any]


# -----------------------------
# Loaders
# -----------------------------

def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def safe_load(path_str: Optional[str]) -> Optional[Any]:
    if not path_str:
        return None
    path = Path(path_str)
    if not path.exists():
        return None
    return load_json(path)


# -----------------------------
# Cleaning logic
# -----------------------------

def build_speaker_map(speaker_meta: Optional[Dict[str, str]]) -> Dict[str, str]:
    if not speaker_meta:
        return {}
    return {str(k): clean_name(v) for k, v in speaker_meta.items()}


def build_participants(meeting_info: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    emails = meeting_info.get("allEmails") or []
    organizer_email = meeting_info.get("organizerEmail", "")
    internal_domain = email_domain(organizer_email)

    participants = []
    internal = []
    external = []

    for email in emails:
        domain = email_domain(email)
        is_internal = bool(internal_domain) and domain == internal_domain
        item = {
            "email": email,
            "domain": domain,
            "role_hint": "internal" if is_internal else "external",
        }
        participants.append(item)
        (internal if is_internal else external).append(item)

    return participants, internal, external


def build_transcript_turns(transcript: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not transcript:
        return []

    turns = []
    for item in transcript.get("data", []):
        turns.append(
            {
                "speaker_name": clean_name(item.get("speaker_name", "")),
                "start_time": float(item.get("time", 0.0) or 0.0),
                "end_time": float(item.get("endTime", 0.0) or 0.0),
                "sentence": clean_sentence(item.get("sentence", "")),
                "sentiment_type": item.get("sentimentType"),
                "average_confidence": item.get("averageConfidence"),
                "speaker_id": item.get("speaker_id"),
                "index": item.get("index"),
            }
        )
    return turns


def build_events(events: Optional[List[Dict[str, Any]]], speaker_map: Dict[str, str]) -> List[Dict[str, Any]]:
    if not events:
        return []

    cleaned = []
    for item in events:
        name = clean_name(item.get("participantName") or speaker_map.get(str(item.get("speaker_id", "")), ""))
        cleaned.append(
            {
                "participant_name": name,
                "event_type": item.get("type", ""),
                "time_seconds": float(item.get("time", 0.0) or 0.0),
                "timestamp_ms": int(item.get("timestamp", 0) or 0),
            }
        )
    return cleaned


def merge_consecutive_turns(turns: List[Dict[str, Any]]) -> List[CleanSpeakerSegment]:
    """Merge consecutive utterances from the same speaker into larger segments."""
    merged: List[CleanSpeakerSegment] = []
    for turn in turns:
        speaker = clean_name(turn.get("speaker_name", "Unknown")) or "Unknown"
        start = float(turn.get("start_time", 0.0) or 0.0)
        end = float(turn.get("end_time", start) or start)
        text = clean_sentence(turn.get("sentence", ""))
        duration = max(0.0, end - start)

        if merged and merged[-1].speaker_name == speaker and start <= merged[-1].end_time + 1.0:
            prev = merged[-1]
            prev.end_time = max(prev.end_time, end)
            prev.duration = max(0.0, prev.end_time - prev.start_time)
            prev.text = (prev.text + " " + text).strip()
        else:
            merged.append(
                CleanSpeakerSegment(
                    speaker_name=speaker,
                    start_time=start,
                    end_time=end,
                    duration=duration,
                    text=text,
                )
            )
    return merged


def build_transcript_text(turns: List[Dict[str, Any]]) -> str:
    parts = []
    for t in turns:
        speaker = clean_name(t.get("speaker_name", "Unknown")) or "Unknown"
        sentence = clean_sentence(t.get("sentence", ""))
        if sentence:
            parts.append(f"{speaker}: {sentence}")
    return "\n".join(parts)


def summarize_stats(turns: List[Dict[str, Any]], participants: List[Dict[str, Any]]) -> Dict[str, Any]:
    speaker_counts = Counter(clean_name(t.get("speaker_name", "Unknown")) or "Unknown" for t in turns)
    speaker_seconds = Counter()
    for t in turns:
        speaker = clean_name(t.get("speaker_name", "Unknown")) or "Unknown"
        start = float(t.get("start_time", 0.0) or 0.0)
        end = float(t.get("end_time", start) or start)
        speaker_seconds[speaker] += max(0.0, end - start)

    return {
        "turn_count": len(turns),
        "participant_count": len(participants),
        "speaker_turn_counts": dict(speaker_counts),
        "speaker_total_seconds": {k: round(v, 2) for k, v in speaker_seconds.items()},
    }


def clean_meeting_record(
    meeting_info: Dict[str, Any],
    summary: Optional[Dict[str, Any]],
    transcript: Optional[Dict[str, Any]],
    speakers: Optional[List[Dict[str, Any]]],
    speaker_meta: Optional[Dict[str, str]],
    events: Optional[List[Dict[str, Any]]],
) -> CleanMeetingRecord:
    speaker_map = build_speaker_map(speaker_meta)
    participants, internal, external = build_participants(meeting_info)
    turns = build_transcript_turns(transcript)
    merged = merge_consecutive_turns(turns)
    transcript_text = build_transcript_text(turns)
    cleaned_events = build_events(events, speaker_map)

    summary = summary or {}

    record = CleanMeetingRecord(
        meeting_id=clean_name(meeting_info.get("meetingId", "")),
        title=clean_sentence(meeting_info.get("title", "")),
        organizer_email=normalize_whitespace(meeting_info.get("organizerEmail", "")),
        host_email=normalize_whitespace(meeting_info.get("host", "")),
        start_time=normalize_whitespace(meeting_info.get("startTime", "")),
        end_time=normalize_whitespace(meeting_info.get("endTime", "")),
        duration_minutes=float(meeting_info.get("duration", 0.0) or 0.0),
        participants=participants,
        internal_participants=internal,
        external_participants=external,
        speaker_map=speaker_map,
        transcript_turns=[
            {
                "speaker_name": seg.speaker_name,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "duration": seg.duration,
                "text": seg.text,
            }
            for seg in merged
        ],
        transcript_text=transcript_text,
        summary=clean_sentence(summary.get("summary", "")),
        topics=[clean_sentence(x) for x in (summary.get("topics") or []) if clean_sentence(x)],
        action_items=[clean_sentence(x) for x in (summary.get("actionItems") or []) if clean_sentence(x)],
        overall_sentiment=summary.get("overallSentiment"),
        sentiment_score=summary.get("sentimentScore"),
        key_moments=summary.get("keyMoments") or [],
        events=cleaned_events,
        stats=summarize_stats(turns, participants),
    )
    return record


# -----------------------------
# CLI
# -----------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Clean and normalize meeting JSON files.")
    parser.add_argument("--meeting-info", required=True, help="Path to meeting-info JSON")
    parser.add_argument("--summary", default=None, help="Path to summary JSON")
    parser.add_argument("--transcript", default=None, help="Path to transcript JSON")
    parser.add_argument("--speakers", default=None, help="Path to speakers JSON")
    parser.add_argument("--speaker-meta", default=None, help="Path to speaker-meta JSON")
    parser.add_argument("--events", default=None, help="Path to events JSON")
    parser.add_argument("--out", required=True, help="Output cleaned JSON path")
    args = parser.parse_args()

    meeting_info = load_json(Path(args.meeting_info))
    summary = safe_load(args.summary)
    transcript = safe_load(args.transcript)
    speakers = safe_load(args.speakers)
    speaker_meta = safe_load(args.speaker_meta)
    events = safe_load(args.events)

    cleaned = clean_meeting_record(
        meeting_info=meeting_info,
        summary=summary,
        transcript=transcript,
        speakers=speakers,
        speaker_meta=speaker_meta,
        events=events,
    )

    output = asdict(cleaned)
    out_path = Path(args.out)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved cleaned meeting JSON to {out_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        with open("classifier_error.log", "w") as f:
            f.write(traceback.format_exc())
        raise
