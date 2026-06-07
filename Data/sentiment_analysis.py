import json
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Locate files relative to this script so it works when run from Data/
here = Path(__file__).parent
master_path = here / "master_meetings.json"
labels_path = here.parent / "labeling_sheet.csv"

# Load master meetings (support wrapper with metadata)
with open(master_path, "r", encoding="utf-8") as f:
    data = json.load(f)

if isinstance(data, dict) and "meetings" in data:
    meetings = data["meetings"]
else:
    meetings = data

# Load labeling sheet if available to get manual labels
label_map = {}
if labels_path.exists():
    labels_df = pd.read_csv(labels_path)
    if "meeting_id" in labels_df.columns and "manual_label" in labels_df.columns:
        label_map = dict(zip(labels_df["meeting_id"], labels_df["manual_label"]))

# Build a dataframe from sentiment + call type
records = []
for meeting in meetings:
    if not isinstance(meeting, dict):
        continue
    mid = meeting.get("meeting_id")
    call_type = label_map.get(mid) or meeting.get("manual_label") or ""
    records.append({
        "meeting_id": mid,
        "call_type": call_type,
        "sentiment": meeting.get("overall_sentiment"),
        "sentiment_score": meeting.get("sentiment_score"),
    })

df = pd.DataFrame(records)

# --- Analysis ---
print("\n=== Average Sentiment Score by Call Type ===")
print(df.groupby("call_type")["sentiment_score"].mean().sort_values())

print("\n=== Sentiment Label Distribution by Call Type ===")
print(pd.crosstab(df["call_type"], df["sentiment"]))

# --- Plot ---
df.groupby("call_type")["sentiment_score"].mean().sort_values().plot(
    kind="barh", title="Avg Sentiment Score by Call Type", color="steelblue"
)
plt.tight_layout()
plt.savefig("sentiment_by_call_type.png")
print("\nChart saved to sentiment_by_call_type.png")

