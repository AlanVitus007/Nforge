# NForge

NForge is an AI-powered academic research assistant for organizing
research papers, understanding individual papers, comparing multiple
papers, identifying research gaps, discovering cross-paper themes, and
analyzing research trends.

## Features

### Paper Management

-   Create and manage research projects.
-   Upload and manage research papers.
-   Rename projects and papers.
-   Process uploaded PDFs into searchable content.

### AI-Powered Research

#### Single-Paper Q&A

Ask questions about an individual paper and receive an answer supported
by retrieved paper evidence.

#### Compare Papers

Compare 2--4 papers for: - Overall synthesis - Similarities -
Differences - Methodology - Findings - Research gaps - Supporting
evidence

#### Research Gap Analysis

Analyze 2--4 papers for: - Overall assessment - Common limitations -
Methodological gaps - Dataset/population gaps - Understudied areas -
Contradictions and inconsistencies - Unanswered research questions -
Future research directions

#### Cross-Paper Thematic Analysis

Identify meaningful themes and recurring concepts across 2--4 papers,
including paper-specific discussions, cross-paper observations, and
supporting evidence.

#### Research Trend Analysis

Analyze research evolution across 2--4 papers, including: - Overall
research trends - Research evolution - Emerging directions - Methodology
evolution - Future research directions

Trend analysis should not claim chronological evolution unless the
available paper metadata or content supports it.

## Research Workspace

The Research Workspace provides a persistent environment for research
sessions.

A session can contain: - Selected research papers - User questions - AI
responses - Structured comparison results - Research gap analyses -
Thematic analyses - Research trend analyses - Evidence and page
references

Sessions can be created, renamed, opened, switched, and deleted.
Previous research can be restored after refreshing the application.

## Architecture

``` text
NForge
├── Frontend
│   ├── React
│   ├── Vite
│   └── Research Workspace UI
└── Backend
    ├── Django
    ├── Django REST Framework
    ├── PDF processing
    ├── Semantic retrieval
    ├── SentenceTransformer embeddings
    └── Gemini AI generation
```

### AI Retrieval Pipeline

``` text
Research Paper
      ↓
PDF Extraction
      ↓
Page-Aware Chunks
      ↓
SentenceTransformer Embeddings
      ↓
Semantic Retrieval
      ↓
Relevant Paper Evidence
      ↓
Gemini
      ↓
Structured Research Response
      ↓
Evidence / Page References
```

NForge uses the `all-MiniLM-L6-v2` SentenceTransformer model for
semantic embeddings.

## Technology Stack

### Frontend

-   React
-   Vite
-   JavaScript
-   CSS

### Backend

-   Python
-   Django
-   Django REST Framework

### AI

-   Google Gemini API
-   SentenceTransformers
-   `all-MiniLM-L6-v2`

### Database

Django ORM is used for persistence.

Important research models include: - `ResearchSession` -
`ResearchMessage` - `ResearchEvidence` - `Paper` - `PaperChunk`

## Project Structure

``` text
NForge/
├── backend/
│   ├── ai/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests.py
│   ├── manage.py
│   └── ...
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── ...
│   ├── package.json
│   └── ...
└── README.md
```

## Requirements

Install: - Python 3.x - Node.js and npm - Git - A Gemini API key

Exact dependency versions are defined by the backend dependency files
and `frontend/package.json`.

## Backend Setup

``` powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The backend normally runs at:

``` text
http://127.0.0.1:8000/
```

## Frontend Setup

Open another terminal:

``` bash
cd frontend
npm install
npm run dev
```

Open the URL shown by Vite.

For a production build:

``` bash
npm run build
```

## Environment Variables

Keep API keys and secrets outside source control.

Configure the Gemini API key and other environment-specific settings
according to the backend configuration.

Never commit: - API keys - Passwords - Django secret keys - Private
credentials - Production environment files containing secrets

## Development Workflow

Use two terminals:

``` text
Terminal 1 → Django backend
Terminal 2 → Vite frontend
```

Typical workflow:

``` text
Start NForge
    ↓
Create / open project
    ↓
