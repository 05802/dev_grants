# Implementation Plan: Local File-Based GrantOps

## Executive Summary

Transform GrantOps from a GitHub-native system into a **local-first, file-based application** that can operate entirely offline, uses markdown files as both storage and interface, and remains fully headless/scriptable.

---

## Part 1: Philosophical Foundations & Architectural Choices

### 1.1 Core Philosophy Tensions

| Tension | Option A | Option B | Recommendation |
|---------|----------|----------|----------------|
| **Storage Format** | Pure Markdown (everything in `.md`) | Markdown + YAML frontmatter | **Frontmatter** - structured metadata embedded in readable files |
| **Versioning** | Git-based (keep current) | File-based snapshots (`.versions/`) | **Hybrid** - Git optional, local snapshots as fallback |
| **State Management** | Stateless (each run is independent) | Stateful (track progress, history) | **Stateful** - local state file enables resumability |
| **Orchestration** | Manual CLI invocations | Declarative pipeline files | **Both** - CLI for flexibility, pipeline files for repeatability |
| **Output Format** | Modify files in place | Generate to separate output dir | **Configurable** - support both modes |

### 1.2 The "Markdown as Database" Paradigm

**Key Insight**: Markdown with YAML frontmatter creates human-readable, machine-parseable documents that serve as both **data storage** and **user interface**.

```markdown
---
id: project-narrative
title: Project Narrative
status: draft
version: 3
word_limit: 2000
last_modified: 2024-01-15T10:30:00Z
agent: drafter_creative
evaluation_scores:
  style: 8.5
  logic: 7.2
  alignment: 9.0
---

# Project Narrative

## Problem Statement

[Content here...]
```

**Benefits**:
- Human-readable without tools
- Git-friendly (meaningful diffs)
- Editable in any text editor
- Parseable by scripts
- Self-documenting

---

## Part 2: Proposed Directory Structure

### 2.1 New Structure

```
my-grant-project/
├── .grantops/                    # System directory (gitignored optional)
│   ├── config.yaml               # Local configuration
│   ├── state.yaml                # Current state/progress
│   ├── history/                  # Operation history
│   │   └── 2024-01-15-draft-narrative.yaml
│   └── cache/                    # LLM response cache (optional)
│
├── config/                       # User-editable configuration
│   ├── agents.md                 # Agent definitions (markdown table + frontmatter)
│   └── prompts/                  # System prompts
│       ├── drafter.md
│       ├── parser.md
│       └── evaluators/
│           ├── style.md
│           ├── logic.md
│           └── alignment.md
│
├── context/                      # Shared knowledge (unchanged)
│   ├── project.md
│   ├── organization.md
│   └── style.md
│
├── source/                       # Input documents
│   ├── rfp.md                    # Main RFP document
│   └── attachments/              # Supporting materials
│
├── sections/                     # The heart of the application
│   ├── _index.md                 # Section overview/manifest
│   ├── project-narrative/
│   │   ├── section.md            # Main file: frontmatter + content
│   │   ├── outline.md            # Structure template
│   │   ├── notes.md              # User notes, research
│   │   └── .versions/            # Local version history
│   │       ├── v1.md
│   │       └── v2.md
│   └── budget-justification/
│       └── ...
│
├── evaluations/                  # Evaluation reports
│   ├── project-narrative/
│   │   ├── style-2024-01-15.md
│   │   ├── logic-2024-01-15.md
│   │   └── alignment-2024-01-15.md
│   └── ...
│
├── output/                       # Generated artifacts
│   ├── compiled/                 # Full application assembly
│   │   └── application-v1.md
│   └── exports/                  # Format conversions
│       ├── application.pdf
│       └── application.docx
│
├── pipelines/                    # Declarative workflows (optional)
│   ├── full-draft.yaml
│   └── final-review.yaml
│
└── grantops.yaml                 # Project manifest (root config)
```

