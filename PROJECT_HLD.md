# PI-EWS Architecture and Methodology

PI-EWS is a prompt-injection early warning system with an interactive honeypot chat, adaptive risk-based defenses, and admin/analyst investigation tools. The diagrams below summarize the deployed application architecture and the live and offline analysis methodologies.

## Application Architecture

<!-- mermaid-checked: no \n, no em-dash/en-dash, no {} in labels, subgraphs are id["label"], arrows are -->|"label"|, all subgraphs closed by end, ids unique -->
```mermaid
flowchart TD
    subgraph Client["Client layer"]
        aBrowser["Web browser"]
        aApp["React single page app"]
        aAuthState["Auth context and route guards"]
        aApiClient["Axios API client"]
    end
    subgraph Backend["Backend layer - FastAPI"]
        aRoutes["REST routers"]
        aAuth["Authentication and role checks"]
        aChat["Chat orchestration"]
        aDetect["Rule and heuristic detector"]
        aRisk["Cumulative risk assessment"]
        aDefense["Adaptive defense policy"]
        aReports["Analyst report service"]
    end
    subgraph Data["Data layer"]
        aMongo[("MongoDB via Motor and Beanie")]
    end
    subgraph Services["External services"]
        aLLM["Groq compatible LLM endpoint"]
        aGoogle["Google ID token verification"]
        aSMTP["SMTP email server"]
    end
    subgraph Evaluation["Offline evaluation"]
        aDataset["Labeled JSONL dataset"]
        aExperiments["Scikit-learn experiments"]
        aResults["JSON experiment results"]
    end

    aBrowser -->|"uses"| aApp
    aApp -->|"session state"| aAuthState
    aApp -->|"calls API"| aApiClient
    aApiClient -->|"REST and bearer token"| aRoutes
    aRoutes -->|"validates identity and role"| aAuth
    aAuth -->|"reads account"| aMongo
    aAuth -->|"verifies Google credential"| aGoogle
    aRoutes -->|"chat request"| aChat
    aChat -->|"analyzes message and history"| aDetect
    aDetect -->|"signals and suspicion"| aRisk
    aRisk -->|"score and recommendation"| aDefense
    aDefense -->|"non-block response"| aLLM
    aChat -->|"saves messages, risk, and events"| aMongo
    aRoutes -->|"reads accounts and investigations"| aMongo
    aReports -->|"loads report data"| aMongo
    aReports -->|"sends PDF and CSV"| aSMTP
    aDataset -->|"training and test samples"| aExperiments
    aExperiments -->|"writes metrics"| aResults
```

### Technology Stack Summary

| Layer | Technology | Version declared | Purpose |
|---|---|---|---|
| Frontend | React, React DOM | `^19.3.1` | User, admin, and analyst interface |
| Frontend | React Router | `^7.18.6` | Client-side navigation and route guards |
| Frontend | Vite | `^8.3.6` | Development server and production build |
| Frontend | Axios | `^1.21.1` | REST requests and bearer-token attachment |
| Frontend | Tailwind CSS, Chart.js, Lucide React | Tailwind `^4.3.5`; Chart.js `^4.6.1` | Styling, dashboard charts, and icons |
| API | FastAPI, Uvicorn, Pydantic | Unpinned in requirements | REST API, validation, and ASGI serving |
| Persistence | MongoDB, Motor, Beanie | Motor `3.7.1`; Beanie `1.29.0` | Async document persistence |
| Authentication | python-jose, Passlib/bcrypt, Google Auth | Google Auth `>=2.28,<3` | JWTs, password hashing, and Google sign-in |
| Live analysis | Python regex and heuristic engines | Application code | Prompt-injection signals and risk-based policy |
| Offline evaluation | scikit-learn | `>=1.5,<2` | TF-IDF and logistic-regression experiment |
| Integrations | httpx, Google Identity, SMTP | httpx unpinned | LLM calls, identity verification, and report delivery |
| Reporting | ReportLab and Python CSV/email libraries | ReportLab `>=4.2,<5` | Analyst PDF and CSV reports |

### Data Storage and External Services

MongoDB stores users, conversations, and security events. Beanie models documents and Motor provides asynchronous database access; conversation messages and risk snapshots are embedded in conversation documents. The backend can call a Groq-hosted OpenAI-compatible chat-completions endpoint, verify Google ID tokens, and deliver analyst reports through SMTP. These integrations require environment configuration; the LLM service uses a canned mock responder when no usable LLM key is configured. The labeled dataset and experiment JSON results are local files, not live application collections.

### Key Architectural Decisions

