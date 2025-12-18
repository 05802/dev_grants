# GrantOps

A headless, version-control-centric system for drafting, editing, and evaluating grant applications.

**Philosophy:** Treat grant writing like software development. Git is the database. GitHub is the UI. Actions are the runtime.

## Quick Start

### 1. Setup Secrets

Add your LLM API keys to repository secrets:
- `OPENAI_API_KEY` - For GPT-4o (parsing, evaluation)
- `ANTHROPIC_API_KEY` - For Claude (drafting)

Go to: Settings → Secrets and variables → Actions → New repository secret

### 2. Add Your Project Context

Edit the files in `context/`:

```
context/
├── project.md      # Your project's goals, approach, and narrative
├── organization.md # Your organization's background and capabilities
└── style.md        # Writing tone and conventions
```

### 3. Add Your RFP

Place your RFP/guidelines document in `application/source/` as markdown or text:

```bash
application/source/rfp.md
```

### 4. Parse the RFP

Go to **Actions** → **Parse RFP** → **Run workflow**

Input the source filename (e.g., `rfp.md`). This will:
- Extract sections and requirements
- Create a directory for each section in `application/sections/`
- Generate `meta.yaml` (requirements) and `outline.md` (structure template)

### 5. Customize Outlines

Edit `application/sections/{section}/outline.md` to control the structure of each section before drafting.

### 6. Generate Drafts

Go to **Actions** → **Draft Section** → **Run workflow**

Input the section ID (e.g., `project_narrative`). This will:
- Generate a draft following your outline
- Create a new branch and Pull Request
- Show the diff against any previous version

### 7. Evaluate Drafts

Go to **Actions** → **Evaluate Section** → **Run workflow**

Choose the section and evaluation mode:
- **style** - Writing quality, clarity, style guide adherence
- **logic** - Requirements coverage, internal consistency
- **alignment** - Project narrative coherence, cross-section consistency

Optionally provide a PR number to post the evaluation as a comment.

## Repository Structure

```
.
├── .github/workflows/     # GitHub Action workflows
│   ├── draft.yml          # Generate section drafts
│   ├── evaluate.yml       # Evaluate draft quality
│   └── parse.yml          # Parse RFP documents
├── config/
│   ├── agents.yaml        # LLM model configuration
│   └── prompts/           # System prompts for each operation
├── context/               # Shared project context
│   ├── project.md         # Project goals and narrative
│   ├── organization.md    # Organization background
│   └── style.md           # Writing style guide
├── application/
│   ├── source/            # RFP/guidelines documents
│   └── sections/          # Generated section structure
│       └── {section_id}/
│           ├── meta.yaml  # Requirements & criteria
│           ├── outline.md # Structure template (editable)
│           └── draft.md   # Current draft (versioned)
└── scripts/               # Python implementation
```

## Configuration

### Model Selection (`config/agents.yaml`)

```yaml
agents:
  parser:
    model: "gpt-4o"
    temperature: 0.1
  drafter:
    model: "claude-sonnet-4-20250514"
    temperature: 0.7
  evaluator:
    model: "gpt-4o"
    temperature: 0.3
```

Change models by editing this file. Supports any model available through [litellm](https://docs.litellm.ai/docs/providers).

### Prompts (`config/prompts/`)

Customize LLM behavior by editing the prompt files:
- `drafter.md` - Instructions for generating drafts
- `evaluator_style.md` - Style evaluation criteria
- `evaluator_logic.md` - Logic evaluation criteria
- `evaluator_alignment.md` - Alignment evaluation criteria
- `parser.md` - RFP parsing instructions

## Workflow Details

### Draft Workflow

**Trigger:** Manual (`workflow_dispatch`)

**Inputs:**
- `section_id` (required): Section to draft
- `branch_name` (optional): Custom branch name

**Process:**
1. Loads project context, style guide, section metadata, and outline
2. Calls the drafter LLM to generate content
3. Creates a new branch (`draft/{section_id}-v{n}`)
4. Commits the draft and opens a Pull Request

**Output:** PR with the new draft, showing diff against previous version

### Evaluate Workflow

**Trigger:** Manual (`workflow_dispatch`)

**Inputs:**
- `section_id` (required): Section to evaluate
- `mode` (required): `style`, `logic`, or `alignment`
- `pr_number` (optional): PR to comment on

**Modes:**
- **style**: Compares draft against style guide; checks clarity, tone, grammar
- **logic**: Checks requirements coverage and internal consistency
- **alignment**: Compares against project narrative and other sections

**Output:** Evaluation report (displayed in Actions log, optionally as PR comment)

### Parse Workflow

**Trigger:** Manual (`workflow_dispatch`)

**Inputs:**
- `source_file` (required): File in `application/source/`

**Process:**
1. Reads the RFP document
2. Extracts sections, requirements, word limits, and criteria
3. Creates section directories with `meta.yaml` and `outline.md`
4. Commits changes to main branch

**Output:** Section structure ready for drafting

## Local Development

Run scripts locally for testing:

```bash
# Install dependencies
pip install -r requirements.txt

# Set API keys
export OPENAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."

# Parse RFP (dry run)
python scripts/parse.py rfp.md --dry-run

# Generate draft (no commit)
python scripts/draft.py project_narrative --no-commit

# Evaluate draft
python scripts/evaluate.py project_narrative --mode style
```

## Design Philosophy

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design rationale:

- **Transparency over Magic** - All prompts and context visible in plain files
- **Editability over Automation** - System proposes, human disposes
- **File System as Schema** - Directory structure defines semantics
- **Single-Purpose Workflows** - Each action does one thing well

## License

[Add your license here]
