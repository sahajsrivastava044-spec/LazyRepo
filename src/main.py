
import argparse
import sys

from src.evidence_builder import build_evidence
from src.file_selector import select_relevant_files
from src.local_analyzer import analyze_evidence
from src.repository_scanner import scan_repository


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Investigate a repository issue using local AI."
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="Path to the repository to investigate.",
    )
    parser.add_argument(
        "--issue",
        required=True,
        help="Description of the issue to investigate.",
    )
    parser.add_argument(
        "--max-scan-files",
        type=int,
        default=500,
        help="Maximum files to inventory (default: 500).",
    )
    parser.add_argument(
        "--max-selected-files",
        type=int,
        default=5,
        help="Maximum files to inspect (default: 5).",
    )
    args = parser.parse_args()

    try:
        print("\n=== LazyRepo: Local Repository Investigation ===")
        print(f"Repository: {args.repo}")
        print(f"Issue: {args.issue}\n")

        # 1. Inventory repository paths.
        scan = scan_repository(
            args.repo,
            max_files=args.max_scan_files,
        )
        print(f"[1/4] Inventory: {len(scan.files)} files")
        if scan.warning:
            print(f"WARNING: {scan.warning}")

        # 2. Select paths using explainable keyword ranking.
        selection = select_relevant_files(
            scan,
            args.issue,
            max_files=args.max_selected_files,
        )
        print("\n[2/4] Candidate files:")
        for candidate in selection.candidates:
            print(
                f"  {candidate.path} "
                f"(score={candidate.score}, "
                f"matched={', '.join(candidate.matched_terms)})"
            )

        if not selection.selected_paths:
            print(f"No files selected: {selection.warning}")
            return 1

        # 3. Read only selected, inventoried paths within size limits.
        evidence = build_evidence(scan, selection.selected_paths,max_bytes_per_file=100_000,)
        print(
            f"\n[3/4] Evidence: "
            f"{evidence.successfully_read_count}/"
            f"{len(evidence.files)} files read successfully"
        )

        for result in evidence.files:
            if result.status != "read":
                print(f"  SKIPPED/ERROR: {result.path}: {result.reason}")

        # 4. Ask the local model to analyze the evidence.
        print("\n[4/4] Analyzing with local Ollama model...")
        analysis = analyze_evidence(args.issue, evidence)

        print(f"\n=== Analysis ({analysis.model}) ===\n")
        print(analysis.report)

        print("\n=== Evidence used ===")
        for path in analysis.evidence_files:
            print(f"  - {path}")

        if analysis.warnings:
            print("\n=== Limitations / warnings ===")
            for warning in analysis.warnings:
                print(f"  - {warning}")

        print("\nInvestigation complete. No repository files were modified.")
        return 0

    except (FileNotFoundError, NotADirectoryError, ValueError) as error:
        print(f"Input error: {error}", file=sys.stderr)
        return 2
    except RuntimeError as error:
        print(f"Analysis error: {error}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