- The FastAPI backend is the source of truth for identity, authorization, conversation ownership, risk decisions, and persisted analysis.
- The live chat pipeline uses rule and heuristic detection followed by cumulative EWMA risk scoring; the scikit-learn classifier is isolated to offline evaluation.
- Defense policy runs before response generation, so a block decision returns an override without calling the LLM.

## Component Relationships

<!-- mermaid-checked: no \n, no em-dash/en-dash, no {} in labels, subgraphs are id["label"], arrows are -->|"label"|, all subgraphs closed by end, ids unique -->
```mermaid
flowchart LR
    subgraph Presentation["Presentation"]
        cPages["React pages"]
        cAuthContext["Auth context"]
        cApi["Axios API service"]
    end
    subgraph Routes["FastAPI routes"]
        cAuthRoutes["Auth routes"]
        cChatRoute["Chat route"]
        cConversationRoutes["Conversation routes"]
        cAdminRoutes["Admin routes"]
        cAnalystRoutes["Analyst routes"]
        cRoleRoutes["Account management routes"]
    end
    subgraph cBackendServices["Backend services and engines"]
        cAuthService["Auth service"]
        cConversationManager["Conversation manager"]
        cDetection["Detection engine"]
        cRisk["Risk engine"]
        cDefense["Defense engine"]
        cLLM["LLM service"]
        cReport["Report service"]
    end
    subgraph Persistence["Persistence"]
        cModels["Beanie document models"]
        cMongo[("MongoDB")]
    end

    cPages -->|"reads session and role"| cAuthContext
    cPages -->|"makes requests"| cApi
    cApi -->|"HTTP requests"| cAuthRoutes
    cApi -->|"HTTP requests"| cChatRoute
    cApi -->|"HTTP requests"| cConversationRoutes
    cApi -->|"HTTP requests"| cAdminRoutes
    cApi -->|"HTTP requests"| cAnalystRoutes
    cApi -->|"HTTP requests"| cRoleRoutes
    cAuthRoutes -->|"authenticates"| cAuthService
    cChatRoute -->|"loads and saves"| cConversationManager
    cChatRoute -->|"analyzes"| cDetection
    cChatRoute -->|"scores"| cRisk
    cChatRoute -->|"chooses policy"| cDefense
    cChatRoute -->|"generates non-block reply"| cLLM
    cConversationRoutes -->|"checks owner and updates history"| cModels
    cConversationManager -->|"persists conversation state"| cModels
    cAdminRoutes -->|"queries investigation data"| cModels
    cAnalystRoutes -->|"reuses read-only investigation routes"| cAdminRoutes
    cAnalystRoutes -->|"builds and emails reports"| cReport
    cRoleRoutes -->|"manages accounts"| cModels
    cAuthService -->|"loads user"| cModels
    cModels -->|"ODM operations"| cMongo
```

### Component Inventory

| Component | Layer | Type | Responsibility |
|---|---|---|---|
| React pages | Presentation | Pages/components | Login, chat, conversation, admin, and analyst screens |
| Auth context | Presentation | Context/provider | Holds the signed-in user and coordinates login state |
| Axios API service | Presentation | HTTP client | Calls API endpoints and attaches the JWT |
| Auth routes | API | Router | Registration, local login, Google login, and profile |
| Chat route | API/orchestration | Router | Coordinates detection, risk, defense, response, and persistence |
| Conversation routes | API | Router | Lists, reads, and hides the signed-in user's conversations |
| Admin routes | API | Router | Admin dashboard, analytics, events, and conversation investigation |
| Analyst routes | API | Router | Read-only investigation and report requests |
| Account management routes | API | Router | Admin-only account, role, and activation management |
| Auth service | Services | Authentication service | Password verification, JWTs, and role dependencies |
| Conversation manager | Services | Domain service | Creates sessions, appends messages, and updates risk snapshots |
| Detection engine | Analysis | Domain engine | Produces rule/heuristic injection signals |
| Risk engine | Analysis | Domain engine | Updates cumulative risk and maps it to a level/recommendation |
| Defense engine | Analysis | Domain engine | Selects allow, monitor, restrict, or block behavior |
| LLM service | Integration | External-service adapter | Calls configured LLM or supplies the mock response |
| Report service | Integration | Reporting service | Builds PDF/CSV attachments and sends SMTP email |
| Beanie document models | Data access | ODM models | Defines users, conversations, embedded messages, and events |
| MongoDB | Data | Document database | Persists application accounts and investigation records |

## Methodology

### Live Chat Analysis and Response