### 2.2 Architectural Decision: Single File vs Directory per Section

**Option A: Single File per Section** (`sections/project-narrative.md`)
- Pros: Simpler, fewer files
- Cons: Mixing content with metadata becomes unwieldy

**Option B: Directory per Section** (`sections/project-narrative/section.md`)
- Pros: Room for versions, notes, attachments
- Cons: More navigation

**Recommendation**: **Directory per Section** - provides room for:
- Version history without Git
- User notes and research
- Section-specific attachments
- Evaluation history

---

## Part 3: Core Data Models (Markdown Schemas)

### 3.1 Project Manifest (`grantops.yaml`)

```yaml
# grantops.yaml - Project root configuration
name: "NSF Research Grant 2024"
version: "1.0"

defaults:
  agent: drafter
  evaluators: [style, logic, alignment]

source:
  rfp: source/rfp.md
  deadline: 2024-03-15

sections:
  order:
    - project-narrative
    - budget-justification
    - facilities
    - personnel

output:
  format: markdown  # or: pdf, docx
  compile_order: auto  # follows sections.order
```

### 3.2 Section File (`sections/{id}/section.md`)

```markdown
---
# Section Metadata
id: project-narrative
title: "Project Narrative"
status: draft  # draft | review | final | locked
version: 3
created: 2024-01-10T09:00:00Z
modified: 2024-01-15T10:30:00Z

# Requirements (parsed from RFP or manual)
requirements:
  - Describe the problem being addressed
  - Explain the proposed solution
  - Provide evidence of feasibility

word_limit: 2000
current_words: 1847

# Scoring
scoring_weight: 30  # percent of total

# Generation metadata
generated_by: drafter_creative
generation_context:
  model: claude-sonnet-4-20250514
  temperature: 0.7
  timestamp: 2024-01-15T10:30:00Z

# Evaluation summary (latest scores)
evaluations:
  style: { score: 8.5, date: 2024-01-15 }
  logic: { score: 7.2, date: 2024-01-14 }
  alignment: { score: 9.0, date: 2024-01-15 }

# User flags
needs_review: true
flagged_issues:
  - "Budget figures need updating"
  - "Check citation format"
---

# Project Narrative

## Problem Statement

[Draft content here...]

## Proposed Solution

[Draft content here...]
```

### 3.3 Agent Configuration (`config/agents.md`)

**Choice**: YAML file vs Markdown with embedded table

**Recommendation**: Keep as YAML (`config/agents.yaml`) for machine parsing, but provide a `config/agents.md` that's auto-generated for human reading.

```markdown
---
# Agent Registry
format_version: 1
---

# Available Agents

## Drafting Agents

### drafter (default)
- **Model**: claude-sonnet-4-20250514
- **Temperature**: 0.7
- **Use for**: Standard draft generation
- **Prompt**: [drafter.md](prompts/drafter.md)

### drafter_creative
- **Model**: claude-sonnet-4-20250514
- **Temperature**: 0.9
- **Use for**: Creative/innovative sections

| Agent | Model | Temperature | Purpose |
|-------|-------|-------------|---------|
| drafter | claude-sonnet-4-20250514 | 0.7 | Standard drafts |
| drafter_creative | claude-sonnet-4-20250514 | 0.9 | Creative sections |
| parser | gpt-4o | 0.1 | RFP parsing |
```

### 3.4 Evaluation Reports (`evaluations/{section}/{type}-{date}.md`)

