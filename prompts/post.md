# LinkedIn Post Generation

Generate a LinkedIn post for the "Luma Growth Lab" profile.

## Input
You will receive:
- `topic`: The subject or theme for the post.
- `research`: Recent news, data points, or trends found via web search.
- `rules`: The global rules from rules.md.

## Output Schema
```json
{
  "content_type": "linkedin_post",
  "draft_text": "<post body, max 1300 characters, with line breaks as \\n>",
  "hashtags": ["<up to 3 relevant hashtags>"],
  "evidence_snippets": ["<real source references used>"],
  "confidence_score": 0.0
}
```

## Guidelines
- Open with a bold, specific observation or counterintuitive take — never a generic question.
- Use real data or examples from the research. If research is "Not found," write from genuine experience without fabricating.
- End with an open question or a thought that invites comments. Not a CTA.
- Max 3 hashtags, placed at the end.
- Short paragraphs. White space is your friend.
