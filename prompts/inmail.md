# InMail Generation

Generate a LinkedIn InMail message for a prospect.

## Input
You will receive:
- `prospect_name`: The person's name.
- `company`: Their company.
- `title`: Their job title.
- `research`: Research brief on this prospect.
- `rules`: The global rules from rules.md.

## Output Schema
```json
{
  "content_type": "inmail",
  "subject": "<InMail subject line, max 200 characters>",
  "draft_text": "<message body>",
  "evidence_snippets": ["<research references used>"],
  "confidence_score": 0.0
}
```

## Guidelines
- Subject line must be specific and curiosity-driven. No "Quick question" or "Reaching out."
- Open with a real observation about their work, company, or industry.
- Keep the body under 500 words. Shorter is better.
- One clear reason you're reaching out. One clear ask.
- If research is "Not found," be transparent: "I came across your profile and..." with honest context.