```markdown
---
section: project-narrative
evaluation_type: style
date: 2024-01-15T14:30:00Z
agent: evaluator_strict
draft_version: 3
overall_score: 8.5
---

# Style Evaluation: Project Narrative

**Draft Version**: 3
**Evaluated**: 2024-01-15 14:30 UTC
**Agent**: evaluator_strict
**Overall Score**: 8.5/10

## Summary

The draft demonstrates strong adherence to the style guide with clear,
professional language. Minor issues with passive voice in technical sections.

## Strengths

1. **Clear problem framing** - Opening paragraph immediately establishes stakes
2. **Active voice** - 85% of sentences use active construction
3. **Consistent terminology** - Key terms used uniformly throughout

## Issues Found

### Issue 1: Passive Voice in Methods
- **Location**: Paragraph 3, sentences 2-4
- **Current**: "The data will be collected and analyzed..."
- **Suggested**: "We will collect and analyze the data..."
- **Severity**: Minor

### Issue 2: Jargon Without Definition
- **Location**: Paragraph 5
- **Term**: "heterogeneous computing paradigm"
- **Recommendation**: Define on first use or simplify

## Recommendations

1. Revise passive constructions in methodology section
2. Add glossary or define technical terms inline
3. Shorten paragraph 7 (currently 12 sentences)

## Metrics

| Metric | Score | Target |
|--------|-------|--------|
| Readability (Flesch) | 42 | 40-50 |
| Passive Voice % | 15% | <20% |
| Avg Sentence Length | 24 words | <25 |
| Style Guide Adherence | 92% | >90% |
```

---

## Part 4: State Management

### 4.1 The State Problem

**Question**: How do we track progress, history, and resumability without a database?

**Options**:

| Approach | Description | Pros | Cons |
|----------|-------------|------|------|
| **Stateless** | Each CLI run is independent | Simple, no cleanup | No history, no resumability |
| **File-embedded state** | State in frontmatter | Self-contained | Scattered, hard to query |
| **Central state file** | `.grantops/state.yaml` | Easy to query/backup | Extra file to maintain |
| **Git-based** | State = Git history | Powerful, auditable | Requires Git knowledge |

**Recommendation**: **Hybrid approach**
- File-embedded state for section-specific data (in frontmatter)
- Central state file for cross-cutting concerns (current workflow, queue)
- Git optional for history (but not required)

### 4.2 State File (`.grantops/state.yaml`)

```yaml
# .grantops/state.yaml
# Auto-managed by grantops CLI

project:
  initialized: 2024-01-10T09:00:00Z
  last_activity: 2024-01-15T14:30:00Z

current_workflow:
  active: true
  type: draft-all
  started: 2024-01-15T10:00:00Z
  progress:
    completed: [project-narrative, budget-justification]
    current: facilities
    pending: [personnel]
    failed: []

queue:
  - action: evaluate
    section: project-narrative
    mode: alignment
    scheduled: 2024-01-16T09:00:00Z

statistics:
  total_drafts: 15
  total_evaluations: 42
  total_llm_tokens: 125000
  estimated_cost: $4.50

last_operations:
  - timestamp: 2024-01-15T14:30:00Z
    action: evaluate
    section: project-narrative
    mode: style
    result: success

  - timestamp: 2024-01-15T10:30:00Z
    action: draft
    section: project-narrative
    agent: drafter_creative
    result: success
```

### 4.3 History/Audit Trail (`.grantops/history/`)

Each operation creates a timestamped record:

```yaml
# .grantops/history/2024-01-15-103000-draft-project-narrative.yaml
timestamp: 2024-01-15T10:30:00Z
action: draft
section: project-narrative
agent: drafter_creative

input:
  context_files:
    - context/project.md
    - context/style.md
    - sections/project-narrative/outline.md
  context_hash: sha256:abc123...

execution:
  model: claude-sonnet-4-20250514
  temperature: 0.7
  tokens_in: 4500
  tokens_out: 2100
  duration_ms: 8500

output:
  file: sections/project-narrative/section.md
  version_created: 3
  word_count: 1847

result: success
```

---

## Part 5: CLI Design

### 5.1 Command Structure

```bash
grantops <command> [subcommand] [options]
```

### 5.2 Core Commands

