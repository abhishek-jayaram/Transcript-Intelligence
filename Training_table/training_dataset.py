import json
import pandas as pd
from pathlib import Path

MASTER_FILE = "Data/master_meetings.json"
OUTPUT_CSV = "training_dataset.csv"

# -------------------------------------------------
# Helpers
# -------------------------------------------------

def extract_transcript_text(meeting):
    turns = meeting.get("transcript_turns", [])

    texts = []

    for turn in turns:
        speaker = turn.get("speaker_name", "")
        text = turn.get("text", "")

        if text:
            texts.append(f"{speaker}: {text}")

    return " ".join(texts)


def extract_topics(meeting):
    return ", ".join(meeting.get("topics", []))


def extract_action_items(meeting):
    return " | ".join(meeting.get("action_items", []))


# -------------------------------------------------
# Load Master File
# -------------------------------------------------

with open(MASTER_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# Extract meetings from the master structure
if isinstance(data, dict) and "meetings" in data:
    meetings = data["meetings"]
else:
    meetings = data

rows = []

for m in meetings:

    row = {
        "meeting_id": m.get("meeting_id"),

        "title": m.get("title", ""),

        "summary": m.get("summary", ""),

        "transcript_text": extract_transcript_text(m),

        "duration_minutes": m.get("duration_minutes", 0),

        "participant_count": len(
            m.get("participants", [])
        ),

        "internal_count": len(
            m.get("internal_participants", [])
        ),

        "external_count": len(
            m.get("external_participants", [])
        ),

        "speaker_count": len(
            m.get("speaker_map", {})
        ),

        "topics": extract_topics(m),

        "action_items": extract_action_items(m),

        "overall_sentiment": m.get(
            "overall_sentiment",
            ""
        ),

        "sentiment_score": m.get(
            "sentiment_score",
            0
        ),

        "has_external": int(
            len(m.get("external_participants", [])) > 0
        ),

        "topic_count": len(
            m.get("topics", [])
        ),

        "action_item_count": len(
            m.get("action_items", [])
        ),

        "summary_length": len(
            m.get("summary", "").split()
        ),

        "transcript_length": len(
            extract_transcript_text(m).split()
        ),

        # Manual label goes here
        "label": ""
    }

    rows.append(row)

df = pd.DataFrame(rows)

df.to_csv(
    OUTPUT_CSV,
    index=False
)

print(f"Saved {len(df)} meetings")
print(df.head())