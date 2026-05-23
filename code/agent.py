import os
import re
import json
import logging
import time
import requests
from collections import defaultdict
from pydantic import BaseModel, Field
from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types

    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

load_dotenv()

# ---------------------------------------------------------------------------
# Tri-Mode Configuration:
# 1. OPENROUTER_API_KEY → Uses Open Router (Claude 3 Haiku, best for this task)
# 2. GEMINI_API_KEY → Uses Gemini 2.0 Flash (fallback)
# 3. Neither → Falls back to Ollama (local, no quota)
# ---------------------------------------------------------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Temporarily disable Open Router due to account credit issue, fallback to Gemini
USE_OPENROUTER = False  # bool(OPENROUTER_API_KEY)
USE_GEMINI = HAS_GEMINI and bool(GEMINI_API_KEY) and not USE_OPENROUTER

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:1b")

MAX_CORPUS_CHARS = 40_000 if (USE_OPENROUTER or USE_GEMINI) else 6_000
INTER_TICKET_DELAY = 8 if USE_OPENROUTER else (12 if USE_GEMINI else 0)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"


class TicketResponse(BaseModel):
    status: str = Field(description="'replied' or 'escalated'")
    product_area: str = Field(
        description="most relevant support category or domain area"
    )
    response: str = Field(
        description="user-facing answer grounded in the corpus, or polite out-of-scope message"
    )
    justification: str = Field(
        description="concise explanation of the routing/answering decision"
    )
    request_type: str = Field(
        description="'product_issue', 'feature_request', 'bug', or 'invalid'"
    )


