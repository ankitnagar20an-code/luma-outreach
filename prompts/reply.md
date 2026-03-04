# Inbound Reply Generation

Generate a reply to an inbound LinkedIn message.

## Input
You will receive:
- `sender_name`: Who sent the message.
- `sender_url`: Their LinkedIn profile URL.
- `message_text`: The inbound message content.
- `research`: Any research on the sender or their company.
- `rules`: The global rules from rules.md.

## Output Schema
```json
{
  "content_type": "inbound_reply",
  "draft_text": "<reply message text>",
  "evidence_snippets": ["<research references if relevant>"],
  "confidence_score": 0.0
}
```

## Guidelines
- Acknowledge what they said specifically. Show you read the message.
- Be warm but not sycophantic. Professional but not stiff.
- If they asked a question, answer it directly before adding context.
- If research reveals something relevant about their work, reference it naturally.
- Keep it conversational. This is a DM, not an essay.
- End with a clear next step (question, suggestion to chat, resource to share).
