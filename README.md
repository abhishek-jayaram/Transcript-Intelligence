# Transcript-Intelligence




This report presents a comprehensive analysis of 100 recorded meetings usingautomated transcript analytics. We used a hybrid topic-discovery approach (rule-based keyword matching
plus
NMF topic modeling) to classify meetings into seven business-relevant themes (e.g.
compliance audit
,
customer support escalation
). We also performed sentiment analysis on each meeting. Key findings include:the largest theme is
Compliance Audits
(42 meetings), reflecting a major customer focus on regulatoryreadiness;
Customer Support
calls (33 meetings) show the most negative sentiment (consistent with theirincident-driven nature); and
External
customer-facing calls (56 meetings) are markedly more positive,indicating healthy renewals, demos, and adoption discussions. We include tables of theme counts andsentiment summary, plus charts to visualize these trends. Finally, we outline stakeholderimplications, limitations, and next steps in an actionable roadmap (see Appendix for scripts and datasources)


# Data Sources & Assumptions
# Data:
We analyzed
master_meetings.json
(100 meetings with transcripts, summaries, titles, and pre-computed sentiment scores) and
themes_by_meeting.csv
(meeting themes assigned via our pipeline).No other datasets were used.
# Assumptions:
We assume the provided sentiment labels (very-positive, mixed-negative, etc.) andscores are correct. Meetings without clear matches were left unthemed. Unless noted, results belowrefer to these 100 meetings.

# Methods
# Theme Discovery:
We used a
hybrid approach
. First, rule-based patterns (from keywords in titles/summaries/transcripts) assigned meetings to predefined business themes (e.g. “HIPAA” or “audit” →
compliance_audit
). Second, we validated these assignments with an unsupervised topic model (TF-IDFvectorization + Non-Negative Matrix Factorization, NMF) to ensure clusters aligned with ourcategories. NMF is a common unsupervised technique for discovering “hidden” topicsin text. The final report focuses on the human-readable rule-based themes, with theNMF results serving as supporting evidence of coherent clusters.
# Sentiment Analysis:
We used existing sentiment scores from the transcripts (presumably using aneutral/positive/negative classifier). For the report, we grouped themes into three call types:
customer_support
(escalations),
external
(all customer-facing, including compliance, renewal,onboarding, feedback, competitive review), and
internal
(planning/roadmap). We computed theaverage sentiment score and distribution of sentiment labels by call type.
Analysis Tools:
Custom Python scripts processed the JSON/CSV files (see Appendix). We generatedcharts using Matplotlib (e.g. bar charts of average sentiment and stacked sentiment distribution).
