# telegram-agent-aws

An end-to-end Telegram “agent” deployed on AWS Lambda as a container image. It handles text, voice notes, and photos, and uses Retrieval-Augmented Generation (RAG) + conversation memory to keep replies consistent over time.

## Features

- **Serverless Telegram webhook**: Telegram → API Gateway → AWS Lambda (`lambda_handler`) via container image.
- **Multi-modal chat**:
  - Text → LLM reply
  - Voice → Whisper transcription → LLM reply → optional voice reply via ElevenLabs
  - Photo → vision description → LLM reply
- **Agent workflow**: LangGraph graph with tool-calling and conversation summarization.
- **RAG**: Qdrant vector store + OpenAI embeddings (indexes `data/george_biography.pdf` into a Qdrant collection).
- **Memory**: MongoDB checkpointer for per-user conversation threads.
- **Observability**: Opik tracer hooks (configured via Comet/Opik credentials).

## Tech stack

Python, AWS Lambda (container image), API Gateway, `python-telegram-bot`, LangGraph/LangChain, OpenAI (chat/vision, Whisper, embeddings), Qdrant, MongoDB, ElevenLabs, GitHub Actions + ECR.

## Project structure

```text
.
├── .github/workflows/
│   └── deploy_aws_lambda.yaml         # CI/CD: build → push to ECR → deploy to Lambda
├── Dockerfile                         # Lambda container image build
├── Makefile                           # Common dev tasks (format/lint/index)
├── pyproject.toml                     # Project metadata + dependencies
├── uv.lock                            # Locked dependencies (uv)
├── data/
│   └── george_biography.pdf           # Example RAG source document
├── src/
│   └── aws_telegram_bot/
│       ├── application/
│       │   ├── conversation_service/
│       │   │   ├── generate_response.py
│       │   │   └── workflow/          # LangGraph state machine
│       │   │       ├── graph.py
│       │   │       ├── nodes.py
│       │   │       ├── edges.py
│       │   │       ├── state.py
│       │   │       └── tools.py
│       │   └── rag_indexing_service/
│       │       └── index_documents.py # PDF → chunks → embeddings → Qdrant
│       ├── domain/
│       │   └── prompts.py             # System/router prompts (+ Opik prompt versioning)
│       ├── infrastructure/
│       │   ├── clients/               # External service clients (OpenAI, Qdrant, MongoDB, ElevenLabs)
│       │   ├── telegram/
│       │   │   └── handlers.py        # Text/voice/photo handlers
│       │   ├── lambda_function.py     # AWS Lambda handler entrypoint
│       │   └── opik_utils.py          # Opik helper utilities
│       └── config.py                  # Settings loaded from env vars
└── tests/
    └── __init__.py
```

## Key files

- `src/aws_telegram_bot/infrastructure/lambda_function.py`: Lambda entrypoint and Telegram update processing.
- `src/aws_telegram_bot/infrastructure/telegram/handlers.py`: Telegram message handlers (text/voice/photo).
- `src/aws_telegram_bot/application/conversation_service/workflow/`: LangGraph nodes/edges/state.
- `src/aws_telegram_bot/application/rag_indexing_service/index_documents.py`: PDF → chunks → Qdrant indexing.
- `data/george_biography.pdf`: Example document used for RAG.
- `.github/workflows/deploy_aws_lambda.yaml`: CI/CD pipeline to ECR + Lambda.

## Configuration

Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

Required environment variables:

- `OPENAI_API_KEY`
- `ELEVENLABS_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `MONGODB_CONNECTION_STRING`
- `QDRANT_API_KEY`
- `QDRANT_URL`
- `COMET_API_KEY`

Optional (defaults in `src/aws_telegram_bot/config.py`):

- `OPENAI_MODEL` (default: `gpt-4o-mini`)
- `EMBEDDING_MODEL` (default: `text-embedding-3-large`)
- `COMET_PROJECT` (default: `telegram_agent_aws`)
- `OPIK_CONFIG_PATH` (default: `/tmp/.opik.config`)

## Local development

### Install dependencies

This project uses `uv` and includes a `uv.lock`.

```bash
uv sync --frozen
```

### Format / lint

```bash
make format-check
make lint-check
make format-fix
make lint-fix
```

### Index documents into Qdrant (RAG)

This reads `data/george_biography.pdf`, splits it into chunks, and uploads embeddings to Qdrant collection `aws_telegram_bot_collection`.

```bash
make index-qdrant
```

## Run locally (Lambda container)

Build the Lambda container image:

```bash
docker build -t telegram-agent-aws .
```

Run it locally with your `.env`:

```bash
docker run --env-file .env -p 9000:8080 telegram-agent-aws
```

Invoke the Lambda runtime (example event):

```bash
curl -sS \
  -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{
    "body": {
      "update_id": 1,
      "message": {
        "message_id": 1,
        "date": 0,
        "text": "Hello!",
        "from": { "id": 123, "is_bot": false, "first_name": "Test" },
        "chat": { "id": 123, "type": "private" }
      }
    }
  }'
```

Note: this project replies by calling the Telegram Bot API, so the `chat.id` and token must correspond to a real chat with your bot.

## Deploy to AWS

The workflow in `.github/workflows/deploy_aws_lambda.yaml` deploys on pushes to `main`:

1. Builds and pushes the Docker image to Amazon ECR (`telegram_bot_agent` in `us-east-1` by default).
2. Updates the Lambda function (`telegram-agent-lambda` by default) to the new image and sets env vars.

### Prerequisites

- An ECR repository matching the workflow’s `ECR_REPOSITORY` value.
- A Lambda function created with **package type: Image**.
- An API Gateway HTTP endpoint (or similar) that forwards Telegram webhook POSTs to the Lambda function.
- GitHub Actions secrets:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_LAMBDA_EXECUTION_ROLE`
  - `OPENAI_API_KEY`
  - `ELEVENLABS_API_KEY`
  - `TELEGRAM_BOT_TOKEN`
  - `MONGODB_CONNECTION_STRING`
  - `COMET_API_KEY`
  - `QDRANT_API_KEY`
  - `QDRANT_URL`

### Set the Telegram webhook

After you have a public HTTPS endpoint that routes to your Lambda handler, set the webhook:

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=<YOUR_WEBHOOK_URL>"
```

## Notes

- Lambda uses `/tmp` for temporary audio/image files (voice notes and photos).
- OpenAI and ElevenLabs usage may incur costs depending on your plan and traffic.

## License

MIT