```bash
# Project Management
grantops init [--template <name>]           # Initialize new project
grantops status                              # Show project status
grantops validate                            # Validate project structure

# Parsing
grantops parse <source-file>                 # Parse RFP into sections
grantops parse --interactive                 # Interactive section creation

# Drafting
grantops draft <section-id>                  # Draft a single section
grantops draft --all                         # Draft all pending sections
grantops draft --agent <agent-name>          # Use specific agent
grantops draft --outline-only                # Generate outline, not full draft

# Evaluation
grantops evaluate <section-id>               # Run all evaluators
grantops evaluate <section-id> --mode style  # Run specific evaluator
grantops evaluate --all                      # Evaluate all sections
grantops evaluate --report                   # Generate summary report

# Version Management
grantops versions <section-id>               # List versions
grantops versions <section-id> --diff 2 3    # Diff two versions
grantops restore <section-id> --version 2    # Restore previous version
grantops snapshot [message]                  # Create named snapshot of all

# Compilation
grantops compile                             # Compile full application
grantops compile --format pdf                # Compile to specific format
grantops compile --section <id>              # Compile single section

# Utilities
grantops agents                              # List available agents
grantops agents --test <agent>               # Test agent connectivity
grantops context                             # Show assembled context
grantops stats                               # Show project statistics

# Pipeline Execution
grantops run <pipeline-file>                 # Run declarative pipeline
grantops run --dry-run <pipeline-file>       # Preview pipeline
```

### 5.3 Interactive vs Headless Mode

**Design Choice**: Support both modes via flags

```bash
# Headless (default) - non-interactive, scriptable
grantops draft project-narrative --agent drafter

# Interactive - prompts for decisions
grantops draft project-narrative --interactive

# Fully automated batch
grantops run pipelines/full-draft.yaml --yes
```

### 5.4 Output Modes

```bash
# Human-readable (default for TTY)
grantops status

# JSON (for scripting)
grantops status --json

# Quiet (minimal output)
grantops draft section-1 --quiet

# Verbose (debug info)
grantops draft section-1 --verbose
```

---

## Part 6: Pipeline System (Declarative Workflows)

### 6.1 Pipeline File Format

```yaml
# pipelines/full-draft.yaml
name: Full Draft Pipeline
description: Generate drafts for all sections with evaluation

options:
  stop_on_failure: false
  parallel: false  # or: true for concurrent section processing

steps:
  - name: Parse RFP
    action: parse
    source: source/rfp.md
    condition: "!exists(sections/_index.md)"  # Skip if already parsed

  - name: Draft All Sections
    action: draft
    sections: all  # or: [project-narrative, budget]
    agent: drafter
    options:
      skip_existing: true

  - name: Style Evaluation
    action: evaluate
    sections: all
    mode: style

  - name: Logic Evaluation
    action: evaluate
    sections: all
    mode: logic
    continue_on_failure: true

  - name: Generate Report
    action: report
    output: output/evaluation-summary.md
```

### 6.2 Conditional Logic

```yaml
steps:
  - name: Draft if needed
    action: draft
    section: project-narrative
    condition: |
      section.status != 'final' and
      section.evaluation.style.score < 8.0

  - name: Re-evaluate after revision
    action: evaluate
    section: project-narrative
    depends_on: "Draft if needed"
    condition: "steps['Draft if needed'].executed"
```

---

## Part 7: Version Control Without Git

### 7.1 Local Version System

**Design**: Each section maintains its own version history

```
sections/project-narrative/
├── section.md              # Current version
├── .versions/
│   ├── v1.md               # First draft
│   ├── v2.md               # After revision
│   ├── v3.md               # Current (copy of section.md)
│   └── manifest.yaml       # Version metadata
```

