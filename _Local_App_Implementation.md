# Implementation Plan: Local File-Based GrantOps

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
│       ├── evaluator_alignment.md
│       └── parser.md
├── context/                    # Shared knowledge base
│   ├── project.md              # Core project logic and goals
│   ├── organization.md         # Boilerplate org info
│   └── style.md                # Voice and tone guidelines
├── application/                # The actual grant content
│   ├── source/                 # Original RFP/guidelines
│   └── sections/               # Generated per-question structure
│       └── {section_id}/       # e.g., project_narrative_Q1
│           ├── meta.yaml       # Requirements, word limits, criteria
│           ├── outline.md      # Editable structure template
│           ├── draft.md        # Current version (for git diffs)
│           ├── draft_YYYY-MM-DD-HHMM.md      # Timestamped snapshots
│           └── evaluation_{mode}_YYYY-MM-DD-HHMM.md  # Evaluation history
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

### 2.3 Hybrid Versioning Strategy

**Design Decision:** Balance git's line-level diff capabilities with explicit file-based version history.

**Problem:**
- Pure git history requires CLI knowledge, not browsable
- Pure dated files lose line-level diff quality in PRs
- Users need both: quick browsing AND detailed change tracking

**Solution: Hybrid Approach**

Each generation creates **two artifacts**:
1. **`draft.md`** - Always contains the latest version
   - Updated in-place with each generation
   - Enables high-quality line-level diffs in Pull Requests
   - Git history provides full change tracking

2. **`draft_YYYY-MM-DD-HHMM.md`** - Timestamped snapshot
   - Automatic copy saved on each generation
   - Browsable file history without git CLI
   - Enables quick file comparisons in any tool
   - Format: `draft_2025-12-18-1430.md` (24-hour time)

**Evaluation files** are always timestamped (no "current" concept):
- `evaluation_style_YYYY-MM-DD-HHMM.md`
- `evaluation_logic_YYYY-MM-DD-HHMM.md`
- `evaluation_alignment_YYYY-MM-DD-HHMM.md`

**Benefits:**
- ✅ PR reviewers see clean line-level diffs
- ✅ Users can browse versions in file explorer
- ✅ Compare any two versions without git
- ✅ Evaluation history is first-class, not buried in PR comments
- ✅ No "which file is current?" confusion (always `draft.md`)

### 2.4 Section Naming Convention: `SectionName_Q#`

**Format:** `{descriptive_name}_Q{number}`

**Examples:**
- `project_narrative_Q1`
- `project_narrative_Q2`
- `budget_justification_Q1`
- `organizational_capacity_Q1`

**Rationale:**
- Clear identification of multi-question sections
- Natural alphabetical sorting
- Flat structure (no nesting) for easy browsing
- Each question is self-contained in its own folder

### 2.5 The LLM Abstraction Layer

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

### 2.6 Context Assembly (The Critical Path)

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

### 2.7 Workflow Design Philosophy

Each GitHub Action workflow follows a pattern:

1. **Receive** explicit inputs (which section, which mode, which agent)
2. **Assemble** context from files
3. **Execute** a single LLM call (or minimal chain)
4. **Output** results to files (both current and timestamped)
5. **Commit** changes to a branch

**Anti-pattern avoided:** Complex multi-step agentic loops. These are:
- Hard to debug
- Expensive (many API calls)
- Unpredictable (cascading errors)

Instead, each workflow does *one thing*. Composition happens at the human level: run Parse, then run Draft, then run Evaluate.

---

## Part III: Revised Requirements & Architectural Changes

### 3.1 Discussion: Versioning Strategy Evolution

**Original Proposal Changes:**
1. ✅ Use `YYYY-MM-DD` timestamps in filenames for version history
2. ✅ Store evaluation versions as unique dated files
3. ✅ Option to modify in-place OR generate new file
4. ✅ Section naming: `SectionName_Q#` format
5. ✅ Flat directories with one folder per question

**Feasibility Analysis:**

