# Follow-up DM Generation

Generate a LinkedIn follow-up direct message for an existing connection.

## Input
You will receive:
- `prospect_name`: The person's name.
- `company`: Their company.
- `title`: Their job title.
- `research`: Research brief on this prospect.
- `previous_interaction`: Summary of prior outreach (connection note, previous DM, etc.).
- `rules`: The global rules from rules.md.

## Output Schema
```json
{
  "content_type": "follow_up_dm",
  "draft_text": "<DM text>",
  "evidence_snippets": ["<research references used>"],
  "confidence_score": 0.0
}
```

## Guidelines
- Reference the previous interaction naturally. "Following up on..." is fine if brief.
- Add new value: share a relevant article, insight, or offer something useful.
- If research found recent news about them, use it as the reason for reaching out again.
- Keep it under 300 words. DMs are conversations, not essays.
- End with a low-friction ask (not "Let's book a call" — try "Would this be relevant to what you're working on?").
