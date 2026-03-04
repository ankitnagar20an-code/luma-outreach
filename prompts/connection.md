# Connection Request Note Generation

Generate a LinkedIn connection request note (max 300 characters).

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
  "content_type": "connection_request",
  "draft_text": "<note text, max 300 characters>",
  "evidence_snippets": ["<what prompted the connection>"],
  "confidence_score": 0.0
}
```

## Guidelines
- 300 character limit is hard (LinkedIn enforces this).
- Lead with something specific: shared interest, their recent post, mutual connection context.
- If research is "Not found," write a genuine, brief note about why you'd like to connect based on their role/industry.
- Never pitch in a connection request. The goal is to start a conversation.
- One sentence is often better than two.
