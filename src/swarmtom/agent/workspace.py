"""An agent's file view: a private working copy of its brief, its batches and the shared files.

Agents never see the world directory itself (it holds ground_truth.json). Each game gives each
agent its own copy, so files an agent writes from the Python tool stay private to it.
"""

from __future__ import annotations

import shutil
from pathlib import Path, PurePosixPath

import pandas as pd
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

TEXT_SUFFIXES = {".md", ".txt", ".csv", ".json", ".py", ".log"}


class WorkspaceError(Exception):
    """A tool argument the agent can fix (bad path, missing sheet...)."""


class Workspace:
    def __init__(self, root: Path):
        self.root = root.resolve()

    @classmethod
    def create(cls, world_dir: Path, callsign: str, dest: Path) -> "Workspace":
        if not dest.exists():
            agent_dir = world_dir / "agents" / callsign
            dest.mkdir(parents=True)
            shutil.copy2(agent_dir / "TASK_BRIEF.md", dest / "TASK_BRIEF.md")
            shutil.copytree(agent_dir / "batches", dest / "batches")
            shutil.copytree(world_dir / "shared", dest / "shared")
        return cls(dest)

    def resolve(self, rel: str) -> Path:
        rel = (rel or "").strip().replace("\\", "/")
        if rel.startswith("/"):
            raise WorkspaceError("Use paths relative to your workspace, e.g. 'shared/lot_master.xlsx'.")
        parts = PurePosixPath(rel).parts
        if ".." in parts:
            raise WorkspaceError("Paths may not contain '..'.")
        path = (self.root / rel).resolve()
        if path != self.root and self.root not in path.parents:
            raise WorkspaceError("Path is outside your workspace.")
        return path

    def list_files(self, rel: str = "") -> str:
        base = self.resolve(rel)
        if not base.exists():
            raise WorkspaceError(f"No such directory: {rel or '.'}")
        if base.is_file():
            return f"{rel} ({base.stat().st_size:,} bytes)"
        lines = []
        for p in sorted(base.rglob("*")):
            if p.is_file() and not any(part.startswith(".") for part in p.relative_to(self.root).parts):
                lines.append(f"{p.relative_to(self.root).as_posix()}  ({p.stat().st_size:,} bytes)")
        return "\n".join(lines) or "(empty)"

    def read_document(self, rel: str, page: int = 1, page_chars: int = 8000) -> str:
        path = self.resolve(rel)
        if not path.is_file():
            raise WorkspaceError(f"No such file: {rel}")
        if path.suffix.lower() == ".docx":
            text = docx_text(path)
        elif path.suffix.lower() in TEXT_SUFFIXES:
            text = path.read_text(errors="replace")
        elif path.suffix.lower() in (".xlsx", ".xls"):
            raise WorkspaceError("This is a spreadsheet; use read_table or run_python.")
        else:
            raise WorkspaceError(f"Unsupported file type: {path.suffix}")
        pages = max(1, -(-len(text) // page_chars))
        if not 1 <= page <= pages:
            raise WorkspaceError(f"Page {page} out of range (1–{pages}).")
        chunk = text[(page - 1) * page_chars: page * page_chars]
        return f"[{rel} — page {page} of {pages}]\n{chunk}"

    def read_table(self, rel: str, sheet: str | None = None, start_row: int = 0, n_rows: int = 40) -> str:
        path = self.resolve(rel)
        if not path.is_file():
            raise WorkspaceError(f"No such file: {rel}")
        if path.suffix.lower() == ".csv":
            sheets = {"(csv)": pd.read_csv(path)}
        elif path.suffix.lower() in (".xlsx", ".xls"):
            sheets = pd.read_excel(path, sheet_name=None)
        else:
            raise WorkspaceError("read_table supports .xlsx and .csv files.")
        name = sheet or next(iter(sheets))
        if name not in sheets:
            raise WorkspaceError(f"No sheet {name!r}; sheets are {list(sheets)}.")
        df = sheets[name]
        n_rows = max(1, min(int(n_rows), 200))
        start_row = max(0, int(start_row))
        part = df.iloc[start_row: start_row + n_rows]
        end = start_row + len(part)
        header = (f"[{rel} — sheet {name!r} of {list(sheets)}; rows {start_row}–{max(start_row, end - 1)} "
                  f"of {len(df)} (0-indexed); columns: {list(df.columns)}]")
        return header + "\n" + part.to_csv(index=False)


def docx_text(path: Path) -> str:
    """Paragraphs and tables in document order."""
    doc = Document(path)
    out = []
    for child in doc.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            t = Paragraph(child, doc).text
            if t.strip():
                out.append(t)
        elif tag == "tbl":
            for row in Table(child, doc).rows:
                out.append(" | ".join(c.text for c in row.cells))
    return "\n".join(out)