| Change | Works? | Complexity | Fragility | Recommendation |
|--------|--------|------------|-----------|----------------|
| Dated draft filenames | ✅ Yes | Medium | Low | ⚠️ Hybrid better |
| Dated evaluation files | ✅ Yes | Low | None | ✅ Strongly yes |
| In-place vs snapshot option | ✅ Yes | Low | None | ✅ Yes |
| `SectionName_Q#` naming | ✅ Yes | None | None | ✅ Yes |
| Flat folders per question | ✅ Yes | Low | None | ✅ Yes |

**Key Tension Identified:** Dated files vs Git diffs

| Approach | Git Diffs (PR reviews) | File History (browser) |
|----------|------------------------|------------------------|
| **Git-only** | ✅ Excellent (line-level) | ❌ Requires git CLI |
| **Dated files only** | ❌ Weak (whole file) | ✅ Easy browsing |
| **Hybrid** ✓ | ✅ Keep `draft.md` for PRs | ✅ Save timestamped copies |

### 3.2 Decision Point

**Question:** Which structure do you prefer? And should dated drafts replace `draft.md` or supplement it?

**Answer:** Use hybrid filenames. The current file is `draft.md`; each generation also saves a timestamped copy.

**Rationale:**
- Preserves git diff quality for PR reviews (line-level changes visible)
- Provides browsable file history without git CLI
- Best of both worlds: precision tracking + accessibility
- Evaluation history becomes queryable and comparable

### 3.3 Updated File Structure Specification

**Per-question directory structure:**

```
application/sections/
└── project_narrative_Q1/
    ├── meta.yaml                              # Section requirements
    ├── outline.md                             # Structure template
    ├── draft.md                               # Current version (always latest)
    ├── draft_2025-12-15-0930.md              # Timestamped snapshots
    ├── draft_2025-12-18-1445.md              # (sorted chronologically)
    ├── draft_2025-12-19-1620.md
    ├── evaluation_style_2025-12-18-1500.md   # Evaluation history
    ├── evaluation_logic_2025-12-19-1000.md   # (mode + timestamp)
    └── evaluation_alignment_2025-12-19-1630.md
```

**File naming conventions:**
- Current draft: `draft.md`
- Draft snapshots: `draft_YYYY-MM-DD-HHMM.md`
- Evaluations: `evaluation_{mode}_YYYY-MM-DD-HHMM.md`
- Timestamp format: ISO date + 24-hour time (e.g., `2025-12-18-1430`)

**Finding the latest version:**
```python
# Scripts default to draft.md for current version
current_draft = f"application/sections/{section_id}/draft.md"

# Can also find latest snapshot by sorting timestamps
def get_latest_snapshot(section_id):
    pattern = f"application/sections/{section_id}/draft_*.md"
    files = sorted(glob(pattern), reverse=True)
    return files[0] if files else None
```

---

## Part IV: Implementation Strategy

### 4.1 Phased Approach

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

### 4.2 Complexity Reduction Decisions

Several simplifications from the original brief:

| Original Idea | Simplified Approach | Rationale |
|---------------|---------------------|-----------|
| Multiple evaluation agents | Single evaluator with mode parameter | One script, one prompt template per mode |
| Auto-commit style fixes | Post fixes as PR comment (diff format) | User reviews before any file changes |
| PDF parsing | Start with markdown/text paste | PDF libraries are fragile; manual paste works |
| LangChain | Direct litellm calls | LangChain adds complexity without benefit here |
| Dropdown inputs | Simple text inputs with validation | Fewer moving parts |
| Git-only versioning | Hybrid (git + timestamped files) | Accessibility + precision |

### 4.3 Configuration Schema

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

