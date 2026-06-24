"""
llm_client.py — provider-agnostic JSON completion for the Happy Hour pipeline.

The default provider is OLLAMA: a local model running on your own machine.
It is free, private, and costs **no Anthropic tokens** — nothing leaves the box.

Pick the provider with the env var LLM_PROVIDER:

    ollama     (default)  Local Ollama daemon. Install once: https://ollama.com
                          then `ollama pull llama3.1` (or qwen2.5, llama3.2:3b…).
    openai                Any OpenAI-compatible endpoint — LM Studio, a free
                          Groq tier, etc. Still no Anthropic cost.
    anthropic             Claude API. Costs tokens. Kept only as an opt-in.

Relevant env vars:
    LLM_PROVIDER      ollama | openai | anthropic            (default: ollama)
  Ollama:
    OLLAMA_HOST       default http://localhost:11434
    OLLAMA_MODEL      default llama3.1
  OpenAI-compatible:
    OPENAI_BASE_URL   e.g. http://localhost:1234/v1  |  https://api.groq.com/openai/v1
    OPENAI_API_KEY    key for that endpoint ("not-needed" works for most local ones)
    OPENAI_MODEL      model name the endpoint serves
  Anthropic:
    ANTHROPIC_API_KEY
    ANTHROPIC_MODEL   default claude-opus-4-8

Every backend returns a parsed dict that conforms to the JSON schema you pass —
the caller (pass1_llm.py) never knows which model produced it.
"""

import json
import os

PROVIDER = os.environ.get('LLM_PROVIDER', 'ollama').lower()


def provider_info():
    """Human-readable 'who am I using' string for startup logging."""
    if PROVIDER == 'ollama':
        return (f"ollama / {os.environ.get('OLLAMA_MODEL', 'llama3.1')} "
                f"@ {os.environ.get('OLLAMA_HOST', 'http://localhost:11434')}  (local, no token cost)")
    if PROVIDER == 'anthropic':
        return f"anthropic / {os.environ.get('ANTHROPIC_MODEL', 'claude-opus-4-8')}  (COSTS TOKENS)"
    return (f"openai-compatible / {os.environ.get('OPENAI_MODEL', '?')} "
            f"@ {os.environ.get('OPENAI_BASE_URL', '?')}")


def complete_json(system, user, schema, max_tokens=2048):
    """Run one structured-output completion and return the parsed JSON dict."""
    if PROVIDER == 'ollama':
        return _ollama(system, user, schema, max_tokens)
    if PROVIDER in ('openai', 'openai-compatible', 'lmstudio', 'groq'):
        return _openai(system, user, schema, max_tokens)
    if PROVIDER == 'anthropic':
        return _anthropic(system, user, schema, max_tokens)
    raise RuntimeError(f"Unknown LLM_PROVIDER={PROVIDER!r} (use ollama | openai | anthropic)")


def preflight():
    """Cheap reachability/error check so a batch fails fast with a clear message."""
    if PROVIDER == 'ollama':
        import requests
        host = os.environ.get('OLLAMA_HOST', 'http://localhost:11434').rstrip('/')
        model = os.environ.get('OLLAMA_MODEL', 'llama3.1')
        try:
            tags = requests.get(f'{host}/api/tags', timeout=5).json().get('models', [])
        except Exception as e:
            raise RuntimeError(
                f"Can't reach Ollama at {host}. Install it (https://ollama.com), then it "
                f"runs automatically. Error: {e}")
        names = [m.get('name', '') for m in tags]
        if not any(n == model or n.startswith(model + ':') or n.split(':')[0] == model for n in names):
            raise RuntimeError(
                f"Ollama model {model!r} not pulled. Run:  ollama pull {model}\n"
                f"Installed: {', '.join(names) or '(none)'}")
    elif PROVIDER == 'anthropic':
        if not os.environ.get('ANTHROPIC_API_KEY'):
            raise RuntimeError('ANTHROPIC_API_KEY not set (and anthropic COSTS TOKENS).')
    elif PROVIDER in ('openai', 'openai-compatible', 'lmstudio', 'groq'):
        if not os.environ.get('OPENAI_BASE_URL'):
            raise RuntimeError('OPENAI_BASE_URL not set for the openai-compatible provider.')


# ── backends ──────────────────────────────────────────────────────────────────
def _ollama(system, user, schema, max_tokens):
    import requests
    host = os.environ.get('OLLAMA_HOST', 'http://localhost:11434').rstrip('/')
    model = os.environ.get('OLLAMA_MODEL', 'llama3.1')
    r = requests.post(f'{host}/api/chat', timeout=600, json={
        'model': model,
        'messages': [{'role': 'system', 'content': system},
                     {'role': 'user', 'content': user}],
        'stream': False,
        'format': schema,            # JSON-schema structured output (Ollama >= 0.5)
        'options': {'temperature': 0, 'num_predict': max_tokens},
    })
    r.raise_for_status()
    return json.loads(r.json()['message']['content'])


def _openai(system, user, schema, max_tokens):
    import requests
    base = os.environ.get('OPENAI_BASE_URL', 'http://localhost:1234/v1').rstrip('/')
    key = os.environ.get('OPENAI_API_KEY', 'not-needed')
    model = os.environ.get('OPENAI_MODEL', 'local-model')
    r = requests.post(f'{base}/chat/completions', timeout=600,
                      headers={'Authorization': f'Bearer {key}'},
                      json={
                          'model': model,
                          'messages': [{'role': 'system', 'content': system},
                                       {'role': 'user', 'content': user}],
                          'temperature': 0,
                          'max_tokens': max_tokens,
                          'response_format': {
                              'type': 'json_schema',
                              'json_schema': {'name': 'result', 'schema': schema, 'strict': True},
                          },
                      })
    r.raise_for_status()
    return json.loads(r.json()['choices'][0]['message']['content'])


def _anthropic(system, user, schema, max_tokens):
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=os.environ.get('ANTHROPIC_MODEL', 'claude-opus-4-8'),
        max_tokens=max_tokens,
        thinking={'type': 'adaptive'},
        system=system,
        messages=[{'role': 'user', 'content': user}],
        output_config={'format': {'type': 'json_schema', 'schema': schema}},
    )
    text = next((b.text for b in resp.content if b.type == 'text'), '')
    return json.loads(text)
