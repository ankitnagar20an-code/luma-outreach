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
  "draft_text": "<email body — see formatting rules below>",
  "evidence_snippets": ["<research references used>"],
  "confidence_score": 0.0
}
```

## Email Formatting Rules
- Use `\n\n` to separate paragraphs. Never put multiple sentences in one long block.
- Structure the email exactly like this:

```
Hi [First Name],

[Opening paragraph — 1-2 sentences referencing something specific about them or their work.]

[Value paragraph — 1-2 sentences about what you can offer or why you're reaching out.]

[Ask paragraph — 1 sentence with a clear, low-pressure call to action.]

Best regards,
Ankit Nagar
Luma Growth Lab
```

- The greeting ("Hi [Name],") must be on its own line followed by a blank line.
- Each paragraph must be separated by a blank line (`\n\n`).
- The sign-off must be on separate lines:
  - "Best regards," then `\n`
  - "Ankit Nagar" then `\n`
  - "Luma Growth Lab"
- NEVER run the body text into the sign-off on the same line.
- NEVER start with "I hope this email finds you well" or similar filler.

## Guidelines
- Subject line: specific, under 60 characters, no clickbait.
- Open with something real about them or their company — a project, a role change, a published piece.
- Body should be 3-4 short paragraphs max (1-2 sentences each).
- One clear value proposition. One clear ask (e.g., "Would you be open to a quick call?").
- Keep total email under 150 words.
- If research is "Not found," keep it honest and brief — focus on role/industry relevance.
