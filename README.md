TrustGuard
A Multi-Layered Runtime Verification Gateway for LLM Applications

TrustGuard is a runtime verification gateway designed to reduce hallucinations in Large Language Model (LLM) applications.

It checks model-generated claims against retrieved evidence, evaluates document freshness, and determines whether an answer should be allowed, flagged, blocked, or revised before presenting it as reliable.

Problem Statement

Large Language Models can generate confident answers that contain incorrect, unsupported, or outdated information.

In document-based applications, users often rely on AI-generated responses to understand policies, reports, and other important information. An inaccurate answer can lead to confusion, misinformation, and poor decisions.

Traditional prompting alone cannot guarantee that every generated claim is supported by the available evidence.

TrustGuard addresses this problem by introducing a verification layer between the LLM and the user.

## Solution

TrustGuard verifies AI-generated answers against relevant evidence retrieved from uploaded documents.

Instead of directly presenting the model's response as reliable, TrustGuard:

- Retrieves relevant passages from uploaded documents.
- Generates an answer using the configured Meta model.
- Extracts individual claims from the answer.
- Verifies claims against retrieved evidence.
- Identifies potentially outdated or unknown document freshness.
- Determines an appropriate runtime decision.
- Revises unreliable answers when possible and verifies them again.

 Key Features

 Document-Based Retrieval

Upload PDF, TXT, and Markdown documents and use them as evidence for answering questions.

### Claim-Level Verification

Extracts individual claims from generated answers and checks them against retrieved passages.

### Evidence Verdicts

Each claim is classified as:

- `SUPPORTED`
- `CONTRADICTED`
- `UNVERIFIED`

 Runtime Decision System

TrustGuard determines whether an answer should be:

- `ALLOW` — Claims are supported by available evidence and configured checks.
- `FLAG` — The answer requires additional review.
- `BLOCK` — The original answer should not be presented as reliable.
- `REVISE` — The answer is revised using available evidence and checked again.

 Document Freshness Assessment

Evaluates document dates and identifies potentially outdated or unknown freshness.

 Answer Revision

Can revise an unreliable answer using retrieved evidence and verify the revised response again.

 Demo Scenarios

Includes example workflows to demonstrate supported answers, outdated evidence, contradicted claims, unsupported claims, and missing evidence.

 System Workflow

```text
User Question
     |
     v
Document Retrieval
     |
     v
LLM Answer Generation
     |
     v
Claim Extraction
     |
     v
Evidence Verification
     |
     v
Document Freshness Assessment
     |
     v
Runtime Decision
     |
     +-- ALLOW
     +-- FLAG
     +-- BLOCK
     +-- REVISE
             |
             v
      Re-Verification
```

 Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application logic |
| Streamlit | Interactive web interface |
| Meta Model API | LLM answer generation |
| Document Processing | PDF, TXT, and Markdown handling |
| Retrieval | Evidence selection from documents |
| Claim Verification | Claim-level evidence checking |

 Project Structure

```text
TrustGuard/
|
├── app.py
├── config/
├── core/
├── sample_docs/
├── tests/
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

Getting Started

 Prerequisites

- Python installed on your computer
- Git
- A valid API key with access to the configured Meta model API

 1. Clone the Repository

```bash
git clone https://github.com/Jaithra-dev/TrustGuard-LLM-Verification.git
```

Navigate to the project directory:

```bash
cd TrustGuard-LLM-Verification
```

 2. Create a Virtual Environment

On Windows:

```bash
python -m venv .venv
```

Activate it:

```bash
.venv\Scripts\activate
```

On macOS/Linux:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

 3. Install Dependencies

```bash
pip install -r requirements.txt
```

 4. Configure Environment Variables

Create your own `.env` file by copying `.env.example`.

On Windows:

```powershell
Copy-Item .env.example .env
```

On macOS/Linux:

```bash
cp .env.example .env
```

Open the `.env` file and enter your own API key and configuration.

```env
MODEL_API_KEY=your_api_key_here
MODEL_API_BASE_URL=https://api.meta.ai/v1
MODEL_NAME=muse-spark-1.3
```

Replace `your_api_key` with your own valid API key.

Do not commit or share your `.env` file.

5. Run TrustGuard

```bash
streamlit run app.py
```

Open the local URL displayed in your terminal, usually:

```text
http://localhost:8501
```

 Demo Scenarios

TrustGuard includes demonstration scenarios for:

| Scenario | Expected Behavior |
|---|---|
| Refund policy question | Supported answer |
| Shipping duration question | Flag potentially outdated evidence |
| Warranty question | Supported answer with unknown freshness |
| Unsupported shipping destination | Unverified claim |
| Question without relevant evidence | No answer presented as verified |
| Deliberately incorrect answer | Contradicted claim and block |
| Answer revision | Corrected answer verified against evidence |
| Verification disabled | Plain model answer without verification |
| User-uploaded document | Retrieve and answer from uploaded evidence |

Security

TrustGuard uses environment variables to configure API credentials.

- API keys are stored in a local `.env` file.
- `.env` is excluded from version control.
- `.env.example` provides a configuration template.
- Each user must configure their own API credentials.
- Never publish API keys in source code, screenshots, or public repositories.

 Limitations

TrustGuard does not guarantee that every generated answer is correct.

Verification quality depends on:

- The completeness and quality of the uploaded documents.
- Retrieval relevance.
- Claim extraction and verification performance.
- Source document freshness.
- The configured model API and its response.

An `ALLOW` decision indicates that the answer passed the configured verification checks against available evidence. It does not guarantee universal factual correctness.

Future Improvements

- Improved retrieval and chunking for long documents.
- More advanced multi-document evidence verification.
- Expanded automated evaluation datasets.
- Additional verification metrics.
- Better handling of ambiguous and complex claims.
- Support for additional model providers. Project Objective

TrustGuard demonstrates how runtime verification can improve the reliability of LLM applications by grounding generated claims in retrieved evidence and identifying potentially unreliable answers before users depend on them.

Developer
Jaithra TM

Student Project | AI | LLM Reliability | Runtime Verification

License

This project is developed for educational and demonstration purposes.
