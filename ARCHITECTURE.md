# GrantOps: Architecture & Design Philosophy

## Part I: Philosophical Foundations

### 1.1 The Core Insight: Grant Writing as Software Development

The traditional approach to grant writing treats documents as monolithic artifacts—Word files passed between collaborators, versioned with filenames like `proposal_v3_final_FINAL.docx`. This model inherits all the pathologies of pre-version-control software development: merge conflicts resolved by shouting, lost work, unclear attribution, and the impossibility of understanding *why* something changed.

**GrantOps inverts this model.** We treat grant applications as:

- **Code:** Structured, modular, testable units of text
- **State:** Declarative configurations describing what each section requires
- **Pipelines:** Composable operations (draft, evaluate, revise) that transform state

This isn't a metaphor—it's a literal implementation. Git *is* the database. GitHub *is* the UI. Actions *are* the runtime.

### 1.2 The Principle of Minimal Indirection

> "Every layer of abstraction is a debt that must be repaid with debugging."

Many AI-powered writing tools hide complexity behind polished interfaces. This creates fragility: when the magic fails, users have no recourse. GrantOps takes the opposite approach:

- **Transparency over Magic:** Every decision the system makes is visible in plain text files
- **Editability over Automation:** The system *proposes*, the human *disposes*
- **Unix Philosophy:** Small, composable tools that do one thing well

A user should be able to understand exactly what context an LLM receives by reading the files in their repo. No hidden prompts. No opaque embeddings. No mystery.

### 1.3 The Flexibility Mandate

Grant applications vary wildly:
- Different funders have different evaluation criteria
- Different projects require different narrative structures
- Different teams have different review processes

Rather than building configuration for every possibility, we embrace the **file system as schema**. Want to add a new evaluation dimension? Create a new prompt file. Want to change the model for drafting? Edit one line in YAML. Want to restructure how context is assembled? The logic is in plain Python, not buried in a framework.

### 1.4 Why GitHub-Native?

GitHub provides three things for free that would cost weeks to build:

1. **Diff Visualization:** See exactly what changed between drafts, with line-level granularity
2. **Branch-Based Workflows:** Experiment with alternative versions without fear
3. **Collaboration Infrastructure:** Comments, reviews, and approvals are built-in

By treating GitHub as our application layer, we avoid:
- Building authentication
- Building a database
- Building a UI
- Building collaboration features

**The absence of custom infrastructure is a feature, not a limitation.**

---

## Part II: Architectural Decisions

### 2.1 Design Principles (Ranked by Priority)

1. **Simplicity over Completeness:** We build what's needed, not what's possible
2. **Transparency over Convenience:** Users can always see what's happening
3. **Flexibility over Optimization:** Easy to modify beats slightly faster
4. **Convention over Configuration:** Sensible defaults, escape hatches available

### 2.2 The Repository as Database

The file system is not merely storage—it's the semantic structure of the application:

```
.
├── .github/workflows/          # "Functions" - triggered operations
├── config/
│   ├── agents.yaml             # Model/provider configuration
│   └── prompts/                # Reusable system prompts
│       ├── drafter.md
│       ├── evaluator_style.md
│       ├── evaluator_logic.md
│       └── parser.md
├── context/                    # Shared knowledge base
│   ├── project.md              # Core project logic and goals
│   ├── organization.md         # Boilerplate org info
│   └── style.md                # Voice and tone guidelines
├── application/                # The actual grant content
│   ├── source/                 # Original RFP/guidelines
│   └── sections/               # Generated per-question structure
│       └── {section_id}/
│           ├── meta.yaml       # Requirements, word limits, criteria
│           ├── outline.md      # Editable structure template
│           └── draft.md        # Current answer (versioned)
└── scripts/                    # Python implementation
    ├── core/                   # Shared utilities
    │   ├── context.py          # Context assembly logic
    │   ├── llm.py              # Model abstraction layer
    │   └── git_ops.py          # Git operations helper
    ├── parse.py                # RFP parsing
    ├── draft.py                # Answer generation
    └── evaluate.py             # Evaluation modes
```

**Key insight:** This structure is *self-documenting*. A new team member can understand the system by browsing directories.

### 2.3 The LLM Abstraction Layer

Rather than coupling to a specific provider, we use a thin abstraction:

```python
# scripts/core/llm.py (conceptual)
def call_llm(agent_name: str, prompt: str) -> str:
    config = load_yaml("config/agents.yaml")
    agent = config["agents"][agent_name]

    # litellm handles the provider routing
    return litellm.completion(
        model=agent["model"],
        messages=[{"role": "user", "content": prompt}],
        temperature=agent.get("temperature", 0.7)
    )
```

This enables:
- Switching models by editing one YAML field
- A/B testing different providers
- Fallback configurations
- Cost optimization per task

