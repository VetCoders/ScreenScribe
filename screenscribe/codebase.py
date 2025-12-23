"""Codebase integration for mapping findings to source files.

Uses Loctree component manifest and grep fallback to map video review
findings to actual source code locations.
"""

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

console = Console()


@dataclass
class ComponentInfo:
    """Information about a source code component."""

    name: str
    path: str
    lines: int = 0
    imports: list[str] = field(default_factory=list)
    imported_by: list[str] = field(default_factory=list)


@dataclass
class CodeMapping:
    """Mapping from a finding to source code locations."""

    finding_id: int
    component_hints: list[str]  # From semantic analysis affected_components
    matched_files: list[dict]  # [{path, confidence, reason, testids}]
    search_patterns: list[str]  # Patterns used for matching


@dataclass
class CodebaseContext:
    """Loaded codebase context for mapping."""

    project_path: Path
    manifest: dict[str, ComponentInfo]  # name -> ComponentInfo
    manifest_path: Path | None = None
    total_components: int = 0


def load_codebase_context(project_path: Path) -> CodebaseContext | None:
    """
    Load codebase context from project directory.

    Looks for:
    1. component-manifest.json (Loctree generated)
    2. .loctree/snapshot.json (fallback)

    Args:
        project_path: Path to the project root

    Returns:
        CodebaseContext or None if no manifest found
    """
    project_path = Path(project_path).resolve()

    # Try component-manifest.json first (preferred, smaller)
    manifest_path = project_path / "component-manifest.json"
    if manifest_path.exists():
        return _load_component_manifest(manifest_path, project_path)

    # Try .loctree/snapshot.json
    loctree_snapshot = project_path / ".loctree" / "snapshot.json"
    if loctree_snapshot.exists():
        return _load_loctree_snapshot(loctree_snapshot, project_path)

    # No manifest found
    console.print(f"[yellow]No component manifest found in {project_path}[/]")
    console.print("[dim]Run 'loct scan' or ensure component-manifest.json exists[/]")
    return None


def _load_component_manifest(manifest_path: Path, project_path: Path) -> CodebaseContext:
    """Load from component-manifest.json format."""
    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)

    manifest: dict[str, ComponentInfo] = {}

    # Handle both formats: {components: [...]} and [...]
    components = data.get("components", data) if isinstance(data, dict) else data

    for item in components:
        name = item.get("name", "")
        path = item.get("path", "")

        if not name or not path:
            continue

        # Extract component name from path if name is generic
        if name == "default" or not name:
            name = Path(path).stem

        component = ComponentInfo(
            name=name,
            path=path,
            lines=item.get("lines", 0),
            imports=item.get("imports", []),
            imported_by=item.get("importedBy", []),
        )

        # Index by multiple keys for better matching
        manifest[name.lower()] = component
        manifest[Path(path).stem.lower()] = component

    console.print(f"[green]Loaded {len(components)} components from manifest[/]")

    return CodebaseContext(
        project_path=project_path,
        manifest=manifest,
        manifest_path=manifest_path,
        total_components=len(components),
    )


def _load_loctree_snapshot(snapshot_path: Path, project_path: Path) -> CodebaseContext:
    """Load from .loctree/snapshot.json format."""
    with open(snapshot_path, encoding="utf-8") as f:
        data = json.load(f)

    manifest: dict[str, ComponentInfo] = {}
    files = data.get("files", [])

    for item in files:
        path = item.get("path", "")
        if not path:
            continue

        # Skip non-source files
        if not any(path.endswith(ext) for ext in [".tsx", ".ts", ".jsx", ".js", ".vue"]):
            continue

        name = Path(path).stem

        # Extract exported names
        exports = item.get("exports", [])
        export_names = [e.get("name", "") for e in exports if e.get("name")]

        component = ComponentInfo(
            name=name,
            path=path,
            lines=item.get("loc", 0),
            imports=[imp.get("resolved_path", "") for imp in item.get("imports", [])],
            imported_by=[],  # Not directly available in snapshot
        )

        # Index by file name and export names
        manifest[name.lower()] = component
        for export_name in export_names:
            if export_name and export_name.lower() not in manifest:
                manifest[export_name.lower()] = component

    console.print(f"[green]Loaded {len(files)} files from Loctree snapshot[/]")

    return CodebaseContext(
        project_path=project_path,
        manifest=manifest,
        manifest_path=snapshot_path,
        total_components=len(files),
    )


