"""Theme / topic discovery for meeting transcripts.

Goal
----
Discover and explain recurring themes in your meeting dataset, such as:
- support escalation / troubleshooting
- renewal / expansion / commercial discussion
- onboarding / implementation
- product feedback / feature gaps
- compliance / audit preparation
- internal planning / roadmap / engineering sync
- demo / POC / technical evaluation
- competitive review / market analysis

This script uses a HYBRID approach:
1) Rule-based theme assignment for clear cases.
2) Unsupervised topic discovery (TF-IDF + NMF) for broader theme exploration.
3) Example extraction so you can explain each theme with real meetings.

Why hybrid?
- Rules are interpretable and reliable for obvious meeting types.
- NMF helps uncover latent patterns without needing pre-labeled themes.
- The combination is easy to justify in a report because it shows both reasoning and data-driven discovery.

Input
-----
A consolidated master JSON like:
    master_meetings.json

Expected structure per meeting:
- meeting_id
- title
- summary
- topics
- action_items
- transcript_text (or transcript_turns)
- external_participants / internal_participants
- duration_minutes

Outputs
-------
- themes_by_meeting.csv
- theme_summary.csv
- discovered_topics.json
- representative_examples.json

Usage
-----
python theme_discovery.py \
    --input master_meetings.json \
    --outdir theme_outputs \
    --n-topics 8
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer


# -----------------------------
# Theme seeds (rule-based layer)
# -----------------------------

THEME_SEEDS: Dict[str, Dict[str, object]] = {
    "customer_support_escalation": {
        "keywords": [
            "incident", "outage", "downtime", "bug", "issue", "errors", "error",
            "ticket", "escalation", "troubleshoot", "troubleshooting", "root cause",
            "investigation", "not working", "broken", "failure", "alert fatigue",
            "false positive", "false positives", "urgent"
        ],
        "description": "Calls focused on customer problems, incidents, debugging, or support escalation.",
    },
    "renewal_expansion": {
        "keywords": [
            "renewal", "renewals", "expand", "expansion", "add-on", "upsell", "cross-sell",
            "pricing", "contract", "billing", "commercial", "decision", "decision making",
            "term", "quote", "proposal", "annual", "multi-year", "ramp"
        ],
        "description": "Calls about renewal, expansion, pricing, contract discussions, or add-on decisions.",
    },
    "onboarding_implementation": {
        "keywords": [
            "onboarding", "implementation", "kickoff", "setup", "deployment", "go live",
            "migration", "integrat", "configuration", "configure", "technical onboarding",
            "rollout", "working session", "scoping", "implementation plan"
        ],
        "description": "Calls about deploying, configuring, or onboarding a customer into the product.",
    },
    "product_feedback_feature_gap": {
        "keywords": [
            "feedback", "feature gap", "missing", "gap", "wishlist", "pain point", "pain points",
            "improve", "improvement", "request", "feature request", "would like", "could eventually",
            "frustration", "too manual", "manual", "product review"
        ],
        "description": "Calls where customers discuss product strengths, weaknesses, or missing capabilities.",
    },
    "compliance_audit": {
        "keywords": [
            "audit", "compliance", "soc 2", "hipaa", "iso 27001", "pci dss", "ffiec",
            "glba", "evidence", "controls", "security rule", "audit-ready", "regulator",
            "audit prep", "reporting", "remediation", "policy"
        ],
        "description": "Calls around compliance, audits, evidence collection, or regulatory readiness.",
    },
    "internal_planning_roadmap": {
        "keywords": [
            "roadmap", "planning", "quarterly", "q1", "q2", "q3", "sprint", "standup",
            "design review", "engineering sync", "release", "launch", "capacity", "spec",
            "backlog", "timeline", "technical dependency", "staff meeting", "retro"
        ],
        "description": "Internal company meetings on planning, roadmap, design, or execution.",
    },
    "demo_poc_evaluation": {
        "keywords": [
            "demo", "preview", "proof of concept", "poc", "evaluation", "evaluate",
            "technical demo", "trial", "pilot", "walkthrough", "show us", "see how", "scoped poc"
        ],
        "description": "Evaluation-oriented customer conversations including demos and proof-of-concept work.",
    },
    "competitive_review": {
        "keywords": [
            "competitive", "competitor", "competition", "market", "sentinel", "vaultedge",
            "cybernova", "fortiguard", "alternatives", "compare", "comparison"
        ],
        "description": "Calls discussing competitors, market positioning, or win/loss analysis.",
    },
}


STOPWORDS = set(
    "a an and are as at be by for from has have he her hers him his i in is it its just "
    "me my no not of on or our ours she that the their them they this to was we were what when where who "
    "why with would you your yours about after before could should will can".split()
)


# -----------------------------
# Helpers
# -----------------------------


def normalize_text(text: str) -> str:
    text = text or ""
    text = text.replace("\u2014", "-").replace("\u2013", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def as_text_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in re.split(r"[;,|]", value) if v.strip()]
    return [str(value)]


def extract_transcript_text(meeting: Dict) -> str:
    if meeting.get("transcript_text"):
        return str(meeting.get("transcript_text"))

    turns = meeting.get("transcript_turns") or []
    parts = []
    for turn in turns:
        speaker = str(turn.get("speaker_name", "")).strip()
        text = str(turn.get("text") or turn.get("sentence") or "").strip()
        if text:
            parts.append(f"{speaker}: {text}" if speaker else text)
    return " ".join(parts)


def build_search_text(meeting: Dict) -> str:
    pieces = [
        meeting.get("title", ""),
        meeting.get("summary", ""),
        " ".join(as_text_list(meeting.get("topics"))),
        " ".join(as_text_list(meeting.get("action_items"))),
        extract_transcript_text(meeting),
    ]
    return normalize_text(" ".join([p for p in pieces if p]))


def keyword_hits(text: str, keywords: List[str]) -> Tuple[int, List[str]]:
    hits = []
    for kw in keywords:
        kw_n = normalize_text(kw)
        if not kw_n:
            continue
        if " " in kw_n:
            if kw_n in text:
                hits.append(kw)
        else:
            if re.search(rf"\b{re.escape(kw_n)}\b", text):
                hits.append(kw)
    return len(hits), hits


@dataclass
class ThemeAssignment:
    meeting_id: str
    title: str
    assigned_theme: str
    theme_method: str
    confidence: float
    matched_keywords: str
    theme_reason: str


# -----------------------------
# Rule-based assignment
# -----------------------------


def assign_rule_based_theme(meeting: Dict) -> Tuple[str, float, List[str], str]:
    text = build_search_text(meeting)

    theme_scores = []
    for theme, meta in THEME_SEEDS.items():
        keywords = meta["keywords"]
        count, hits = keyword_hits(text, keywords)  # type: ignore[arg-type]
        if count:
            # Slight boost if multiple keywords match and if title/summary contain them.
            score = count
            if normalize_text(meeting.get("title", "")) and any(
                normalize_text(k) in normalize_text(meeting.get("title", "")) for k in hits
            ):
                score += 1
            if normalize_text(meeting.get("summary", "")) and any(
                normalize_text(k) in normalize_text(meeting.get("summary", "")) for k in hits
            ):
                score += 1
            theme_scores.append((theme, score, hits))

    if not theme_scores:
        return "uncategorized", 0.0, [], "No strong keyword pattern matched."

    theme_scores.sort(key=lambda x: (-x[1], x[0]))
    best_theme, best_score, best_hits = theme_scores[0]
    # Confidence is a simple heuristic for explainability.
    confidence = min(1.0, 0.35 + 0.15 * best_score)
    reason = f"Matched {best_score} seed signal(s): {', '.join(best_hits[:6])}"
    return best_theme, round(confidence, 2), best_hits, reason


# -----------------------------
# Topic discovery with NMF
# -----------------------------


def discover_topics(texts: List[str], n_topics: int, max_features: int = 5000):
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
    )
    X = vectorizer.fit_transform(texts)

    # NMF works well on TF-IDF and gives interpretable word groups.
    n_components = max(2, min(n_topics, max(2, X.shape[0] - 1)))
    model = NMF(n_components=n_components, random_state=42, init="nndsvda", max_iter=500)
    W = model.fit_transform(X)
    H = model.components_

    feature_names = vectorizer.get_feature_names_out()
    topic_terms = []
    for topic_idx, weights in enumerate(H):
        top_idx = weights.argsort()[::-1][:10]
        terms = [feature_names[i] for i in top_idx]
        topic_terms.append({
            "topic_id": topic_idx,
            "top_terms": terms,
        })

    topic_labels = [
        " / ".join(t["top_terms"][:3]) for t in topic_terms
    ]

    return {
        "vectorizer": vectorizer,
        "model": model,
        "weights": W,
        "topic_terms": topic_terms,
        "topic_labels": topic_labels,
    }


# -----------------------------
# Theme summary / examples
# -----------------------------


def build_theme_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for theme, grp in df.groupby("assigned_theme", dropna=False):
        grp = grp.copy()
        top_titles = grp["title"].head(3).tolist()
        rows.append({
            "theme": theme,
            "count": len(grp),
            "avg_confidence": round(float(grp["confidence"].mean()), 3) if len(grp) else 0.0,
            "example_titles": " | ".join(top_titles),
            "top_keywords": " | ".join(sorted(set(
                kw for s in grp["matched_keywords"].fillna("") for kw in s.split("; ") if kw
            ))[:12]),
        })
    return pd.DataFrame(rows).sort_values(["count", "theme"], ascending=[False, True])


def build_representative_examples(df: pd.DataFrame, n_examples: int = 3) -> Dict[str, List[Dict[str, str]]]:
    examples: Dict[str, List[Dict[str, str]]] = {}
    for theme, grp in df.groupby("assigned_theme"):
        # Prefer high-confidence examples for explanation.
        sample = grp.sort_values(["confidence", "title"], ascending=[False, True]).head(n_examples)
        examples[theme] = [
            {
                "meeting_id": row["meeting_id"],
                "title": row["title"],
                "reason": row["theme_reason"],
                "matched_keywords": row["matched_keywords"],
            }
            for _, row in sample.iterrows()
        ]
    return examples


# -----------------------------
# Main
# -----------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover and explain themes in meeting transcripts.")
    parser.add_argument("--input", required=True, help="Path to master_meetings.json")
    parser.add_argument("--outdir", required=True, help="Directory to write theme outputs")
    parser.add_argument("--n-topics", type=int, default=8, help="Number of latent topics for NMF discovery")
    args = parser.parse_args()

    input_path = Path(args.input)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Support master files that wrap meetings with metadata
    if isinstance(data, dict) and "meetings" in data:
        meetings = data["meetings"]
    else:
        meetings = data

    rows = []
    texts = []

    for meeting in meetings:
        text = build_search_text(meeting)
        theme, confidence, hits, reason = assign_rule_based_theme(meeting)

        rows.append({
            "meeting_id": meeting.get("meeting_id", ""),
            "title": meeting.get("title", ""),
            "summary": meeting.get("summary", ""),
            "assigned_theme": theme,
            "theme_method": "rule_based_hybrid",
            "confidence": confidence,
            "matched_keywords": "; ".join(hits),
            "theme_reason": reason,
            "duration_minutes": meeting.get("duration_minutes", 0),
            "external_count": len(meeting.get("external_participants", [])),
            "internal_count": len(meeting.get("internal_participants", [])),
            "participant_count": len(meeting.get("participants", [])),
        })
        texts.append(text)

    df = pd.DataFrame(rows)

    # Unsupervised discovery layer on all meeting texts.
    discovery = discover_topics(texts, n_topics=args.n_topics)
    topic_terms = discovery["topic_terms"]
    topic_labels = discovery["topic_labels"]
    W = discovery["weights"]

    # Attach latent topic probabilities / dominant topic to each meeting.
    dominant_topic = W.argmax(axis=1)
    dominant_topic_score = W.max(axis=1)
    df["latent_topic_id"] = dominant_topic
    df["latent_topic_label"] = [topic_labels[i] for i in dominant_topic]
    df["latent_topic_strength"] = [round(float(v), 4) for v in dominant_topic_score]

    # Build concise latent-topic summary for interpretation.
    topic_summary_rows = []
    for t in topic_terms:
        topic_id = t["topic_id"]
        top_terms = t["top_terms"]
        sample_rows = df[df["latent_topic_id"] == topic_id].sort_values(
            ["latent_topic_strength", "title"], ascending=[False, True]
        ).head(3)
        topic_summary_rows.append({
            "topic_id": topic_id,
            "label": topic_labels[topic_id],
            "top_terms": ", ".join(top_terms[:10]),
            "count": int((df["latent_topic_id"] == topic_id).sum()),
            "example_titles": " | ".join(sample_rows["title"].tolist()),
        })

    theme_summary = build_theme_summary(df)
    examples = build_representative_examples(df)

    # Write outputs.
    df.to_csv(outdir / "themes_by_meeting.csv", index=False)
    theme_summary.to_csv(outdir / "theme_summary.csv", index=False)

    with (outdir / "discovered_topics.json").open("w", encoding="utf-8") as f:
        json.dump(topic_summary_rows, f, indent=2, ensure_ascii=False)

    with (outdir / "representative_examples.json").open("w", encoding="utf-8") as f:
        json.dump(examples, f, indent=2, ensure_ascii=False)

    # A small markdown explanation you can reuse in your write-up.
    explanation_md = f"""# Theme Discovery Approach\n\nWe used a hybrid method because it balances interpretability and discovery:\n\n1. **Rule-based theme assignment**\n   - Clear keyword patterns map meetings to known themes such as support escalation, renewal/expansion, onboarding, compliance, internal planning, and demos/POCs.\n   - This makes the output easy to explain and easy to audit.\n\n2. **Unsupervised topic discovery (TF-IDF + NMF)**\n   - NMF groups meetings by shared language patterns without needing labels.\n   - This helps surface latent themes that may not have been obvious from the seed rules alone.\n\n3. **Representative examples**\n   - For each theme, we keep a few example meetings and the matched keywords so the result is explainable, not just a black-box assignment.\n\n### Output counts\n- Meetings processed: {len(df)}\n- Rule-based themes found: {df['assigned_theme'].nunique()}\n- Latent topics discovered: {len(topic_terms)}\n"""
    (outdir / "approach_explanation.md").write_text(explanation_md, encoding="utf-8")

    print(f"Saved outputs to: {outdir}")
    print(f"Meetings processed: {len(df)}")
    print(f"Themes discovered: {df['assigned_theme'].nunique()}")
    print(f"Latent topics discovered: {len(topic_terms)}")
    print("Top rule-based themes:")
    print(theme_summary.head(10).to_string(index=False))
    print("\nTop latent topics:")
    print(pd.DataFrame(topic_summary_rows).sort_values(["count", "topic_id"], ascending=[False, True]).head(10).to_string(index=False))


if __name__ == "__main__":
    main()