**`application/sections/{section_id}/meta.yaml`:**
```yaml
title: "Project Narrative - Question 1"
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

### 4.4 Prompt Architecture

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

### 4.5 Workflow Implementation Pattern

All workflows follow this skeleton:

```yaml
name: Draft Section
on:
  workflow_dispatch:
    inputs:
      section_id:
        description: 'Section to draft (e.g., "project_narrative_Q1")'
        required: true
        type: string
      agent:
        description: 'Agent to use (leave empty for default "drafter")'
        required: false
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
        run: |
          python scripts/draft.py "${{ inputs.section_id }}" \
            --agent "${{ inputs.agent || 'drafter' }}"

      - name: Commit and create PR
        # Git operations: commits draft.md + timestamped snapshot
```

---

## Part V: Action Plan

### Phase 0: Foundation ✅ (Complete)

**Goal:** Establish repository structure and configuration schema.

- [x] Create directory structure as specified above
- [x] Create `config/agents.yaml` with placeholder configuration
- [x] Create example prompt files in `config/prompts/`
- [x] Create example context files in `context/`
- [x] Create `requirements.txt` with minimal dependencies
- [x] Update README with usage instructions

**Deliverable:** A repository that users can clone and immediately start populating with their project context.

### Phase 1: Core Utilities ✅ (Complete)

**Goal:** Build the shared Python infrastructure.

- [x] `scripts/core/llm.py` - Model abstraction layer using litellm
- [x] `scripts/core/context.py` - Context assembly utilities
- [x] `scripts/core/git_ops.py` - Git operations helper (branching, committing)
- [x] Unit tests for core utilities

**Deliverable:** Tested Python modules that other scripts can import.

### Phase 2: Draft Workflow ✅ (Complete - Needs Update)

**Goal:** Enable automated first-draft generation with hybrid versioning.

- [x] `scripts/draft.py` - Main drafting script
- [ ] **UPDATE:** Add timestamped snapshot saving
- [x] `.github/workflows/draft.yml` - GitHub Action workflow
- [x] `config/prompts/drafter.md` - Drafting system prompt
- [ ] **UPDATE:** Documentation for hybrid versioning

**Required Changes:**
1. Modify `draft.py` to save both `draft.md` and `draft_YYYY-MM-DD-HHMM.md`
2. Update git commit to include both files
3. Document timestamp format and file access patterns

**Deliverable:** Users can trigger draft generation from GitHub Actions UI, receiving both current and snapshot versions.

### Phase 3: Evaluate Workflow ✅ (Complete - Needs Update)

**Goal:** Enable automated draft evaluation with timestamped output files.

- [x] `scripts/evaluate.py` - Evaluation script with mode routing
- [ ] **UPDATE:** Save evaluations as `evaluation_{mode}_YYYY-MM-DD-HHMM.md`
- [x] `.github/workflows/evaluate.yml` - GitHub Action workflow
- [x] `config/prompts/evaluator_style.md` - Style evaluation prompt
- [x] `config/prompts/evaluator_logic.md` - Logic evaluation prompt
- [x] `config/prompts/evaluator_alignment.md` - Project alignment prompt
- [ ] **UPDATE:** Documentation for evaluation file history

**Required Changes:**
1. Modify `evaluate.py` to write timestamped files
2. Keep PR comment functionality (optional)
3. Update workflow to commit evaluation files to branch

**Deliverable:** Users can get automated feedback on any draft, with full evaluation history preserved in files.

### Phase 4: Parse Workflow ✅ (Complete - Needs Update)

**Goal:** Automate RFP structure extraction with `SectionName_Q#` naming.

- [x] `scripts/parse.py` - RFP parsing script
- [ ] **UPDATE:** Generate sections with `_Q#` suffix
- [x] `.github/workflows/parse.yml` - GitHub Action workflow
- [x] `config/prompts/parser.md` - Parsing system prompt
- [x] Handling for markdown/text input (PDF deferred)

**Required Changes:**
1. Update parser to extract question numbers
2. Generate section IDs like `project_narrative_Q1`
3. Update prompts to identify multi-question sections

**Deliverable:** Users can auto-generate section structure from RFP text with clear question numbering.

### Phase 5: Integration & Documentation 📝 (New - In Progress)

