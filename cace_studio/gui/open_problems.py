from __future__ import annotations

from pathlib import Path

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QComboBox,
        QFileDialog,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    raise RuntimeError("GUI requires PySide6. Install with: pip install -e '.[gui]'") from exc

from cace_studio.research.open_problems import (
    OPEN_PROBLEM_STATUSES,
    OpenProblem,
    OpenProblemCatalog,
    load_millennium_catalog,
)


class OpenProblemsWidget(QWidget):
    """Offline-first source-backed research problem browser."""

    def __init__(self, import_callback, play_callback, parent=None) -> None:
        super().__init__(parent)
        self.import_callback = import_callback
        self.play_callback = play_callback
        self._entries: dict[str, OpenProblem] = {
            entry.problem_id: entry for entry in load_millennium_catalog().entries
        }

        self.notice = QLabel(
            "Research navigation only. Problem status is date-stamped; AI Play cannot "
            "mark a problem solved or create verification evidence."
        )
        self.notice.setWordWrap(True)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search open problems, fields, tags…")
        self.search.textChanged.connect(self.refresh)

        self.status = QComboBox()
        self.status.addItem("All statuses", "")
        for value in OPEN_PROBLEM_STATUSES:
            self.status.addItem(value, value)
        self.status.currentIndexChanged.connect(self.refresh)

        filters = QHBoxLayout()
        filters.addWidget(self.search)
        filters.addWidget(self.status)

        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._selection_changed)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMinimumHeight(180)

        self.import_button = QPushButton("Import to Canvas")
        self.import_button.clicked.connect(self.import_selected)
        self.play_button = QPushButton("▶ Play on Canvas with Local AI")
        self.play_button.clicked.connect(self.play_selected)
        self.custom_button = QPushButton("Import Catalog JSON")
        self.custom_button.clicked.connect(self.import_catalog_file)

        buttons = QHBoxLayout()
        buttons.addWidget(self.import_button)
        buttons.addWidget(self.play_button)
        buttons.addWidget(self.custom_button)

        self.result = QLabel()
        self.result.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.notice)
        layout.addLayout(filters)
        layout.addWidget(self.list)
        layout.addWidget(self.details)
        layout.addLayout(buttons)
        layout.addWidget(self.result)
        self.refresh()

    def _filtered(self) -> tuple[OpenProblem, ...]:
        needle = self.search.text().strip().casefold()
        status = self.status.currentData() or None
        values = []
        for entry in self._entries.values():
            if status and entry.status != status:
                continue
            haystack = " ".join(
                (
                    entry.title,
                    entry.domain,
                    entry.collection,
                    entry.summary,
                    " ".join(entry.tags),
                )
            ).casefold()
            if needle and needle not in haystack:
                continue
            values.append(entry)
        values.sort(key=lambda item: (item.status, item.domain, item.title))
        return tuple(values)

    def refresh(self) -> None:
        selected_id = self.selected_problem().problem_id if self.selected_problem() else None
        self.list.blockSignals(True)
        self.list.clear()
        for entry in self._filtered():
            item = QListWidgetItem(f"[{entry.status}] {entry.title}")
            item.setData(Qt.UserRole, entry.problem_id)
            self.list.addItem(item)
            if selected_id == entry.problem_id:
                self.list.setCurrentItem(item)
        self.list.blockSignals(False)
        if self.list.currentItem() is None and self.list.count():
            self.list.setCurrentRow(0)
        self._selection_changed(self.list.currentItem(), None)

    def selected_problem(self) -> OpenProblem | None:
        item = self.list.currentItem()
        if item is None:
            return None
        return self._entries.get(str(item.data(Qt.UserRole)))

    def _selection_changed(self, current, previous) -> None:
        problem = self.selected_problem()
        if problem is None:
            self.details.setPlainText("No problem selected.")
            self.import_button.setEnabled(False)
            self.play_button.setEnabled(False)
            return
        self.import_button.setEnabled(True)
        self.play_button.setEnabled(True)
        source_lines = "\n".join(f"  {url}" for url in problem.source_urls)
        self.details.setPlainText(
            f"{problem.title}\n"
            f"Domain: {problem.domain}\n"
            f"Status: {problem.status}\n"
            f"Collection: {problem.collection}\n"
            f"Authority: {problem.authority}\n"
            f"Last verified: {problem.last_verified}\n"
            f"Tags: {', '.join(problem.tags)}\n\n"
            f"{problem.summary}\n\n"
            f"Status note: {problem.status_note or 'none'}\n\n"
            f"Sources:\n{source_lines}"
        )

    def import_selected(self) -> None:
        problem = self.selected_problem()
        if problem is None:
            return
        try:
            node_id = self.import_callback(problem)
        except Exception as exc:
            self.result.setText(f"Import failed: {type(exc).__name__}: {exc}")
            return
        self.result.setText(f"Imported {problem.title} as canvas node {node_id}.")

    def play_selected(self) -> None:
        problem = self.selected_problem()
        if problem is None:
            return
        try:
            accepted = bool(self.play_callback(problem))
        except Exception as exc:
            self.result.setText(f"Play failed: {type(exc).__name__}: {exc}")
            return
        self.result.setText(
            "Heartbeat Play sent to the configured local AI."
            if accepted
            else "Heartbeat Play ran locally; enable/configure Local AI for model analysis."
        )

    def import_catalog_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Open Problems Catalog",
            "",
            "CACE problem catalog (*.json);;JSON (*.json);;All files (*)",
        )
        if not path:
            return
        target = Path(path)
        try:
            if target.stat().st_size > 5_000_000:
                raise ValueError("catalog exceeds 5 MB GUI import limit")
            catalog = OpenProblemCatalog.from_json_text(target.read_text(encoding="utf-8"))
            duplicates = sorted(set(self._entries) & {entry.problem_id for entry in catalog.entries})
            if duplicates:
                raise ValueError(f"catalog contains IDs already loaded: {duplicates[:8]}")
            for entry in catalog.entries:
                self._entries[entry.problem_id] = entry
        except Exception as exc:
            self.result.setText(f"Catalog import failed: {type(exc).__name__}: {exc}")
            return
        self.result.setText(
            f"Imported {len(catalog.entries)} problem card(s) from {catalog.catalog_id}. "
            "Catalog import executes no code."
        )
        self.refresh()