<!-- mermaid-checked: no \n, no em-dash/en-dash, no {} in labels, subgraphs are id["label"], arrows are -->|"label"|, all subgraphs closed by end, ids unique -->
```mermaid
flowchart TD
    mStart["User submits chat message"]
    mValidate["Validate request and bearer token"]
    mLoad["Load or create owned conversation"]
    mSignals["Extract detector signals"]
    mAggregate["Combine signals with escalation"]
    mRisk["Update cumulative EWMA risk score"]
    mLevel["Classify low, medium, high, or critical"]
    mPolicy["Select allow, monitor, restrict, or block"]
    mOverride["Use fixed block response"]
    mPrompt["Add reinforcement for monitor or restrict"]
    mLLM["Call configured LLM or mock responder"]
    mSave["Save user message, assistant reply, and risk snapshot"]
    mEvent["Save security event for suspicious activity"]
    mReturn["Return response, risk, action, and explanation"]

    mStart -->|"request"| mValidate
    mValidate -->|"authorized and valid"| mLoad
    mLoad -->|"conversation context"| mSignals
    mSignals -->|"detection result"| mAggregate
    mAggregate -->|"suspicion score"| mRisk
    mRisk -->|"updated score"| mLevel
    mLevel -->|"risk level"| mPolicy
    mPolicy -->|"block"| mOverride
    mPolicy -->|"allow, monitor, or restrict"| mPrompt
    mPrompt -->|"non-block request"| mLLM
    mOverride -->|"response"| mSave
    mLLM -->|"generated response"| mSave
    mSave -->|"if suspicious"| mEvent
    mSave -->|"otherwise or after event"| mReturn
    mEvent -->|"completed"| mReturn
```

The detector combines pattern matches, manipulation/override checks, context and encoding checks, phrase similarity, message anomaly scoring, and prior-turn escalation. Its signals are combined into an overall suspicion score; a turn is marked suspicious at `0.35` or higher. The risk engine updates the conversation score with an EWMA (`alpha=0.3`) for suspicious input and applies a gradual `0.05` decay for benign input. Risk bands are low below `0.3`, medium from `0.3`, high from `0.6`, and critical from `0.8`. The defense policy maps these levels to allow, monitor, restrict, and block; the response and risk metadata are persisted, with a security event recorded for suspicious turns.

### Offline Detector Evaluation

<!-- mermaid-checked: no \n, no em-dash/en-dash, no {} in labels, subgraphs are id["label"], arrows are -->|"label"|, all subgraphs closed by end, ids unique -->
```mermaid
flowchart TD
    eDataset["Labeled prompt-injection JSONL"]
    eValidate["Validate labels and sample records"]
    eSplit["Create stratified cross-validation folds"]
    eTrain["Fit TF-IDF and logistic regression"]
    eBaseline["Run existing rule and heuristic detector"]
    eClassifier["Run detection-only classifier"]
    eCompare["Compare held-out predictions"]
    eMetrics["Calculate classification and latency metrics"]
    eOutcomes["Optionally load human-adjudicated injection outcomes"]
    eReport["Write experiment JSON with protocol and dataset hash"]

    eDataset -->|"samples"| eValidate
    eValidate -->|"valid samples"| eSplit
    eSplit -->|"training folds"| eTrain
    eSplit -->|"held-out samples"| eBaseline
    eSplit -->|"held-out samples"| eClassifier
    eTrain -->|"fitted model"| eClassifier
    eBaseline -->|"baseline predictions"| eCompare
    eClassifier -->|"classifier predictions"| eCompare
    eCompare -->|"predictions and labels"| eMetrics
    eOutcomes -->|"optional observed outcomes"| eMetrics
    eMetrics -->|"evaluation results"| eReport
```

The experiment script defaults to five stratified folds and a fixed seed of `42`. It compares the rule/heuristic baseline against the TF-IDF plus balanced logistic-regression detector on held-out, single-turn samples with empty conversation history; it does not call the LLM or apply defenses. Actual injection-success rate is reported only when human-adjudicated outcomes are provided; otherwise it is unavailable, and detector false negatives are reported as pass-through rate.

### Methodology Tools

| Activity | Tools |
|---|---|
| Web interaction | React, React Router, Axios, Vite |
| API and validation | FastAPI, Pydantic |
| Authentication | JWT, Passlib/bcrypt, Google Auth |
| Persistence | MongoDB, Motor, Beanie |
| Live prompt analysis | Python regular expressions and custom detection, risk, and defense engines |
| LLM response | httpx with configured OpenAI-compatible endpoint or mock service |
| Offline evaluation | scikit-learn, TF-IDF, logistic regression, stratified cross-validation |
| Reporting | ReportLab, Python CSV/email libraries, SMTP |
