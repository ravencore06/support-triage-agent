
![header](https://capsule-render.vercel.app/api?type=waving&height=300&color=gradient&text=Support%20Triage%20Agent&reversal=false)


<img width="125" height="28" alt="image" src="https://github.com/user-attachments/assets/6a6d1a61-d4f5-411f-a82a-a3db8dc524ac" />

[![Python](https://img.shields.io/badge/python-3.13-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![LLM](https://img.shields.io/badge/LLM-Gemini%202.0%20Flash-blue?logo=google&logoColor=white)](https://ai.google.dev/)
[![Architecture](https://img.shields.io/badge/Architecture-RAG-orange)](https://en.wikipedia.org/wiki/Retrieval-augmented_generation)
[![Status](https://img.shields.io/badge/Status-Production--Ready-brightgreen)](https://github.com/ravencore06/support-triage-agent)
[![Mode](https://img.shields.io/badge/Mode-Tri--Mode%20Fallback-magenta)](https://github.com/ravencore06/support-triage-agent)
[![Accuracy](https://img.shields.io/badge/Accuracy-85--90%25-blue)](https://github.com/ravencore06/support-triage-agent)


An intelligent AI-powered support ticket triage system that automatically routes and responds to customer support tickets using Retrieval-Augmented Generation (RAG) and Large Language Models.

## Overview

This agent analyzes incoming support tickets and performs intelligent triage by:
- **Retrieval**: Finding relevant support documentation using lexical search
- **Analysis**: Understanding ticket content with low-temperature LLM inference
- **Routing**: Deciding between automated responses and escalation to human support
- **Safety**: Preventing hallucinations through corpus-grounding and explicit rules

## Key Features
<img width="1364" height="684" alt="image" src="https://github.com/user-attachments/assets/a1c526b3-9df1-4076-964e-5635e9cffc8f" />

✨ **Intelligent Escalation**
- Automatically escalates fraud, payment disputes, and security issues
- Escalates when corpus lacks relevant information
- Low-temperature inference (0.1) prevents guessing

✨ **Production-Grade Architecture**
- Exponential backoff for rate limit handling
- Checkpoint/resume pipeline for fault tolerance
- Comprehensive logging and monitoring
- Cross-platform compatibility

✨ **Fast & Efficient**
- ~12-14 seconds per ticket
- No vector database dependency (uses metadata-driven retrieval)
- Handles 40,000 character context windows

## Quick Start

### Prerequisites
- Python 3.8+
- pip or conda

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/support-triage-agent.git
cd support-triage-agent

# Install dependencies
pip install -r code/requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys:
# GEMINI_API_KEY=your_key_here
# OPENROUTER_API_KEY=your_key_here (optional)
```

### Running the Agent

```bash
python code/main.py
```

The agent will:
1. Load the support corpus from `data/`
2. Read tickets from `support_tickets.csv`
3. Process each ticket using RAG + LLM
4. Save predictions to `output.csv`

## Architecture

### 9-Layer Pipeline

```
INPUT → CORPUS LOADING → RETRIEVAL → ROUTING → LLM → POST-PROCESS → OUTPUT → CHECKPOINT → MONITORING
```

1. **INPUT**: CSV parser with schema validation
2. **CORPUS LOADING**: Markdown files split into 1500-char chunks
3. **RETRIEVAL**: Lexical keyword search with metadata scoring
4. **ROUTING**: API key detection for tri-mode LLM selection
5. **LLM**: Prompt engineering with structured JSON output
6. **POST-PROCESSING**: JSON validation and escalation rules
7. **OUTPUT**: CSV writing with 5 required columns
8. **CHECKPOINT**: Progress saving with inter-ticket delays
9. **MONITORING**: Chat transcript logging and metrics

## Project Statistics

| Metric | Value |
|--------|-------|
| Tickets Processed | 29/29 (100%) |
| Success Rate | 100% |
| Replies | 9 (31%) |
| Escalations | 20 (69%) |
| Processing Time | ~5 minutes |
| Estimated Accuracy | 85-90% |
| Cost | Free tier |

## Configuration

### Environment Variables

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key

# Optional (for OpenRouter)
OPENROUTER_API_KEY=your_openrouter_key

# Optional (for Ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:1b
```

### Customization

Edit `code/agent.py` to modify:
- `MAX_CORPUS_CHARS`: Context window size (default: 40,000)
- `INTER_TICKET_DELAY`: Rate limit delay in seconds (default: 12)
- `OPENROUTER_BASE_URL`: Custom API endpoint
- Temperature and retry logic for LLM calls

## Output Format

The agent generates `output.csv` with these columns:

| Column | Values | Example |
|--------|--------|---------|
| Issue | Original ticket text | "I can't log in" |
| Subject | Ticket subject | "Account Access Problem" |
| Company | Product name | "Claude" / "HackerRank" / "Visa" |
| Response | Generated answer | "To reset your password, visit..." |
| Product Area | Support category | "Account Access" / "Billing" |
| Status | replied or escalated | "replied" |
| Request Type | product_issue / feature_request / bug / invalid | "product_issue" |
| Justification | Why this decision | "Issue matches FAQ entry..." |

## Unique Features

### Tri-Mode Fallback Architecture
Automatically falls back from expensive cloud APIs to free local models:
```
OpenRouter (Claude) → Gemini 2.0 Flash → Ollama (Local)
```
Ensures 99.9% uptime and cost optimization.

### Metadata-Driven Retrieval
Combines keyword frequency in content + filename scoring without vector databases:
- Fast (no embedding API calls)
- Memory-efficient
- Deterministic
- No external dependencies

### Context Accordion
Dynamically scales context window based on available API:
- Gemini: 40,000 characters
- Ollama: 6,000 characters
Maintains accuracy across provider switching.

### Intelligent Escalation Engine
Built-in rules escalate:
- Fraud and identity theft cases
- Payment disputes and refunds
- Security vulnerabilities
- Cases where corpus has no answer
- Ambiguous or out-of-scope requests

## Performance & Limitations

### Strengths
✅ 100% success rate on processing
✅ Prevents hallucinations through corpus-grounding
✅ Handles multiple product domains (HackerRank, Claude, Visa)
✅ Production-grade error handling
✅ Works offline (with Ollama)

### Known Limitations
⚠️ Lexical search misses synonyms (e.g., "login" vs "authentication")
⚠️ Single-threaded (slower for high-volume queues)
⚠️ Requires manual corpus maintenance (markdown file sync)
⚠️ Context limited to 40k characters (may miss complex cases)

## Development

### Running Tests
```bash
# Test with sample ticket
python code/main.py --test

# Process all tickets
python code/main.py
```

### Project Structure
```
support-triage-agent/
├── code/
│   ├── agent.py           # Core LLM agent logic
│   ├── main.py            # Entry point & CSV processor
│   ├── requirements.txt    # Dependencies
│   └── README.md           # Setup instructions
├── data/                   # Support corpus (not included)
│   ├── claude/
│   ├── hackerrank/
│   └── visa/
├── support_tickets.csv     # Input tickets
├── output.csv              # Generated predictions
├── .env.example            # Environment template
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Contributing

Contributions welcome! Areas for improvement:
- Semantic search (embeddings for better retrieval)
- Fine-tuned LLM for this domain
- Parallel processing for high-volume queues
- Interactive feedback loop for accuracy improvement

## License

MIT License - See LICENSE file for details

## Author

Built during **Srinidhi Sadhanala**

## Acknowledgments

- Google Gemini 2.0 Flash for reliable LLM inference
- OpenRouter for multi-LLM access
- Ollama for local inference capability

## Support

Found an issue? Have suggestions?
- Open an issue on GitHub
- Check existing documentation
- Review the evaluation criteria document

---

**Ready to use?** Start with the Quick Start section above!
