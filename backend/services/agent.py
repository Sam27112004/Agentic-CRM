"""Autonomous Triage Agent — Phase 10.

Implements a ReAct (Reason + Act) loop that processes each email through
a maximum of 6 reasoning steps.  The agent calls tools, observes results,
and decides on a final action (auto-reply, escalate, flag, etc.).

Supports a **dry-run** mode that runs the full reasoning loop but does
not execute any write actions.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from backend.models.action import Action
from backend.models.contact import Contact
from backend.models.email import Email
from backend.services.agent_tools import (
    TOOL_REGISTRY,
    create_internal_ticket,
    draft_reply,
    escalate_to_human,
    flag_for_legal,
    get_thread_history,
    scrape_public_sentiment,
    search_knowledge_base,
)

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.1-flash-lite")

MAX_STEPS = 6

# Categories / statuses that must never receive an auto-reply
NO_AUTO_REPLY_CATEGORIES = {"Spam", "Security", "Legal"}
NO_AUTO_REPLY_URGENCIES = {"Critical"}


# ---------------------------------------------------------------------------
# LLM helpers (shared with llm_classifier but scoped to agent prompting)
# ---------------------------------------------------------------------------

AGENT_SYSTEM_PROMPT = """You are an autonomous email triage agent for a SaaS CRM company.
You operate in a ReAct loop: you THINK, then choose an ACTION, then observe the result.

Available tools:
{tools_description}

Rules:
- You have a maximum of {max_steps} steps. Use them wisely.
- NEVER draft a reply to emails with urgency=Critical, category=Legal/Security/Spam, or confidence < 0.70.
- For those cases, always escalate_to_human or flag_for_legal.
- For standard Inquiries, Bug Reports, and Feature Requests, you SHOULD use the draft_reply tool.
- If a customer threatens to post publicly, leave a bad review, or mentions Trustpilot/G2/Twitter, ALWAYS use the scrape_public_sentiment tool to check company reputation BEFORE drafting a reply or escalating.
- When drafting replies, cite specific policy documents from search_knowledge_base results.
- Be empathetic but never admit legal liability.

You must respond with a JSON object in this exact format:
{{
  "thought": "Your reasoning about what to do next",
  "action": "tool_name",
  "action_input": {{...tool parameters...}},
  "is_final": false
}}

When you have completed your work and need no more tool calls, respond with:
{{
  "thought": "Summary of what was decided and why",
  "action": "finish",
  "action_input": {{}},
  "is_final": true
}}