**Goal:** Update existing system to fully support hybrid versioning.

- [ ] Update `scripts/core/context.py` with timestamp utilities
- [ ] Add `get_latest_snapshot()` helper function
- [ ] Update all scripts to use new file patterns
- [ ] Comprehensive README update with examples
- [ ] Create migration guide (if needed for existing users)
- [ ] Add file structure diagrams to documentation

**Deliverable:** Fully integrated hybrid versioning system with clear documentation.

---

## Part VI: Flexibility & Extension Points

### 6.1 Adding New Evaluation Dimensions

1. Create `config/prompts/evaluator_{dimension}.md`
2. Add the dimension to the workflow's input options
3. (Optional) Update `scripts/evaluate.py` if special context assembly needed

### 6.2 Supporting New LLM Providers

1. Add credentials to GitHub Secrets
2. Update `config/agents.yaml` with the new model identifier
3. litellm handles the rest (supports 100+ providers)

### 6.3 Customizing Context Assembly

Edit `scripts/core/context.py` to change what files are included. The function signatures are:
```python
def build_draft_context(section_id: str) -> str
def build_evaluate_context(section_id: str, mode: str) -> str
```

### 6.4 Adding Pre/Post Processing

Create new scripts in `scripts/` and new workflows in `.github/workflows/`. The pattern is intentionally simple to copy.

### 6.5 Version Comparison Tools

**Comparing draft versions:**
```bash
# Using standard diff
diff application/sections/project_narrative_Q1/draft_2025-12-18-0930.md \
     application/sections/project_narrative_Q1/draft_2025-12-18-1445.md

# Using git diff (even for timestamped files)
git diff --no-index \
  application/sections/project_narrative_Q1/draft_2025-12-18-0930.md \
  application/sections/project_narrative_Q1/draft_2025-12-18-1445.md
```

**Comparing evaluations over time:**
```bash
# See how feedback evolved
ls -t application/sections/project_narrative_Q1/evaluation_style_*.md
# Shows files sorted by timestamp
```

---

## Part VII: Non-Goals (Explicit Scope Boundaries)

To maintain simplicity, we explicitly **do not** build:

1. **A web interface** - GitHub *is* the interface
2. **User authentication** - GitHub handles this
3. **A database** - The file system is the database
4. **Real-time collaboration** - Use GitHub's native features
5. **Complex agent orchestration** - Each workflow is single-purpose
6. **Automatic revision loops** - Human remains in the loop
7. **PDF parsing (initially)** - Text/markdown paste is sufficient
8. **Automatic file cleanup** - Users manually archive old versions if desired
9. **Version garbage collection** - Disk is cheap, history is valuable

---

## Part VIII: Technical Implementation Details

### 8.1 Timestamp Generation

**Python implementation:**
```python
from datetime import datetime

def generate_timestamp() -> str:
    """Generate timestamp in YYYY-MM-DD-HHMM format."""
    return datetime.now().strftime("%Y-%m-%d-%H%M")

def parse_timestamp(filename: str) -> datetime:
    """Extract datetime from timestamped filename."""
    # Expects format: draft_2025-12-18-1430.md
    timestamp_str = filename.split('_')[1].replace('.md', '')
    return datetime.strptime(timestamp_str, "%Y-%m-%d-%H%M")
```

**Usage in draft.py:**
```python
timestamp = generate_timestamp()
current_file = f"application/sections/{section_id}/draft.md"
snapshot_file = f"application/sections/{section_id}/draft_{timestamp}.md"

# Save both files
with open(current_file, 'w') as f:
    f.write(generated_content)

with open(snapshot_file, 'w') as f:
    f.write(generated_content)
```

### 8.2 File Discovery Patterns

