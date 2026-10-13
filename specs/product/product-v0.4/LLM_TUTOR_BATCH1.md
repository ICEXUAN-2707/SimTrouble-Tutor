# LLM Tutor Batch 1 Implementation Note

## Scope

This batch delivers the minimum safe backend loop for the frozen Product v0.4
Tutor contract:

- learner-safe context projection from SessionView;
- deterministic teaching policy;
- provider-neutral async port;
- optional DeepSeek Responses API adapter;
- JSON Schema plus Pydantic output validation;
- deterministic rule fallback;
- process-local, session-scoped conversation history;
- POST /api/v0.4/sessions/{session_id}/tutor;
- unit and HTTP contract tests.

The adapter defaults to deepseek-flash and is disabled unless both
SIMTROUBLE_LLM_ENABLED=true and DEEPSEEK_API_KEY are present.

## Deliberate boundaries

- The LLM does not read authoritative Case data.
- The LLM does not select state transitions or execute suggested actions.
- The LLM does not score the learner.
- Streaming, persistence, authentication, LangGraph, diagnosis evaluation,
  Tutor Trace events, and frontend integration remain outside this batch.
- Provider failures never make the learning flow unavailable.

## Acceptance criteria

1. With LLM disabled, the route returns a valid Tutor response in rule_fallback
   mode.
2. With a valid provider response, the route returns llm mode.
3. Context contains no frozen private-field markers.
4. Output metadata exactly matches deterministic Policy.
5. Invalid, unavailable, timed-out, limited, or unsafe provider responses fall
   back without exposing provider details.
6. Conversation history is isolated by session_id and bounded.
7. Tests perform no real network calls and require no API Key.