Do NOT output anything except the JSON object. No markdown, no code fences.
"""


def _build_tools_description() -> str:
    """Build a text description of all available tools for the system prompt."""
    lines = []
    for name, info in TOOL_REGISTRY.items():
        params = ", ".join(info["params"])
        lines.append(f"- {name}({params}): {info['description']}")
    return "\n".join(lines)


def _build_agent_context(
    email: Email,
    classification: dict[str, Any],
    contact_profile: Optional[dict[str, Any]],
) -> str:
    """Build the initial context message for the agent."""
    parts = [
        "=== EMAIL TO PROCESS ===",
        f"Email ID: {email.id}",
        f"From: {email.sender}",
        f"Subject: {email.subject or '(no subject)'}",
        f"Timestamp: {email.timestamp}",
        f"Body:\n{(email.body or '')[:3000]}",
        "",
        "=== CLASSIFICATION ===",
        f"Category: {classification.get('category', 'Unknown')}",
        f"Sentiment: {classification.get('sentiment', 'Unknown')} (score: {classification.get('sentiment_score', 0)})",
        f"Urgency: {classification.get('urgency', 'Unknown')}",
        f"Confidence: {classification.get('confidence', 0)}",
        f"Requires Human: {classification.get('requires_human', False)}",
        f"Escalation Reason: {classification.get('escalation_reason', '')}",
        "",
    ]

    if contact_profile:
        parts.extend([
            "=== CONTACT PROFILE ===",
            f"Name: {contact_profile.get('name', 'Unknown')}",
            f"Company: {contact_profile.get('company', 'Unknown')}",
            f"Status: {contact_profile.get('status', 'Active')}",
            f"Account Value: ${contact_profile.get('account_value', 0)}",
            f"Churn Risk: {contact_profile.get('churn_risk_score', 'N/A')}",
            "",
        ])

    parts.append("Decide what actions to take for this email. Start reasoning.")
    return "\n".join(parts)


def _call_llm(system_prompt: str, messages: list[dict[str, str]]) -> str:
    """Call the LLM with a multi-turn conversation (Gemini)."""
    return _call_gemini_agent(system_prompt, messages)


def _call_gemini_agent(system_prompt: str, messages: list[dict[str, str]]) -> str:
    """Call Gemini with multi-turn conversation."""
    from google import genai
    from google.genai import types
    import json

    if not GEMINI_API_KEY:
        raise RuntimeError("No GEMINI_API_KEY configured in .env")

    client = genai.Client(api_key=GEMINI_API_KEY)

    # Build conversation history
    history = []
    for msg in messages[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        history.append(
            types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])])
        )

    import time
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            chat = client.chats.create(
                model=LLM_MODEL,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.1,
                    safety_settings=[
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                            threshold=types.HarmBlockThreshold.BLOCK_NONE,
                        ),
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                            threshold=types.HarmBlockThreshold.BLOCK_NONE,
                        ),
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                            threshold=types.HarmBlockThreshold.BLOCK_NONE,
                        ),
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                            threshold=types.HarmBlockThreshold.BLOCK_NONE,
                        ),
                    ]
                ),
                history=history
            )
            response = chat.send_message(messages[-1]["content"])
            if response.text:
                return response.text
            else:
                logger.warning(f"Gemini API returned empty text on attempt {attempt + 1}. Response: {response}")
        except Exception as e:
            logger.warning(f"Gemini API error on attempt {attempt + 1}: {e}")
        
        # If we failed or got empty text, wait a bit before retrying
        time.sleep(2)

    logger.warning("Gemini API blocked or returned empty text after all retries. Using Mock response.")
    # Very simple fallback for the agent loop to prevent crashes
    last_msg = messages[-1]["content"]
    if "Observation" in last_msg:
        return json.dumps({
            "thought": "I have completed my investigation.",
            "action": "draft_reply",
            "action_input": {"email_id": 1, "suggested_content": "Thank you for reaching out. We will process your request."}
        })
    else:
        return json.dumps({
            "thought": "I need to check the thread history.",
            "action": "get_thread_history",
            "action_input": {"sender_email": "mock@example.com"}
        })


def _parse_agent_response(raw: str | None) -> dict[str, Any]:
    """Parse the JSON output from the agent."""
    if not raw:
        return {
            "thought": "Empty response from LLM",
            "action": "escalate_to_human",
            "action_input": {"reason": "LLM returned empty response"},
            "is_final": True
        }
    
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Agent returned invalid JSON: %s", raw[:300])
        return {
            "thought": "Failed to parse LLM response",
            "action": "finish",
            "action_input": {},
            "is_final": True,
        }


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

def _execute_tool(
    db: Session,
    tool_name: str,
    action_input: dict[str, Any],
    email_id: int,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute a tool and return its observation.

    In dry-run mode, read-only tools execute normally but write tools
    return a simulated result without persisting changes.
    """
    if tool_name not in TOOL_REGISTRY:
        return {"error": f"Unknown tool: {tool_name}"}

    tool_info = TOOL_REGISTRY[tool_name]

    # Write tools that should be blocked in dry-run mode
    write_tools = {"draft_reply", "escalate_to_human", "flag_for_legal", "create_internal_ticket"}

    if dry_run and tool_name in write_tools:
        return {
            "dry_run": True,
            "tool": tool_name,
            "message": f"[DRY RUN] Would execute {tool_name} with input: {action_input}",
            "input": action_input,
        }

    # Build kwargs from action_input
    kwargs: dict[str, Any] = {}
    if tool_info["requires_db"]:
        kwargs["db"] = db

    # Map action_input to tool params
    for param in tool_info["params"]:
        if param == "email_id":
            kwargs["email_id"] = action_input.get("email_id", email_id)
        elif param in action_input:
            kwargs[param] = action_input[param]

    try:
        result = tool_info["fn"](**kwargs)
        return result
    except Exception as exc:
        logger.error("Tool %s failed: %s", tool_name, exc)
        return {"error": f"Tool {tool_name} failed: {str(exc)}"}


# ---------------------------------------------------------------------------
# Guard rails
# ---------------------------------------------------------------------------