Upload research papers
    ↓
Process papers
    ↓
Open Research Workspace
    ↓
Ask / Compare / Gaps / Themes / Trends
```

## AI API Endpoints

AI endpoints are under `/api/ai/`.

``` http
POST /api/ai/ask/
POST /api/ai/compare/
POST /api/ai/gap-analysis/
POST /api/ai/thematic-analysis/
POST /api/ai/research-trends/
```

Research session endpoints:

``` http
POST   /api/ai/sessions/
GET    /api/ai/sessions/
GET    /api/ai/sessions/<session_id>/
PATCH  /api/ai/sessions/<session_id>/
DELETE /api/ai/sessions/<session_id>/
```

Cross-paper analysis features generally support 2--4 papers.

## Persistent AI Research

When an AI analysis receives a `session_id`, the research activity can
be persisted:

``` text
User Question
     ↓
ResearchMessage (USER)
     ↓
AI Analysis
     ↓
ResearchMessage (ASSISTANT)
     ↓
ResearchEvidence
```

Persistence uses database transactions so failed synthesis does not
leave incomplete research records.

Standalone requests without a session do not create research history.

## Evidence Grounding

Evidence can contain: - Paper ID - Paper title - Chunk ID - Page
number - Extracted evidence text

The Research Workspace displays evidence and can navigate to the
relevant paper location.

Invalid or fabricated source references are filtered using backend
source validation.

## Testing

### Backend

``` powershell
python manage.py test ai
python manage.py check
```

### Frontend

``` bash
npm run lint
npm run build
```

## Current Verification Status

The Research Trend Analysis feature (Backend Service, REST API, and Research Workspace Frontend Integration) is complete and verified:

``` text
Research Trend API tests: 20/20 passed
Service + API tests:     40/40 passed
Full AI test suite:      177/177 passed
Django system check:      0 issues
Frontend build:          npm run build succeeded
Frontend linter:         npm run lint passed (0 errors)
```

## Common Troubleshooting

### Backend does not start

Check Python:

``` powershell
python --version
```

Activate the environment:

``` powershell
venv\Scripts\activate
```

Install dependencies:

``` powershell
pip install -r requirements.txt
```

Then:

``` powershell
python manage.py check
```

### Database or migration errors

``` powershell
python manage.py makemigrations
python manage.py migrate
python manage.py check
```

### Frontend cannot connect to backend

Check that: 1. Django is running. 2. The frontend API configuration
points to the correct backend URL. 3. The backend port is accessible. 4.
Required CORS/configuration settings are correct.

### AI analysis fails

Check: - Gemini API configuration - API quota/availability - Backend
logs - Whether enough papers were selected - Whether the selected papers
contain processed/retrievable content

### Cross-paper analysis cannot start

``` text
Minimum: 2 papers
Maximum: 4 papers
```

## Security

Never commit secrets to Git.

The backend performs authentication and ownership validation for
research resources.

AI-generated information should be verified against the cited paper
evidence before academic use.

## Git Workflow

Review changes before committing:

``` bash
git status
git diff
```

When a meaningful batch is complete:

``` bash
git add .
git commit -m "Describe the completed change"
git push origin zoro
```

Do not commit secrets, local environments, generated databases, or
unnecessary build artifacts.

## Roadmap

### Completed

-   Project and paper management
-   PDF processing
-   Semantic retrieval
-   Single-paper AI Q&A
-   Multi-paper comparison
-   Persistent Research Workspace
-   Research session management
-   Research Gap Analysis
-   Cross-Paper Thematic Analysis
-   Research Trend Analysis backend and API
-   Research Trend Analysis Workspace integration (Phase 7.3.3)

### In Progress / Planned

-   Citation and Evidence Intelligence
-   Production hardening
-   Performance improvements
-   Deployment
-   Final documentation and release testing

## Academic Use

NForge is intended to assist academic research workflows.

AI-generated responses should be checked against the original research
papers. Evidence references make verification easier, but users remain
responsible for validating interpretations, citations, and conclusions
before academic submission or publication.

## License

Add the project's intended license here before public release.
