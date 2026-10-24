# LazyRepo 🔍

**Investigate unfamiliar repositories with local AI, grounded in source-code evidence.**

LazyRepo is a local-first, Python-based CLI tool that helps developers investigate issues in unfamiliar codebases. It scans a repository, selects potentially relevant files, builds a bounded evidence package, and uses a locally running AI model to generate an evidence-aware investigation report.

Instead of dumping an entire repository into an AI prompt, LazyRepo follows a structured workflow that prioritizes relevant source files, bounded context, citations, and explicit uncertainty.

> Built for the Hacktoberfest Open-Source AI Challenge — Week 3: Slow and Steady.

## The Problem

When contributing to an unfamiliar open-source project, getting started can be harder than writing the eventual fix.

Developers often need to:
- Navigate large repositories to find relevant files.
- Trace relationships between implementation and tests.
- Gather enough context to understand an issue.
- Separate plausible explanations from unsupported assumptions.
- Decide what to inspect or verify next.

Cloud-based AI assistants can help, but they may require sending source code to external services. They can also produce confident explanations that are not supported by the repository evidence.

## The Solution

LazyRepo provides a repeatable first-pass investigation workflow using local AI inference.

Give it a repository path and an issue description. It scans the repository, selects relevant files, reads them within configured safety and size limits, and asks a local model to analyze the collected evidence.

The result is a structured report intended to help developers decide where to investigate next.

## Features

- **Repository scanning:** Builds a repository file inventory while excluding common generated and dependency directories.
- **Explainable file selection:** Ranks candidate files using issue-related keywords and path information.
- **Bounded source reading:** Applies file-size, binary-file, encoding, and path-safety checks.
- **Evidence packaging:** Collects selected source files with line-numbered content.
- **Local AI inference:** Uses Ollama and a locally installed model; no cloud AI API is required by the core analysis workflow.
- **Citation validation:** Checks whether cited file paths and line numbers correspond to the supplied evidence.
- **Defensive analysis:** Detects certain suspicious or contradictory responses and can withhold them.
- **Transparent limitations:** Reports missing or truncated evidence and encourages further verification.
- **Read-only investigation:** Does not modify the target repository or execute its code and tests.

## How It Works

```text
Issue Description
       |
       v
Repository Scanner
       |
       v
Relevant File Selector
       |
       v
Safe, Bounded File Reader
       |
       v
Evidence Builder
       |
       v
Local AI Analyzer (Ollama)
       |
       v
Citation and Response Checks
       |
       v
Investigation Report
```

### 1. Scan

LazyRepo creates an inventory of repository files while skipping common directories such as `.git`, `.venv`, `venv`, and `node_modules`.

### 2. Select

The file selector ranks candidate files based on the issue description and file-path information. This is a lightweight, explainable selection strategy—not a guarantee that every relevant file will be found.

### 3. Build evidence

Selected files are read within configured safety and size limits. The evidence builder validates selected paths against the scan inventory and prepares line-numbered source content for analysis.

### 4. Analyze locally

LazyRepo sends the bounded evidence and issue description to a locally running Ollama model. The model is instructed to distinguish supported observations from hypotheses and unknowns.

### 5. Check and report

LazyRepo validates citations against supplied evidence and applies additional checks for certain unsupported claims. The resulting report helps the developer understand what the evidence suggests and what still needs verification.

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python |
| Local model runtime | Ollama |
| Model used during development | Qwen2.5-Coder 3B |
| Interface | Command-line interface |
| Testing | Python `unittest` |
| AI inference | Local HTTP API |

The model is replaceable in principle, subject to compatibility and available hardware resources.

## Requirements

- Python installed and available on your `PATH`.
- Ollama installed and running.
- A compatible local model with sufficient available memory.
- Git, if you want to clone the repository.

