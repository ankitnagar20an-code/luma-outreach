"""
Luma Outreach OS — Main Orchestrator

Autonomous workflow:
1. Read prospects, targets, and inbound messages from Google Sheet.
2. Research each via SerpAPI (Google Search).
3. Generate content via Claude.
4. Execute via LinkedIn (Playwright) and Gmail API.
5. Log all activity back to Google Sheet.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path so scripts can import each other
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

# Load .env file if present
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from sheet_client import SheetClient
from brave_search import WebSearch
from claude_client import ClaudeClient
from linkedin_automation import LinkedInAutomation
from gmail_sender import GmailSender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("luma_outreach")

# ── Daily Caps ──────────────────────────────────────────────────────
MAX_POSTS = 2
MAX_COMMENTS = 10
MAX_CONNECTIONS = 25
MAX_EMAILS = 20
CONFIDENCE_THRESHOLD = 0.7


def run_post_workflow(
    sheet: SheetClient,
    search: WebSearch,
    claude: ClaudeClient,
    linkedin: LinkedInAutomation,
    targets: list[dict],
) -> int:
    """Generate and publish LinkedIn posts. Returns count of posts made."""
    post_targets = [t for t in targets if t.get("topic") and not t.get("post_url")]
    posts_made = 0

    for target in post_targets[:MAX_POSTS]:
        topic = target["topic"]
        logger.info("── Post workflow for topic: %s", topic)

        # Research
        research = search.research_topic(topic)

        # Generate
        draft = claude.generate_post(topic, research)
        confidence = draft.get("confidence_score", 0.0)
        text = draft.get("draft_text", "")
        evidence = draft.get("evidence_snippets", [])

        if confidence < CONFIDENCE_THRESHOLD or not text:
            logger.info("Skipping post (confidence=%.2f): %s", confidence, topic)
            sheet.log_activity("linkedin", "post", topic, "SKIPPED", text, evidence)
            continue

        # Add hashtags if present
        hashtags = draft.get("hashtags", [])
        if hashtags:
            text = text.rstrip() + "\n\n" + " ".join(f"#{h.lstrip('#')}" for h in hashtags)

        # Execute
        result = linkedin.create_post(text)
        status = result["status"]
        sheet.log_activity("linkedin", "post", topic, status, text, evidence)
        if status == "SENT":
            posts_made += 1

    return posts_made


def run_comment_workflow(
    sheet: SheetClient,
    search: WebSearch,
    claude: ClaudeClient,
    linkedin: LinkedInAutomation,
    targets: list[dict],
) -> int:
    """Generate and post comments on target LinkedIn posts. Returns count."""
    comment_targets = [t for t in targets if t.get("post_url")]
    comments_made = 0

    for target in comment_targets[:MAX_COMMENTS]:
        post_url = target["post_url"]
        topic = target.get("topic", "")
        logger.info("── Comment workflow for: %s", post_url)

        # Research
        research = search.research_topic(topic) if topic else "Not found"

        # Generate
        draft = claude.generate_comment(post_url, "", topic, research)
        confidence = draft.get("confidence_score", 0.0)
        text = draft.get("draft_text", "")
        evidence = draft.get("evidence_snippets", [])

        if confidence < CONFIDENCE_THRESHOLD or not text:
            logger.info("Skipping comment (confidence=%.2f): %s", confidence, post_url)
            sheet.log_activity("linkedin", "comment", post_url, "SKIPPED", text, evidence)
            continue

        # Execute
        result = linkedin.post_comment(post_url, text)
        status = result["status"]
        sheet.log_activity("linkedin", "comment", post_url, status, text, evidence)
        if status == "SENT":
            comments_made += 1

    return comments_made


def run_inbound_reply_workflow(
    sheet: SheetClient,
    search: WebSearch,
    claude: ClaudeClient,
    linkedin: LinkedInAutomation,
    inbound: list[dict],
) -> int:
    """Reply to inbound LinkedIn messages. Returns count."""
    replies_sent = 0

    for msg in inbound:
        sender_name = msg.get("sender_name", "Unknown")
        sender_url = msg.get("sender_url", "")
        message_text = msg.get("message_text", "")
        logger.info("── Inbound reply workflow for: %s", sender_name)

        if not sender_url or not message_text:
            logger.warning("Skipping inbound: missing sender_url or message_text")
            continue

        # Research the sender
        research = search.research_prospect(sender_name, "")

        # Generate reply
        draft = claude.generate_reply(sender_name, sender_url, message_text, research)
        confidence = draft.get("confidence_score", 0.0)
        text = draft.get("draft_text", "")
        evidence = draft.get("evidence_snippets", [])

        if confidence < CONFIDENCE_THRESHOLD or not text:
            logger.info("Skipping reply (confidence=%.2f): %s", confidence, sender_name)
            sheet.log_activity("linkedin", "inbound_reply", sender_name, "SKIPPED", text, evidence)
            continue

        # Send DM
        result = linkedin.send_dm(sender_url, text)
        status = result["status"]
        sheet.log_activity("linkedin", "inbound_reply", sender_name, status, text, evidence)
        if status == "SENT":
            replies_sent += 1

    return replies_sent


def run_outreach_workflow(
    sheet: SheetClient,
    search: WebSearch,
    claude: ClaudeClient,
    linkedin: LinkedInAutomation,
    gmail: GmailSender,
    prospects: list[dict],
    linkedin_ok: bool = True,
) -> dict[str, int]:
    """Run full outreach on prospects: connections, InMails, DMs, emails. Returns counts."""
    counts = {"connections": 0, "inmails": 0, "dms": 0, "emails": 0}

    for prospect in prospects:
        name = prospect.get("name", "Unknown")
        company = prospect.get("company", "")
        title = prospect.get("title", "")
        linkedin_url = prospect.get("linkedin_url", "")
        email = prospect.get("email", "")
        logger.info("── Outreach workflow for: %s (%s @ %s)", name, title, company)

        # Research
        raw_research = search.research_prospect(name, company)
        research_brief = claude.synthesize_research(name, company, title, raw_research)
        research_text = raw_research  # Use raw for now; brief provides confidence
        research_confidence = research_brief.get("confidence_score", 0.5)

        # ── Connection Request ──
        if linkedin_ok and linkedin_url and counts["connections"] < MAX_CONNECTIONS:
            draft = claude.generate_connection_note(name, company, title, research_text)
            confidence = draft.get("confidence_score", 0.0)
            note = draft.get("draft_text", "")
            evidence = draft.get("evidence_snippets", [])

            if confidence >= CONFIDENCE_THRESHOLD and note:
                result = linkedin.send_connection_request(linkedin_url, note)
                status = result["status"]
                sheet.log_activity("linkedin", "connection_request", name, status, note, evidence)
                if status == "SENT":
                    counts["connections"] += 1
            else:
                sheet.log_activity("linkedin", "connection_request", name, "SKIPPED", note, evidence)

        # ── InMail (if not connected) ──
        if linkedin_ok and linkedin_url and counts["inmails"] < 10:
            draft = claude.generate_inmail(name, company, title, research_text)
            confidence = draft.get("confidence_score", 0.0)
            subject = draft.get("subject", "")
            text = draft.get("draft_text", "")
            evidence = draft.get("evidence_snippets", [])

            if confidence >= CONFIDENCE_THRESHOLD and text:
                result = linkedin.send_inmail(linkedin_url, subject, text)
                status = result["status"]
                sheet.log_activity("linkedin", "inmail", name, status, text, evidence)
                if status == "SENT":
                    counts["inmails"] += 1
            else:
                sheet.log_activity("linkedin", "inmail", name, "SKIPPED", text, evidence)

        # ── Follow-up DM ──
        if linkedin_ok and linkedin_url and counts["dms"] < 15:
            draft = claude.generate_dm(name, company, title, research_text, "Initial connection")
            confidence = draft.get("confidence_score", 0.0)
            text = draft.get("draft_text", "")
            evidence = draft.get("evidence_snippets", [])

            if confidence >= CONFIDENCE_THRESHOLD and text:
                result = linkedin.send_dm(linkedin_url, text)
                status = result["status"]
                sheet.log_activity("linkedin", "follow_up_dm", name, status, text, evidence)
                if status == "SENT":
                    counts["dms"] += 1
            else:
                sheet.log_activity("linkedin", "follow_up_dm", name, "SKIPPED", text, evidence)

        # ── Email ──
        if email and gmail.can_send:
            draft = claude.generate_email(name, company, title, email, research_text)
            confidence = draft.get("confidence_score", 0.0)
            subject = draft.get("subject", "")
            body = draft.get("draft_text", "")
            evidence = draft.get("evidence_snippets", [])

            if confidence >= CONFIDENCE_THRESHOLD and body:
                result = gmail.send_email(email, subject, body)
                status = result["status"]
                sheet.log_activity("email", "outreach_email", name, status, body, evidence)
                if status == "SENT":
                    counts["emails"] += 1
            else:
                sheet.log_activity("email", "outreach_email", name, "SKIPPED", body, evidence)

    return counts


def main() -> None:
    """Main orchestrator — runs the full Luma Outreach OS pipeline."""
    logger.info("=" * 60)
    logger.info("Luma Outreach OS — Starting autonomous run")
    logger.info("=" * 60)

    # Initialize clients
    sheet = SheetClient()
    search = WebSearch()
    claude = ClaudeClient()
    gmail = GmailSender()
    linkedin = LinkedInAutomation()

    try:
        # Start browser — LinkedIn is optional, email still works without it
        linkedin_ok = False
        try:
            linkedin.start()
            linkedin_ok = linkedin._check_login()
        except Exception as e:
            logger.warning("LinkedIn browser failed to start: %s", e)

        if not linkedin_ok:
            logger.warning("LinkedIn session is invalid. Skipping LinkedIn actions, continuing with email.")
            sheet.log_activity("system", "session_check", "LinkedIn", "FAILED", "Session expired", [])

        # Load data from Google Sheet
        prospects = sheet.get_prospects(status_filter="active")
        targets = sheet.get_targets(status_filter="active")
        inbound = sheet.get_inbound(status_filter="new")

        logger.info("Loaded: %d prospects, %d targets, %d inbound messages", len(prospects), len(targets), len(inbound))

        if linkedin_ok:
            # ── Phase 1: LinkedIn Posts ──
            logger.info("── Phase 1: LinkedIn Posts ──")
            posts_made = run_post_workflow(sheet, search, claude, linkedin, targets)
            logger.info("Posts published: %d/%d", posts_made, MAX_POSTS)

            # ── Phase 2: LinkedIn Comments ──
            logger.info("── Phase 2: LinkedIn Comments ──")
            comments_made = run_comment_workflow(sheet, search, claude, linkedin, targets)
            logger.info("Comments posted: %d/%d", comments_made, MAX_COMMENTS)

            # ── Phase 3: Inbound Replies ──
            logger.info("── Phase 3: Inbound Replies ──")
            replies_sent = run_inbound_reply_workflow(sheet, search, claude, linkedin, inbound)
            logger.info("Inbound replies sent: %d", replies_sent)
        else:
            logger.info("Skipping LinkedIn phases (1-3) — session not available")

        # ── Phase 4: Outreach (Connections, InMails, DMs, Emails) ──
        # Email works even without LinkedIn; LinkedIn actions will be skipped gracefully
        logger.info("── Phase 4: Outreach ──")
        outreach_counts = run_outreach_workflow(sheet, search, claude, linkedin, gmail, prospects, linkedin_ok=linkedin_ok)
        logger.info(
            "Outreach complete — Connections: %d, InMails: %d, DMs: %d, Emails: %d",
            outreach_counts["connections"],
            outreach_counts["inmails"],
            outreach_counts["dms"],
            outreach_counts["emails"],
        )

    except Exception as e:
        logger.exception("Fatal error in orchestrator: %s", e)
        try:
            sheet.log_activity("system", "fatal_error", "orchestrator", "FAILED", str(e), [])
        except Exception:
            pass

    finally:
        linkedin.stop()
        search.close()

    logger.info("=" * 60)
    logger.info("Luma Outreach OS — Run complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