def normalize_component_name(name: str) -> list[str]:
    """
    Generate search variations for a component name.

    "search icon in title bar" -> ["search", "icon", "titlebar", "searchicon", ...]
    Returns list ordered by specificity (more specific first).
    """
    # Clean and lowercase
    name = name.lower().strip()

    # Remove common filler words
    filler_words = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "with", "is", "are"}
    words = [w for w in re.split(r"\W+", name) if w and w not in filler_words and len(w) > 2]

    variations = []

    # Most specific: concatenated full phrase (searchicon, titlebar)
    if len(words) >= 2:
        variations.append("".join(words))
        for i in range(len(words) - 1):
            variations.append(words[i] + words[i + 1])

    # Individual meaningful words (4+ chars preferred)
    long_words = [w for w in words if len(w) >= 4]
    short_words = [w for w in words if len(w) < 4]
    variations.extend(long_words)
    variations.extend(short_words)

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for v in variations:
        if v not in seen:
            seen.add(v)
            unique.append(v)

    return unique


def find_components_by_hint(
    context: CodebaseContext, hint: str, max_results: int = 5
) -> list[tuple[ComponentInfo, float]]:
    """
    Find components matching a hint string.

    Args:
        context: Loaded codebase context
        hint: Component hint (e.g., "search icon", "TitleBar", "login button")
        max_results: Maximum number of results

    Returns:
        List of (ComponentInfo, confidence) tuples, sorted by confidence
    """
    variations = normalize_component_name(hint)
    matches: dict[str, tuple[ComponentInfo, float]] = {}

    # Minimum word length for partial matching
    MIN_PARTIAL_LEN = 4

    for variation in variations:
        variation_lower = variation.lower()

        # Exact match on component name or file stem
        if variation_lower in context.manifest:
            comp = context.manifest[variation_lower]
            if comp.path not in matches or matches[comp.path][1] < 1.0:
                matches[comp.path] = (comp, 1.0)
            continue

        # Skip partial matching for very short variations
        if len(variation_lower) < MIN_PARTIAL_LEN:
            continue

        # Partial match - only if variation is substantial part of key
        for key, comp in context.manifest.items():
            # Variation must be in key (not reverse - too broad)
            if variation_lower in key:
                # Calculate how much of the key the variation covers
                coverage = len(variation_lower) / len(key)

                # Only accept if coverage is significant (>40%)
                if coverage < 0.4:
                    continue

                confidence = min(0.85, coverage)

                if comp.path not in matches or matches[comp.path][1] < confidence:
                    matches[comp.path] = (comp, confidence)

    # Sort by confidence
    sorted_matches = sorted(matches.values(), key=lambda x: x[1], reverse=True)
    return sorted_matches[:max_results]


