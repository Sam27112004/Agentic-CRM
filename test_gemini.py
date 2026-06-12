import json
from backend.database import SessionLocal
from backend.models.email import Email
from backend.services.agent import _build_agent_context, AGENT_SYSTEM_PROMPT, _build_tools_description, _call_gemini_agent

db = SessionLocal()
email = db.get(Email, 1)

classification = {
    'category': email.category,
    'sentiment': 'Neutral',
    'sentiment_score': 0,
    'urgency': email.urgency or 'Medium',
    'confidence': 0.95,
    'requires_human': False,
    'escalation_reason': '',
}

context = _build_agent_context(email, classification, None)
system_prompt = AGENT_SYSTEM_PROMPT.format(tools_description=_build_tools_description(), max_steps=5)

messages = [{'role': 'user', 'content': context}]
raw_resp1 = """{
  "thought": "The user is asking about non-profit discounts for the enterprise plan.",
  "action": "search_knowledge_base",
  "action_input": {"query": "non-profit discount policy enterprise plan"},
  "is_final": false
}"""
messages.append({'role': 'assistant', 'content': raw_resp1})
observation_text = '{"query": "non-profit discount", "results": [{"chunk_text": "We offer a 30% discount off the Standard tier.", "source_doc": "pricing.md"}]}'
messages.append({'role': 'user', 'content': f'Observation:\n{observation_text}\n\nContinue reasoning. What is your next step?'})

print('Calling Gemini Step 2...')
try:
    response = _call_gemini_agent(system_prompt, messages)
    print('RESPONSE:')
    print(repr(response))
except Exception as e:
    print('ERROR:', e)