**Version Manifest**:
```yaml
# .versions/manifest.yaml
current_version: 3

versions:
  1:
    created: 2024-01-10T09:00:00Z
    agent: drafter
    word_count: 1200
    message: "Initial draft"

  2:
    created: 2024-01-12T14:00:00Z
    agent: drafter_creative
    word_count: 1650
    message: "Expanded problem statement"
    parent: 1

  3:
    created: 2024-01-15T10:30:00Z
    agent: drafter_creative
    word_count: 1847
    message: "Incorporated style feedback"
    parent: 2
```

### 7.2 Global Snapshots

```bash
grantops snapshot "Before major revision"
```

Creates:
```
.grantops/snapshots/
└── 2024-01-15-before-major-revision/
    ├── manifest.yaml
    ├── sections/
    │   ├── project-narrative.md
    │   └── budget-justification.md
    └── context/
        └── project.md
```

### 7.3 Git Integration (Optional)

```yaml
# grantops.yaml
version_control:
  backend: git  # or: local, none
  auto_commit: true
  commit_on:
    - draft
    - evaluate
```

---

## Part 8: Points of Uncertainty & Architectural Forks

### 8.1 Fork: Prompt Storage Location

**Option A: Prompts in Config Directory**
```
config/prompts/drafter.md
```
- Standard, predictable location
- Easy to version control
- Requires path management

**Option B: Prompts Embedded in Agent Config**
```yaml
# config/agents.yaml
agents:
  drafter:
    prompt: |
      You are an expert grant writer...
```
- Self-contained agent definitions
- Harder to edit (YAML string escaping)
- No separate version history

**Option C: Prompts as First-Class Markdown Files with Metadata**
```markdown
---
type: prompt
for: drafter
version: 2
---

# Drafter System Prompt

You are an expert grant writer...
```
- Consistent with markdown-first philosophy
- Full flexibility
- More files to manage

**Recommendation**: **Option A + C Hybrid** - Prompts in dedicated directory as markdown files with optional frontmatter.

### 8.2 Fork: Evaluation Score Persistence

**Option A: Scores in Section Frontmatter**
```yaml
# In section.md frontmatter
evaluations:
  style: { score: 8.5, date: 2024-01-15 }
```
- Self-contained
- Single source of truth
- Can't see evaluation history

**Option B: Separate Evaluation Files**
```
evaluations/project-narrative/style-2024-01-15.md
```
- Full history preserved
- Detailed reports
- Redundancy with summary scores

**Recommendation**: **Both** - Full reports in `evaluations/`, summary scores in frontmatter.

### 8.3 Fork: Context Assembly Strategy

**Option A: Explicit Context Files**
```yaml
# section.md frontmatter
context:
  include:
    - context/project.md
    - context/style.md
    - sections/budget/section.md  # Cross-reference
```
- Fine-grained control
- Explicit dependencies
- Manual maintenance

**Option B: Convention-Based Context**
- Drafter always includes: project.md, style.md, outline.md
- Evaluators have predefined context per mode
- Overridable but not required

**Recommendation**: **Option B with Override** - Sensible defaults, explicit when needed.

### 8.4 Fork: Multi-Application Support

**Option A: One Directory = One Application**
- Simple mental model
- Different grants = different folders
- No cross-project features

**Option B: Multi-Application in One Directory**
```
my-grants/
├── applications/
│   ├── nsf-2024/
│   └── doe-2024/
├── shared-context/     # Reusable across applications
└── grantops.yaml       # Workspace config
```
- Shared context (org info, style guides)
- Cross-project reporting
- More complex structure

**Recommendation**: Start with **Option A**, design for future **Option B** migration.

### 8.5 Fork: LLM Response Caching

**Option A: No Caching**
- Simpler implementation
- Always fresh results
- Higher cost, slower iteration

**Option B: Hash-Based Caching**
```python
cache_key = hash(model + prompt + context + temperature)
if cache_key in cache:
    return cache[cache_key]
```
- Deterministic for same inputs
- Faster iteration
- Stale results risk

