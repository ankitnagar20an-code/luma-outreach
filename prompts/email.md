# Outreach Email Generation

Generate a cold/warm outreach email to send via Gmail.

## Input
You will receive:
- `prospect_name`: The person's name.
- `company`: Their company.
- `title`: Their job title.
- `email`: Their email address.
- `research`: Research brief on this prospect.
- `rules`: The global rules from rules.md.

## Output Schema
```json
{
  "content_type": "outreach_email",
  "subject": "<email subject line>",
  "draft_text": "<email body in plain text>",
  "evidence_snippets": ["<research references used>"],
  "confidence_score": 0.0
}
```

## Guidelines
- Subject line: specific, under 60 characters, no clickbait.
- Open with something real about them or their company. Not "I hope this finds you well."
- Body should be 3-5 short paragraphs max.
- One clear value proposition. One clear ask.
- Sign off as "Luma Growth Lab" team.
- If research is "Not found," keep it honest and brief — focus on role/industry relevance.