**Finding all drafts for a section:**
```python
import glob
from pathlib import Path

def get_all_drafts(section_id: str) -> list[Path]:
    """Get all draft versions, sorted newest first."""
    pattern = f"application/sections/{section_id}/draft_*.md"
    files = [Path(f) for f in glob.glob(pattern)]
    return sorted(files, reverse=True)

def get_latest_draft_snapshot(section_id: str) -> Path:
    """Get most recent timestamped draft."""
    drafts = get_all_drafts(section_id)
    return drafts[0] if drafts else None

def get_current_draft(section_id: str) -> Path:
    """Get the canonical current draft."""
    return Path(f"application/sections/{section_id}/draft.md")
```

**Finding evaluations by mode:**
```python
def get_evaluations(section_id: str, mode: str = None) -> list[Path]:
    """Get evaluation files, optionally filtered by mode."""
    if mode:
        pattern = f"application/sections/{section_id}/evaluation_{mode}_*.md"
    else:
        pattern = f"application/sections/{section_id}/evaluation_*.md"

    files = [Path(f) for f in glob.glob(pattern)]
    return sorted(files, reverse=True)

def get_latest_evaluation(section_id: str, mode: str) -> Path:
    """Get most recent evaluation for a specific mode."""
    evals = get_evaluations(section_id, mode)
    return evals[0] if evals else None
```

### 8.3 Git Commit Strategy

**Committing both files:**
```bash
# In workflow or script
git add "application/sections/${section_id}/draft.md"
git add "application/sections/${section_id}/draft_${timestamp}.md"
git commit -m "Draft ${section_id}: Generated with ${agent} (${timestamp})"
```

**Commit message format:**
- Drafts: `Draft {section_id}: Generated with {agent} ({timestamp})`
- Evaluations: `Evaluation {section_id}/{mode}: {agent} ({timestamp})`
- Parsing: `Parse: Created sections from {source_file}`

---

## Appendix A: Technology Choices

| Concern | Choice | Rationale |
|---------|--------|-----------|
| LLM abstraction | litellm | Lightest weight, broadest provider support |
| Python version | 3.11+ | Modern features, good GitHub Actions support |
| Config format | YAML | Human-readable, good GitHub UI support |
| Content format | Markdown | Renders nicely in GitHub, easy to edit |
| CI/CD | GitHub Actions | Native, no additional setup |
| Versioning | Hybrid (git + timestamps) | Best of both worlds: precision + browsability |
| Timestamp format | YYYY-MM-DD-HHMM | ISO-sortable, human-readable, filesystem-safe |

## Appendix B: File Naming Conventions

- **Section IDs:** lowercase, underscores, with question number (e.g., `project_narrative_Q1`)
- **Current draft:** `draft.md` (no timestamp, always latest)
- **Draft snapshots:** `draft_YYYY-MM-DD-HHMM.md`
- **Evaluations:** `evaluation_{mode}_YYYY-MM-DD-HHMM.md`
- **Config files:** lowercase, underscores
- **Scripts:** lowercase, underscores
- **Prompts:** `{role}_{variant}.md` pattern

**Timestamp format rules:**
- Date: ISO 8601 (YYYY-MM-DD)
- Time: 24-hour format (HHMM), no colon (filesystem-safe)
- Separator: Hyphen between date and time
- Example: `2025-12-18-1430` = December 18, 2025 at 2:30 PM

## Appendix C: Migration Path (for existing repositories)

If updating an existing GrantOps repository:

1. **Rename sections to include Q# suffix:**
   ```bash
   mv application/sections/project_narrative application/sections/project_narrative_Q1
   ```

2. **No need to rename existing draft.md:**
   - Current `draft.md` files work as-is
   - New snapshots will be created on next generation

3. **Update workflows:**
   - Pull latest workflow files from updated repository
   - No breaking changes to inputs

4. **Optional: Create initial snapshots:**
   ```bash
   # Manually create timestamp for existing drafts
   cp application/sections/project_narrative_Q1/draft.md \
      application/sections/project_narrative_Q1/draft_2025-12-18-0000.md
   ```

---

*This document is the authoritative reference for GrantOps implementation with hybrid versioning. All development should align with these specifications. Last updated: 2025-12-18*