**Option C: Semantic Caching**
- Cache similar prompts (embedding similarity)
- More sophisticated
- Harder to implement correctly

**Recommendation**: **Option B** with explicit cache invalidation.

### 8.6 Fork: Error Handling Philosophy

**Option A: Fail Fast**
- Stop on first error
- Clear error messages
- User fixes, reruns

**Option B: Fail Soft with Recovery**
- Continue processing other sections
- Collect all errors
- Report at end

**Option C: Auto-Recovery**
- Retry with backoff
- Try alternate agents
- Self-healing

**Recommendation**: **Option B** for batch operations, **Option A** for single operations, **Option C** opt-in.

---

## Part 9: Implementation Phases

### Phase 1: Core Foundation (MVP)
**Goal**: Basic file-based operation without GitHub

1. **File System Layer**
   - Markdown frontmatter parsing/writing
   - Section directory management
   - Version file handling

2. **CLI Framework**
   - Basic command structure
   - Configuration loading
   - Output formatting (human/JSON)

3. **Core Operations**
   - `grantops init`
   - `grantops draft <section>`
   - `grantops evaluate <section>`
   - `grantops status`

4. **Context Assembly**
   - Port existing context.py logic
   - Add frontmatter support
   - Implement convention-based includes

### Phase 2: State & Versioning
**Goal**: Full version management and state tracking

5. **Version System**
   - `.versions/` directory management
   - Version creation on draft
   - `grantops versions` commands
   - Diff and restore functionality

6. **State Management**
   - `.grantops/state.yaml` tracking
   - Operation history logging
   - Progress tracking for batch operations

7. **Snapshot System**
   - Global snapshots
   - Named snapshot creation
   - Snapshot restoration

### Phase 3: Advanced Features
**Goal**: Pipeline execution and compilation

8. **Pipeline System**
   - YAML pipeline parsing
   - Step execution engine
   - Conditional logic
   - Parallel execution (optional)

9. **Compilation**
   - Multi-section assembly
   - Format conversion (PDF, DOCX)
   - Template system

10. **Caching**
    - LLM response caching
    - Cache invalidation logic
    - Cache statistics

### Phase 4: Polish & Integration
**Goal**: Production readiness

11. **Git Integration** (optional backend)
    - Auto-commit on operations
    - Branch management
    - Sync status

12. **Interactive Mode**
    - Interactive section creation
    - Guided evaluation review
    - Conflict resolution UI

13. **Reporting & Analytics**
    - Project statistics
    - Progress dashboards
    - Cost tracking

---

## Part 10: Migration Strategy

### From Current GitHub-Based System

```bash
# 1. Export from GitHub repo
git clone <current-repo> grant-project
cd grant-project

# 2. Run migration script
grantops migrate --from-github

# This will:
# - Create grantops.yaml from repo structure
# - Convert application/sections/* to sections/*
# - Add frontmatter to existing markdown files
# - Create .grantops/ directory
# - Import git history into .versions/ (optional)

# 3. Verify migration
grantops validate
grantops status
```

### Migration Checklist

- [ ] Convert `application/sections/{id}/meta.yaml` → frontmatter in `section.md`
- [ ] Move `application/sections/{id}/draft.md` → `sections/{id}/section.md`
- [ ] Keep `application/sections/{id}/outline.md` → `sections/{id}/outline.md`
- [ ] Convert `config/agents.yaml` → `config/agents.yaml` (mostly compatible)
- [ ] Move `context/*` → `context/*` (no change)
- [ ] Create `grantops.yaml` project manifest
- [ ] Create `.grantops/` state directory
- [ ] Generate `.versions/` from git history (optional)

---

## Part 11: API Design (for Headless Integration)

### Python API