class SupportAgent:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.chunks = self._load_corpus_chunks()

        if USE_OPENROUTER:
            logger.info("Initialized with Open Router (Claude 3 Haiku).")
            self.client = None  # Uses HTTP requests
        elif USE_GEMINI:
            logger.info("Initialized with Gemini API (key detected).")
            self.client = genai.Client()
        else:
            logger.info("Initialized with Ollama Local Mode (no API key).")
            self._check_ollama()

    def _check_ollama(self):
        try:
            r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            models = [m["name"] for m in r.json().get("models", [])]
            logger.info("Ollama running. Available models: %s", models)
            if not any(OLLAMA_MODEL.split(":")[0] in m for m in models):
                logger.warning(
                    "Model '%s' not found locally! Run: ollama pull %s",
                    OLLAMA_MODEL,
                    OLLAMA_MODEL,
                )
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                "Ollama is not running! Ensure it is installed from ollama.com"
            )

    def _load_corpus_chunks(self, chunk_size: int = 1500):
        chunks = defaultdict(list)
        for company in ["claude", "hackerrank", "visa"]:
            company_dir = os.path.join(self.data_dir, company)
            if not os.path.exists(company_dir):
                continue
            for root, dirs, files in os.walk(company_dir):
                for fname in files:
                    if not (fname.endswith(".md") or fname.endswith(".txt")):
                        continue
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            text = f.read()
                    except Exception:
                        continue
                    for i in range(0, len(text), chunk_size):
                        chunk = text[i : i + chunk_size + 300]
                        chunks[company].append((fname, chunk))
        return dict(chunks)

    def _retrieve_relevant_chunks(
        self, query: str, company: str, max_chars: int = MAX_CORPUS_CHARS
    ):
        stop_words = {
            "the",
            "and",
            "for",
            "that",
            "this",
            "with",
            "have",
            "from",
            "are",
            "was",
            "not",
            "but",
            "they",
            "you",
            "your",
            "our",
            "can",
            "will",
            "how",
            "what",
            "when",
            "where",
            "which",
            "who",
            "their",
            "there",
            "been",
            "has",
            "had",
            "its",
            "also",
            "all",
        }
        tokens = set(
            w.lower()
            for w in re.findall(r"\b[a-zA-Z]{3,}\b", query)
            if w.lower() not in stop_words
        )

        companies_to_search = (
            [company] if company in self.chunks else list(self.chunks.keys())
        )

        scored = []
        for co in companies_to_search:
            for fname, chunk in self.chunks.get(co, []):
                chunk_lower = chunk.lower()
                score = sum(1 for t in tokens if t in chunk_lower)
                score += sum(1 for t in tokens if t in fname.lower())
                scored.append((score, co, fname, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)

        result_parts = []
        total = 0
        seen_chunks = set()
        for score, co, fname, chunk in scored:
            key = (co, fname, chunk[:50])
            if key in seen_chunks:
                continue
            seen_chunks.add(key)
            if total + len(chunk) > max_chars:
                break
            result_parts.append(f"--- [{co.upper()}] {fname} ---\n{chunk}")
            total += len(chunk)

        return "\n\n".join(result_parts)

    def process_ticket(self, issue: str, subject: str, company: str):
        company_lower = str(company).lower().strip()
        query = f"{subject} {issue}"
        corpus_text = self._retrieve_relevant_chunks(query, company_lower)

        system_prompt = """You are a support triage agent. Analyze the ticket and respond ONLY with a valid JSON object.

The JSON must have exactly these fields:
- "status": "replied" if you can fully answer from the corpus, OR "escalated" if human review is needed
- "product_area": specific support area (e.g. "Billing", "Account Access", "Test Issues", "Platform Bug")
- "response": a helpful user-facing reply grounded strictly in the corpus, or polite out-of-scope message
- "justification": short internal note explaining your routing decision
- "request_type": exactly one of "product_issue", "feature_request", "bug", or "invalid"

Critical rules:
1. ESCALATE (status=escalated) for: fraud, identity theft, refunds, payment disputes, sensitive financial matters, security vulnerabilities, or when the corpus has no answer.
2. Mark request_type="invalid" for malicious requests (e.g. asking to delete files, asking for internal system info) or completely off-topic requests.
3. Mark request_type="bug" ONLY for actual platform bugs (site down, submissions broken, feature not loading).
4. Mark request_type="product_issue" for account questions, policy questions, how-to questions.
5. "replied" means you CAN fully resolve it from the corpus. "escalated" means a human must handle it.
6. Never invent policies. Ground all answers in the provided corpus only."""

        user_prompt = f"""Support Ticket:
Company: {company}
Subject: {subject}
Issue: {issue}

Support Corpus (most relevant excerpts):
{corpus_text}

IMPORTANT: Reply with a JSON object ONLY. No explanation, no markdown. Just the JSON."""

        if USE_OPENROUTER:
            return self._process_with_openrouter(user_prompt, system_prompt)
        elif USE_GEMINI:
            return self._process_with_gemini(user_prompt, system_prompt)
        else:
            return self._process_with_ollama(user_prompt, system_prompt)

    def _process_with_openrouter(self, user_prompt, system_prompt):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    OPENROUTER_BASE_URL,
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "HTTP-Referer": "https://github.com/hackerrank/orchestrate",
                        "X-Title": "HackerRank Orchestrate Agent",
                    },
                    json={
                        "model": "anthropic/claude-3.5-haiku",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 1024,
                        "response_format": {"type": "json_object"},
                    },
                    timeout=30,
                )
                response.raise_for_status()
                result = response.json()

                # Extract the JSON from the response
                content = (
                    result.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "{}")
                )
                parsed = json.loads(content)

                return {
                    "status": parsed.get("status", "escalated"),
                    "product_area": parsed.get("product_area", "General"),
                    "response": parsed.get("response", ""),
                    "justification": parsed.get("justification", ""),
                    "request_type": parsed.get("request_type", "product_issue"),
                }
            except requests.exceptions.HTTPError as e:
                err_msg = str(e)
                if "429" in err_msg or "rate" in err_msg.lower():
                    # Rate limit hit, exponential backoff
                    wait = min(15 * (2**attempt), 60)
                    if attempt < max_retries - 1:
                        logger.warning(
                            "Rate limit hit on Open Router. Waiting %ds...", wait
                        )
                        time.sleep(wait)
                        continue
                logger.error("HTTP Error from Open Router: %s", err_msg[:200])
                break
            except json.JSONDecodeError as e:
                logger.warning(
                    "JSON decode error (attempt %d): %s", attempt + 1, str(e)[:100]
                )
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
            except Exception as e:
                logger.error(
                    "Error processing ticket with Open Router: %s", str(e)[:200]
                )
                break

        return {
            "status": "escalated",
            "product_area": "unknown",
            "response": "Unable to process ticket after retries.",
            "justification": "Max retries exceeded.",
            "request_type": "product_issue",
        }

    def _process_with_gemini(self, user_prompt, system_prompt):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        response_schema=TicketResponse,
                        temperature=0.1,
                    ),
                )
                return json.loads(response.text)
            except Exception as e:
                err = str(e)
                if (
                    "429" in err
                    or "RESOURCE_EXHAUSTED" in err
                    or "503" in err
                    or "UNAVAILABLE" in err
                ):
                    # Exponential backoff
                    try:
                        delay_match = re.search(
                            r"retry.*?(\d+)\.?\d*s", err, re.IGNORECASE
                        )
                        parsed_wait = int(delay_match.group(1)) if delay_match else 0
                        backoff = min(15 * (2**attempt), 60)
                        wait = (
                            max(parsed_wait + 5, backoff)
                            if parsed_wait > 0
                            else backoff
                        )
                    except Exception:
                        wait = min(15 * (2**attempt), 60)

                    if attempt < max_retries - 1:
                        logger.warning("Rate limit hit. Waiting %ds...", wait)
                        time.sleep(wait)
                        continue
                logger.error("Error processing ticket with Gemini: %s", err[:200])
                break

        return {
            "status": "escalated",
            "product_area": "unknown",
            "response": "Unable to process ticket after retries.",
            "justification": "Max retries exceeded.",
            "request_type": "product_issue",
        }

    def _process_with_ollama(self, user_prompt, system_prompt):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    f"{OLLAMA_BASE_URL}/api/chat",
                    json={
                        "model": OLLAMA_MODEL,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "format": "json",
                        "stream": False,
                        "think": False,
                        "options": {"temperature": 0.1, "num_ctx": 8192},
                    },
                    timeout=180,
                )
                resp.raise_for_status()
                raw = resp.json()["message"]["content"]
                text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
                parsed = json.loads(text)
                return {
                    "status": parsed.get("status", "escalated"),
                    "product_area": parsed.get("product_area", "General"),
                    "response": parsed.get("response", ""),
                    "justification": parsed.get("justification", ""),
                    "request_type": parsed.get("request_type", "product_issue"),
                }
            except Exception as e:
                logger.warning(
                    "Ollama error (attempt %d): %s", attempt + 1, str(e)[:100]
                )
                time.sleep(3)

        return {
            "status": "escalated",
            "product_area": "unknown",
            "response": "Unable to process this ticket automatically.",
            "justification": "Max retries exceeded.",
            "request_type": "product_issue",
        }
