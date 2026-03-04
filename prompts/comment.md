# LinkedIn Comment Generation

Generate a thoughtful comment on a target LinkedIn post.

## Input
You will receive:
- `post_url`: The LinkedIn post URL.
- `post_content`: The text of the post being commented on (if available).
- `topic`: The topic or context of the post.
- `research`: Any relevant research to add value.
- `rules`: The global rules from rules.md.

## Output Schema
```json
{
  "content_type": "linkedin_comment",
  "draft_text": "<comment text, max 500 characters>",
  "evidence_snippets": ["<real source references if used>"],
  "confidence_score": 0.0
}
```

## Guidelines
- Add genuine value. Agree AND extend with a new data point or perspective.
- Never write "Great post!" or empty praise.
- Reference specific parts of the original post to show you actually read it.
- If research provides a relevant stat or example, weave it in naturally.
- Keep it under 500 characters. One focused point beats three scattered ones.