### 2.4 Context Assembly (The Critical Path)

The most important design decision is how we build LLM prompts. We use **explicit, file-based context assembly**:

```python
def build_drafting_context(section_id: str) -> str:
    parts = [
        read_file("config/prompts/drafter.md"),
        read_file("context/project.md"),
        read_file("context/style.md"),
        read_file(f"application/sections/{section_id}/meta.yaml"),
        read_file(f"application/sections/{section_id}/outline.md"),
    ]
    return "\n\n---\n\n".join(parts)
```

**Why this matters:**
- Context is *visible*: users can inspect exactly what the LLM sees
- Context is *editable*: modify any file to change behavior
- Context is *versioned*: git tracks every change to every context file
- Context is *isolated*: section A's content doesn't leak into section B (unless deliberately included)

### 2.5 Workflow Design Philosophy

Each GitHub Action workflow follows a pattern:

1. **Receive** explicit inputs (which section, which mode)
2. **Assemble** context from files
3. **Execute** a single LLM call (or minimal chain)
4. **Output** results to files or PR comments
5. **Commit** any file changes to a branch

**Anti-pattern avoided:** Complex multi-step agentic loops. These are:
- Hard to debug
- Expensive (many API calls)
- Unpredictable (cascading errors)

Instead, each workflow does *one thing*. Composition happens at the human level: run Parse, then run Draft, then run Evaluate.

---

## Part III: Implementation Strategy

### 3.1 Phased Approach

We build in layers, with each layer providing immediate value:

| Phase | Deliverable | Value Unlocked |
|-------|-------------|----------------|
| 0 | Repository structure + config schema | Teams can manually organize content |
| 1 | Context loader utility | Standardized prompt assembly |
| 2 | Draft workflow | Automated first-draft generation |
| 3 | Evaluate workflow | Automated feedback on drafts |
| 4 | Parse workflow | Automated RFP analysis |

**Note:** Phase 4 (parsing) comes last because:
- It's the most complex (PDF extraction, structure inference)
- Users can manually create section structure in the meantime
- The value of drafting/evaluation doesn't depend on parsing

### 3.2 Complexity Reduction Decisions

Several simplifications from the original brief:

| Original Idea | Simplified Approach | Rationale |
|---------------|---------------------|-----------|
| Multiple evaluation agents | Single evaluator with mode parameter | One script, one prompt template per mode |
| Auto-commit style fixes | Post fixes as PR comment (diff format) | User reviews before any file changes |
| PDF parsing | Start with markdown/text paste | PDF libraries are fragile; manual paste works |
| LangChain | Direct litellm calls | LangChain adds complexity without benefit here |
| Dropdown inputs | Simple text inputs with validation | Fewer moving parts |

### 3.3 Configuration Schema

**`config/agents.yaml`:**
```yaml
# Model configuration - maps task names to model settings
agents:
  parser:
    model: "gpt-4o"
    temperature: 0.1
    description: "Extracts structure from RFP documents"

  drafter:
    model: "claude-sonnet-4-20250514"
    temperature: 0.7
    description: "Generates section drafts"

  evaluator:
    model: "gpt-4o"
    temperature: 0.3
    description: "Provides feedback on drafts"

# Default settings (can be overridden per-agent)
defaults:
  max_tokens: 4096
  timeout: 120
```

**`application/sections/{id}/meta.yaml`:**
```yaml
title: "Project Narrative"
source_reference: "Section 4.1 of RFP"
word_limit: 2000
scoring_weight: 30  # percent of total score

requirements:
  - "Describe the problem being addressed"
  - "Explain the proposed solution"
  - "Provide evidence of feasibility"

evaluation_criteria:
  - criterion: "Clear problem statement"
    weight: 25
  - criterion: "Innovative approach"
    weight: 25
  - criterion: "Realistic timeline"
    weight: 25
  - criterion: "Measurable outcomes"
    weight: 25
```

### 3.4 Prompt Architecture

Prompts live in `config/prompts/` as markdown files. This enables:
- Version control of prompt engineering
- Easy A/B testing
- Clear separation of concerns

**Example: `config/prompts/drafter.md`:**
```markdown
You are an expert grant writer. Your task is to draft a section of a grant application.

## Instructions
1. Follow the provided outline structure exactly
2. Match the tone defined in the style guide
3. Stay within the word limit specified in the metadata
4. Address every requirement listed in the metadata
5. Be specific and evidence-based; avoid vague claims

## Output Format
Produce only the section content in markdown format. Do not include meta-commentary.
```

### 3.5 Workflow Implementation Pattern

All workflows follow this skeleton:

```yaml
name: Draft Section
on:
  workflow_dispatch:
    inputs:
      section_id:
        description: 'Section to draft (e.g., "narrative", "budget_justification")'
        required: true
        type: string
      branch_name:
        description: 'Branch for the draft (leave empty for auto-generated)'
        required: false
        type: string

jobs:
  draft:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run draft script
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python scripts/draft.py "${{ inputs.section_id }}"

      - name: Commit and create PR
        # ... git operations ...
```

---

## Part IV: Action Plan

### Phase 0: Foundation (Immediate)

**Goal:** Establish repository structure and configuration schema.

- [ ] Create directory structure as specified above
- [ ] Create `config/agents.yaml` with placeholder configuration
- [ ] Create example prompt files in `config/prompts/`
- [ ] Create example context files in `context/`
- [ ] Create `requirements.txt` with minimal dependencies
- [ ] Update README with usage instructions

**Deliverable:** A repository that users can clone and immediately start populating with their project context.

### Phase 1: Core Utilities

**Goal:** Build the shared Python infrastructure.

- [ ] `scripts/core/llm.py` - Model abstraction layer using litellm
- [ ] `scripts/core/context.py` - Context assembly utilities
- [ ] `scripts/core/git_ops.py` - Git operations helper (branching, committing)
- [ ] Unit tests for core utilities

**Deliverable:** Tested Python modules that other scripts can import.

### Phase 2: Draft Workflow

**Goal:** Enable automated first-draft generation.

- [ ] `scripts/draft.py` - Main drafting script
- [ ] `.github/workflows/draft.yml` - GitHub Action workflow
- [ ] `config/prompts/drafter.md` - Drafting system prompt
- [ ] Documentation: How to use the draft workflow

**Deliverable:** Users can trigger draft generation from GitHub Actions UI.

### Phase 3: Evaluate Workflow

**Goal:** Enable automated draft evaluation.

- [ ] `scripts/evaluate.py` - Evaluation script with mode routing
- [ ] `.github/workflows/evaluate.yml` - GitHub Action workflow
- [ ] `config/prompts/evaluator_style.md` - Style evaluation prompt
- [ ] `config/prompts/evaluator_logic.md` - Logic evaluation prompt
- [ ] `config/prompts/evaluator_alignment.md` - Project alignment prompt
- [ ] Documentation: Evaluation modes explained

**Deliverable:** Users can get automated feedback on any draft.

### Phase 4: Parse Workflow (Optional/Future)

**Goal:** Automate RFP structure extraction.

- [ ] `scripts/parse.py` - RFP parsing script
- [ ] `.github/workflows/parse.yml` - GitHub Action workflow
- [ ] `config/prompts/parser.md` - Parsing system prompt
- [ ] Handling for markdown/text input (defer PDF support)

**Deliverable:** Users can auto-generate section structure from RFP text.

---

## Part V: Flexibility & Extension Points

### 5.1 Adding New Evaluation Dimensions

1. Create `config/prompts/evaluator_{dimension}.md`
2. Add the dimension to the workflow's input options
3. (Optional) Update `scripts/evaluate.py` if special context assembly needed

### 5.2 Supporting New LLM Providers

1. Add credentials to GitHub Secrets
2. Update `config/agents.yaml` with the new model identifier
3. litellm handles the rest (supports 100+ providers)

### 5.3 Customizing Context Assembly

Edit `scripts/core/context.py` to change what files are included. The function signatures are:
```python
def build_draft_context(section_id: str) -> str
def build_evaluate_context(section_id: str, mode: str) -> str
```

### 5.4 Adding Pre/Post Processing

Create new scripts in `scripts/` and new workflows in `.github/workflows/`. The pattern is intentionally simple to copy.

---

## Part VI: Non-Goals (Explicit Scope Boundaries)

To maintain simplicity, we explicitly **do not** build:

1. **A web interface** - GitHub *is* the interface
2. **User authentication** - GitHub handles this
3. **A database** - The file system is the database
4. **Real-time collaboration** - Use GitHub's native features
5. **Complex agent orchestration** - Each workflow is single-purpose
6. **Automatic revision loops** - Human remains in the loop
7. **PDF parsing (initially)** - Text/markdown paste is sufficient

---

## Appendix A: Technology Choices

| Concern | Choice | Rationale |
|---------|--------|-----------|
| LLM abstraction | litellm | Lightest weight, broadest provider support |
| Python version | 3.11+ | Modern features, good GitHub Actions support |
| Config format | YAML | Human-readable, good GitHub UI support |
| Content format | Markdown | Renders nicely in GitHub, easy to edit |
| CI/CD | GitHub Actions | Native, no additional setup |

## Appendix B: File Naming Conventions

- Section IDs: lowercase, underscores (e.g., `project_narrative`)
- Config files: lowercase, underscores
- Scripts: lowercase, underscores
- Prompts: `{role}_{variant}.md` pattern

---

*This document is the authoritative reference for GrantOps architecture. Implementation should not deviate from these principles without updating this document first.*