```python
from grantops import Project, Section, Agent

# Load project
project = Project.load("./my-grant")

# Draft a section
section = project.get_section("project-narrative")
result = section.draft(agent="drafter_creative")

# Evaluate
evaluation = section.evaluate(mode="style")
print(evaluation.score)  # 8.5
print(evaluation.issues)  # List of Issue objects

# Compile
output = project.compile(format="pdf")
output.save("output/application.pdf")

# Batch operations
for section in project.sections:
    if section.status != "final":
        section.draft()
        section.evaluate(mode="style")
```

### Events/Hooks System

```yaml
# grantops.yaml
hooks:
  pre_draft:
    - "python scripts/validate_context.py"
  post_draft:
    - "grantops evaluate {section} --mode style"
  post_evaluate:
    - "python scripts/notify.py {section} {score}"
```

---

## Part 12: Testing Strategy

### Unit Tests
- Frontmatter parsing/serialization
- Version management logic
- Context assembly
- CLI argument parsing

### Integration Tests
- Full draft workflow
- Evaluation workflow
- Pipeline execution
- Migration from GitHub format

### End-to-End Tests
- Complete project lifecycle
- Multi-section application
- Export to various formats

### Mock LLM Testing
```python
# Use mock responses for predictable testing
@mock_llm(response="Mocked draft content...")
def test_draft_creates_section():
    ...
```

---

## Appendix A: File Format Specifications

### A.1 Frontmatter Schema (JSON Schema)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "id": { "type": "string", "pattern": "^[a-z0-9-]+$" },
    "title": { "type": "string" },
    "status": { "enum": ["draft", "review", "final", "locked"] },
    "version": { "type": "integer", "minimum": 1 },
    "created": { "type": "string", "format": "date-time" },
    "modified": { "type": "string", "format": "date-time" },
    "word_limit": { "type": "integer" },
    "requirements": { "type": "array", "items": { "type": "string" } },
    "evaluations": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "score": { "type": "number" },
          "date": { "type": "string", "format": "date" }
        }
      }
    }
  },
  "required": ["id", "title", "status"]
}
```

### A.2 CLI Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | File not found |
| 4 | Invalid project structure |
| 5 | LLM API error |
| 6 | Pipeline step failed |
| 7 | Validation failed |

---

## Appendix B: Configuration Reference

### B.1 `grantops.yaml` Full Schema

```yaml
# Project identification
name: string (required)
version: string

# Source documents
source:
  rfp: path (required)
  attachments: path[]
  deadline: date

# Section configuration
sections:
  order: string[]  # Section IDs in desired order
  defaults:
    status: draft
    word_limit: 1000

# Output configuration
output:
  directory: path (default: output/)
  format: markdown | pdf | docx
  template: path

# Agent defaults
agents:
  default_drafter: string (default: drafter)
  default_evaluator: string (default: evaluator)

# Version control
version_control:
  backend: git | local | none
  auto_commit: boolean
  auto_snapshot: boolean

# Caching
cache:
  enabled: boolean
  ttl: duration (e.g., "24h")
  max_size: bytes (e.g., "100MB")

# Hooks
hooks:
  pre_draft: command[]
  post_draft: command[]
  pre_evaluate: command[]
  post_evaluate: command[]
  pre_compile: command[]
  post_compile: command[]
```

---

## Summary: Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Storage format | Markdown + YAML frontmatter | Human-readable, machine-parseable |
| Directory structure | Directory per section | Room for versions, notes, attachments |
| State management | Hybrid (embedded + central) | Best of both worlds |
| Versioning | Local `.versions/` + optional Git | Works offline, Git when available |
| CLI design | Subcommand pattern | Familiar, extensible |
| Pipeline format | YAML declarative | Readable, versionable |
| Output modes | Human/JSON/Quiet | Supports all use cases |
| Error handling | Fail soft for batch | Better UX for large projects |

---

## Next Steps

1. **Validate this plan** with stakeholders
2. **Prototype Phase 1** (core file operations)
3. **Define test fixtures** (sample projects)
4. **Implement CLI framework**
5. **Iterate based on usage patterns**