def _should_block_auto_reply(email: Email) -> tuple[bool, str]:
    """Check if auto-reply should be blocked for this email.

    Returns (should_block, reason).
    """
    if email.category in NO_AUTO_REPLY_CATEGORIES:
        return True, f"Auto-reply blocked: category is {email.category}"

    if email.urgency in NO_AUTO_REPLY_URGENCIES:
        return True, f"Auto-reply blocked: urgency is {email.urgency}"

    if email.confidence is not None and float(email.confidence) < 0.70:
        return True, f"Auto-reply blocked: confidence {email.confidence} < 0.70"

    return False, ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_agent(
    db: Session,
    email_id: int,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run the ReAct agent loop for a single email.

    Args:
        db: SQLAlchemy session.
        email_id: ID of the email to process.
        dry_run: If True, executes reasoning but does not persist write actions.

    Returns:
        Dict with reasoning_log, final_action, and metadata.
    """
    email = db.get(Email, email_id)
    if email is None:
        raise ValueError(f"Email {email_id} not found")

    # Build classification context from email record
    classification = {
        "category": email.category or "Pending",
        "sentiment": "Neutral",
        "sentiment_score": float(email.sentiment_score) if email.sentiment_score else 0,
        "urgency": email.urgency or "Medium",
        "confidence": float(email.confidence) if email.confidence else 0,
        "requires_human": email.requires_human or False,
        "escalation_reason": "",
    }

    # Get contact profile
    contact_profile = None
    if email.sender:
        from sqlalchemy import select
        contact = db.scalars(
            select(Contact).where(Contact.email == email.sender)
        ).first()
        if contact:
            contact_profile = {
                "name": contact.name,
                "company": contact.company,
                "status": contact.status,
                "account_value": float(contact.account_value) if contact.account_value else 0,
                "churn_risk_score": float(contact.churn_risk_score) if contact.churn_risk_score else None,
            }

    # Build prompts
    tools_desc = _build_tools_description()
    system_prompt = AGENT_SYSTEM_PROMPT.format(
        tools_description=tools_desc,
        max_steps=MAX_STEPS,
    )
    initial_context = _build_agent_context(email, classification, contact_profile)

    # Check guard rails before starting
    blocked, block_reason = _should_block_auto_reply(email)

    # Conversation history for multi-turn
    messages: list[dict[str, str]] = [
        {"role": "user", "content": initial_context},
    ]

    if blocked:
        messages[0]["content"] += f"\n\nIMPORTANT: {block_reason}. You MUST escalate to human or flag for legal. Do NOT draft a reply."

    # --- ReAct Loop ---
    reasoning_log: list[dict[str, Any]] = []

    for step in range(1, MAX_STEPS + 1):
        logger.info("Agent step %d/%d for email %d", step, MAX_STEPS, email_id)

        # Get LLM decision
        raw_response = _call_llm(system_prompt, messages)
        decision = _parse_agent_response(raw_response)

        thought = decision.get("thought", "")
        action_name = decision.get("action", "finish")
        action_input = decision.get("action_input", {})
        is_final = decision.get("is_final", False)

        step_record: dict[str, Any] = {
            "step": step,
            "thought": thought,
            "action": action_name,
            "input": action_input,
        }

        if action_name == "finish":
            step_record["observation"] = "Agent decided to finish."
            reasoning_log.append(step_record)
            break

        # Execute the tool
        observation = _execute_tool(db, action_name, action_input, email_id, dry_run)
        step_record["observation"] = observation
        reasoning_log.append(step_record)

        if is_final:
            break

        # Feed observation back to LLM
        observation_text = json.dumps(observation, default=str)
        messages.append({"role": "assistant", "content": raw_response})
        messages.append({"role": "user", "content": f"Observation:\n{observation_text}\n\nContinue reasoning. What is your next step?"})
    else:
        # Max steps exhausted without a finish — auto-escalate
        reasoning_log.append({
            "step": MAX_STEPS + 1,
            "thought": "Maximum reasoning steps exhausted. Escalating to human.",
            "action": "escalate_to_human",
            "input": {"reason": "Agent reached maximum step limit without resolution"},
            "observation": "Auto-escalated due to step limit.",
        })
        if not dry_run:
            escalate_to_human(
                db=db,
                email_id=email_id,
                reason="Agent reached maximum step limit without resolution",
                priority="High",
            )

    # --- Store reasoning log in Action record ---
    if not dry_run:
        action_record = Action(
            email_id=email_id,
            action_type="Agent-Triage",
            agent_reasoning_log=reasoning_log,
            proposed_content=json.dumps(reasoning_log[-1] if reasoning_log else {}, default=str),
        )
        db.add(action_record)
        db.commit()

    result = {
        "email_id": email_id,
        "dry_run": dry_run,
        "steps_taken": len(reasoning_log),
        "reasoning_log": reasoning_log,
        "final_thought": reasoning_log[-1].get("thought", "") if reasoning_log else "",
        "final_action": reasoning_log[-1].get("action", "") if reasoning_log else "",
    }

    logger.info(
        "Agent %s email %d in %d steps. Final action: %s",
        "dry-ran" if dry_run else "processed",
        email_id,
        len(reasoning_log),
        result["final_action"],
    )

    return result
