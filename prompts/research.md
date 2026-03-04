# Prospect Research Synthesis

Synthesize raw search results into a structured research brief.

## Input
You will receive:
- `prospect_name`: The person's name.
- `company`: Their company.
- `title`: Their job title.
- `search_results`: Raw results from Brave Search.
- `rules`: The global rules from rules.md.

## Output Schema
```json
{
  "content_type": "research_brief",
  "prospect_name": "<name>",
  "company": "<company>",
  "recent_news": ["<real news items or 'Not found'>"],
  "linkedin_activity": "<summary of recent posts/activity or 'Not found'>",
  "talking_points": ["<specific, factual hooks for outreach>"],
  "evidence_snippets": ["<source URLs or descriptions>"],
  "confidence_score": 0.0
}
```

## Guidelines
- Only include verifiable facts. If search returns nothing useful, set fields to "Not found."
- Prioritize recency: news from the last 30 days > older info.
- Talking points must be specific enough to use in outreach (not generic like "they work in tech").
- Confidence score reflects how actionable the research is:
  - 0.9+: Recent news + clear hooks
  - 0.7-0.9: Some useful info but not time-sensitive
  - <0.7: Minimal findings, generic outreach only
