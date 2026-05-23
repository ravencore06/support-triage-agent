# HackerRank Orchestrate AI Agent

This directory contains the terminal-based AI agent to resolve support tickets for HackerRank, Claude, and Visa.

## Setup Instructions

1. Ensure you have Python 3.8+ installed.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. The agent is configured in **Hybrid Mode**:
   - If a `GEMINI_API_KEY` is present in the environment or `.env` file, it will use the Gemini 2.0 Flash model via the Google GenAI SDK (useful for the automated evaluation on HackerRank).
   - If no key is found, it will safely fallback to **Ollama** running locally using the `gemma3:1b` model.

   **Optional (for cloud evaluation):** Create a `.env` file in the root directory:
   ```
   GEMINI_API_KEY=your_gemini_key_here
   ```
## Running the Agent

To execute the agent and process the `support_tickets.csv` file, run the following command from the repository root:

```bash
python code/main.py
```

The predictions will be saved to `support_tickets/output.csv`.

## Architecture
- **`main.py`**: The entry point that reads the CSV file, includes checkpoint logic for resuming, and saves outputs.
- **`agent.py`**: Contains the `SupportAgent` class which uses keyword retrieval to find relevant corpus chunks. It supports dual-mode routing: querying the Gemini API (if an API key is detected) or querying a local Ollama server as a fallback.