The model used during development is `qwen2.5-coder:3b`. Response quality and speed depend on the model, system resources, and the evidence supplied.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/LazyRepo.git
cd LazyRepo
```

Replace `YOUR_USERNAME` with the actual GitHub username or repository owner.

### 2. Create a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks environment activation, use the appropriate execution-policy configuration for your machine or run the environment's Python executable directly.

**Linux/macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install the model

Install Ollama from its official website:

https://ollama.com/

Then download the model:

```bash
ollama pull qwen2.5-coder:3b
```

Start the Ollama service if it is not already running:

```bash
ollama serve
```

Keep Ollama running while using LazyRepo. If your installation already runs Ollama as a background service, you may not need to start it manually.

### 4. Run LazyRepo

From the repository root:

```bash
python -m src.main --repo "PATH_TO_TARGET_REPOSITORY" --issue "Describe the issue"
```

For example, on Windows:

```powershell
python -m src.main --repo "D:\Projects\Nexus" --issue "Project registry fails to find a project by ID"
```

The example is an investigation prompt, not a claim that Nexus contains a confirmed defect.

## Command-Line Options

| Option | Description |
|---|---|
| `--repo` | Required path to the repository to investigate. |
| `--issue` | Required description of the issue. |
| `--max-scan-files` | Maximum number of files to include in the repository scan; defaults to `500`. |
| `--max-selected-files` | Maximum number of selected files to include for evidence building; defaults to `5`. |

Use:

```bash
python -m src.main --help
```

to inspect the available command-line arguments.

## Example Report

A typical investigation report is organized around these questions:

1. **Relevant evidence:** Which files and source lines relate to the issue?
2. **Likely explanation:** What explanation, if any, is supported by the supplied evidence?
3. **What remains unknown:** Which facts cannot be established yet?
4. **Next verification steps:** What should the developer inspect or test next?
5. **Limitations and warnings:** Was evidence omitted, truncated, or insufficient?

The exact report depends on the model response, selected files, and available evidence.

## Running the Tests

LazyRepo includes unit tests for its scanning, selection, file-reading, evidence-building, and analysis components.

Run the complete suite from the project root:

```bash
python -m unittest discover -s tests -v
```

To run the local analyzer tests:

```bash
python -m unittest tests.test_local_analyzer -v
```

The tests use mocked model responses where appropriate, so the unit-test suite does not require a running Ollama model for every test.

A passing unit-test suite verifies the behaviors covered by those tests. It does not establish that an AI-generated diagnosis is correct for every repository.

## Design Principles

### Local-first

Repository evidence is processed through a locally running model rather than requiring a cloud AI API for the core investigation workflow.

### Evidence before explanation

The system gathers and bounds source evidence before requesting an analysis. The goal is to make the model's reasoning easier to inspect.

### Safety by design

Path validation, file-size limits, binary and encoding checks, and bounded evidence help reduce avoidable risks when inspecting unfamiliar repositories.

### Honest uncertainty

An issue description is not proof of a bug. If the supplied evidence does not establish a defect, the report should make that uncertainty clear.

### Human verification

LazyRepo assists investigation; the developer remains responsible for reproducing the issue, checking the implementation, running tests, and deciding whether a change is appropriate.

## Limitations

LazyRepo is an experimental developer tool, and its safeguards have important limits:

- Keyword-based file selection may miss relevant code or select irrelevant files.
- The context budget can omit relevant source lines.
- Local models can generate incorrect explanations even when citations point to real source lines.
- Citation validation confirms that a reference exists in supplied evidence; it does not prove that the reference semantically supports the claim.
- Contradiction checks cover selected patterns and are not a general proof of correctness.
- LazyRepo does not currently execute repository code, run repository tests, reproduce bugs, or generate and apply patches.
- Local inference can be slower or less capable than larger hosted models, depending on hardware and model choice.

Treat the report as an investigation aid, not an authoritative diagnosis.

## Privacy

LazyRepo's core analysis workflow sends the selected evidence to the configured local Ollama service. It does not require sending repository evidence to a cloud AI provider.

However, local inference alone does not guarantee that an entire workflow is offline. Initial setup and model downloads may require internet access, and other tools or services you use independently may have their own data-handling behavior.

Review the code and your local environment before using LazyRepo with sensitive repositories.

## Roadmap

Potential future improvements include:

- Better relevance ranking using repository structure and symbol relationships.
- More robust evidence-to-claim verification.
- Optional repository test execution in an isolated environment.
- Evaluation fixtures covering both genuine defects and false-positive reports.
- Improved terminal formatting and clearer investigation summaries.
- Additional local model support and performance measurements.

These are potential directions, not features promised to be implemented already.

## Contributing

Contributions are welcome!

You can help by:
- Reporting reproducible bugs.
- Improving file selection and evidence quality.
- Adding regression tests for false positives and genuine defects.
- Improving error handling, documentation, and CLI usability.
- Evaluating behavior across different repository languages and local models.

Please keep contributions focused, include tests for behavioral changes, and document the limitations of new safeguards.

## License

[Add your chosen open-source license here and include the corresponding `LICENSE` file.]

## Acknowledgments

LazyRepo was built for the Hacktoberfest Open-Source AI Challenge, Week 3: **Slow and Steady**.

The project explores how open-weight models and local inference can make AI-assisted repository investigation more accessible, inspectable, and privacy-conscious.