def grep_for_identifiers(
    project_path: Path,
    patterns: list[str],
    file_extensions: list[str] | None = None,
) -> list[dict]:
    """
    Use ripgrep to find UI identifiers (data-testid, aria-label, etc.).

    Args:
        project_path: Project root path
        patterns: Patterns to search for
        file_extensions: File extensions to search (default: tsx, ts, jsx, js, vue)

    Returns:
        List of {file, line, match, identifier_type} dicts
    """
    if file_extensions is None:
        file_extensions = ["tsx", "ts", "jsx", "js", "vue"]

    results = []

    for pattern in patterns:
        # Build ripgrep command
        glob_patterns = [f"*.{ext}" for ext in file_extensions]
        glob_args = []
        for g in glob_patterns:
            glob_args.extend(["-g", g])

        # Search for data-testid and aria-label containing the pattern
        search_patterns = [
            f'data-testid[="].*{pattern}',
            f'aria-label[="].*{pattern}',
            f"data-testid.*{pattern}",
            f"aria-label.*{pattern}",
        ]

        for search_pattern in search_patterns:
            try:
                cmd = [
                    "rg",
                    "--no-heading",
                    "--line-number",
                    "--ignore-case",
                    *glob_args,
                    search_pattern,
                    str(project_path / "src"),
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        if not line:
                            continue

                        # Parse rg output: file:line:content
                        parts = line.split(":", 2)
                        if len(parts) >= 3:
                            file_path = parts[0]
                            line_num = parts[1]
                            content = parts[2]

                            # Determine identifier type
                            id_type = "unknown"
                            if "data-testid" in content:
                                id_type = "data-testid"
                            elif "aria-label" in content:
                                id_type = "aria-label"

                            results.append(
                                {
                                    "file": file_path,
                                    "line": int(line_num),
                                    "match": content.strip(),
                                    "identifier_type": id_type,
                                    "pattern": pattern,
                                }
                            )

            except subprocess.TimeoutExpired:
                console.print(f"[yellow]Grep timeout for pattern: {pattern}[/]")
            except FileNotFoundError:
                console.print("[yellow]ripgrep (rg) not found - grep fallback disabled[/]")
                return []

    # Deduplicate by file+line and filter out test files
    seen = set()
    unique_results = []
    for r in results:
        # Skip test files
        if "__tests__" in r["file"] or ".test." in r["file"] or ".spec." in r["file"]:
            continue

        key = f"{r['file']}:{r['line']}"
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    return unique_results


def map_finding_to_code(
    finding_id: int,
    component_hints: list[str],
    context: CodebaseContext,
    use_grep: bool = True,
) -> CodeMapping:
    """
    Map a finding to source code locations.

    Args:
        finding_id: The finding/detection ID
        component_hints: List of component hints from semantic analysis
        context: Loaded codebase context
        use_grep: Whether to use grep fallback for data-testid/aria-label

    Returns:
        CodeMapping with matched files
    """
    matched_files: list[dict] = []
    search_patterns: list[str] = []

    # Track which files we've already matched
    matched_paths = set()

    for hint in component_hints:
        # Generate search patterns
        patterns = normalize_component_name(hint)
        search_patterns.extend(patterns[:5])  # Limit patterns

        # Search in manifest
        manifest_matches = find_components_by_hint(context, hint)

        for comp, confidence in manifest_matches:
            if comp.path in matched_paths:
                continue
            matched_paths.add(comp.path)

            matched_files.append(
                {
                    "path": comp.path,
                    "confidence": round(confidence, 2),
                    "reason": f"manifest match for '{hint}'",
                    "component_name": comp.name,
                    "testids": [],
                }
            )

        # Grep fallback for data-testid/aria-label
        if use_grep and patterns:
            grep_results = grep_for_identifiers(context.project_path, patterns[:3])

            for grep_match in grep_results:
                file_path = grep_match["file"]

                # Make path relative to project
                try:
                    rel_path = str(Path(file_path).relative_to(context.project_path))
                except ValueError:
                    rel_path = file_path

                if rel_path in matched_paths:
                    # Add testid to existing match
                    for mf in matched_files:
                        if mf["path"] == rel_path:
                            if grep_match["match"] not in mf["testids"]:
                                mf["testids"].append(grep_match["match"])
                    continue

                matched_paths.add(rel_path)
                matched_files.append(
                    {
                        "path": rel_path,
                        "confidence": 0.7,  # Grep matches are slightly less confident
                        "reason": f"{grep_match['identifier_type']} match for '{grep_match['pattern']}'",
                        "component_name": Path(rel_path).stem,
                        "testids": [grep_match["match"]],
                    }
                )

    # Sort by confidence
    matched_files.sort(key=lambda x: x["confidence"], reverse=True)

    return CodeMapping(
        finding_id=finding_id,
        component_hints=component_hints,
        matched_files=matched_files[:10],  # Limit to top 10
        search_patterns=list(set(search_patterns))[:10],
    )


def map_all_findings(
    semantic_analyses: list,
    context: CodebaseContext,
    use_grep: bool = True,
) -> list[CodeMapping]:
    """
    Map all semantic analysis findings to code.

    Args:
        semantic_analyses: List of SemanticAnalysis objects
        context: Loaded codebase context
        use_grep: Whether to use grep fallback

    Returns:
        List of CodeMapping objects
    """
    mappings = []

    console.print(f"[blue]Mapping {len(semantic_analyses)} findings to codebase...[/]")

    for i, analysis in enumerate(semantic_analyses, 1):
        hints = analysis.affected_components or []

        if not hints:
            # Try to extract hints from summary
            summary_words = re.findall(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b", analysis.summary)
            hints = summary_words[:3]

        if hints:
            console.print(f"[dim]  [{i}/{len(semantic_analyses)}] {', '.join(hints[:3])}...[/]")
            mapping = map_finding_to_code(
                finding_id=analysis.detection_id,
                component_hints=hints,
                context=context,
                use_grep=use_grep,
            )
            mappings.append(mapping)

            if mapping.matched_files:
                console.print(
                    f"[green]  -> {len(mapping.matched_files)} files matched[/]"
                )
            else:
                console.print("[yellow]  -> no matches[/]")
        else:
            console.print(f"[dim]  [{i}/{len(semantic_analyses)}] no component hints[/]")

    return mappings
