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
    OpenProblem,
    OpenProblemCatalog,
    default_open_problem_catalog,
    merge_catalogs,
)


class OpenProblemsToolkitWidget(QWidget):
    """Offline-first catalog browser with import/play callbacks."""

    def __init__(self, import_callback, play_callback, parent=None) -> None:
        super().__init__(parent)
        self.import_callback = import_callback
        self.play_callback = play_callback
        self.catalogs: list[OpenProblemCatalog] = [default_open_problem_catalog()]
        self.problems: dict[str, OpenProblem] = {}
        self._rebuild_problem_map()

        notice = QLabel(
            "Catalog statuses are dated source snapshots. Import/Play creates research "
            "navigation and AI attention only; it never means an open problem is solved."
        )
        notice.setWordWrap(True)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search title, domain, tags, summary…")
        self.search.textChanged.connect(self.refresh)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "open", "solved", "partially-resolved", "unknown"])
        self.status_filter.currentTextChanged.connect(self.refresh)

        self.domain_filter = QComboBox()
        self.domain_filter.currentTextChanged.connect(self.refresh)

        filters = QHBoxLayout()
        filters.addWidget(self.search)
        filters.addWidget(self.status_filter)
        filters.addWidget(self.domain_filter)

        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._selection_changed)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMinimumHeight(180)

        self.import_button = QPushButton("Import to Canvas")
        self.import_button.clicked.connect(self.import_selected)
        self.play_button = QPushButton("▶ Play on Canvas with Local AI")
        self.play_button.clicked.connect(self.play_selected)
        self.catalog_button = QPushButton("Import Catalog JSON")
        self.catalog_button.clicked.connect(self.import_catalog_file)

        buttons = QHBoxLayout()
        buttons.addWidget(self.import_button)
        buttons.addWidget(self.play_button)
        buttons.addWidget(self.catalog_button)

        layout = QVBoxLayout(self)
        layout.addWidget(notice)
        layout.addLayout(filters)
        layout.addWidget(self.list)
        layout.addWidget(self.details)
        layout.addLayout(buttons)

        self._refresh_domains()
        self.refresh()

    def _rebuild_problem_map(self) -> None:
        self.problems = {problem.problem_id: problem for problem in merge_catalogs(self.catalogs)}

    def _refresh_domains(self) -> None:
        current = self.domain_filter.currentText() if self.domain_filter.count() else "All"
        domains = sorted({problem.domain for problem in self.problems.values()})
        self.domain_filter.blockSignals(True)
        self.domain_filter.clear()
        self.domain_filter.addItem("All")
        self.domain_filter.addItems(domains)
        index = self.domain_filter.findText(current)
        self.domain_filter.setCurrentIndex(index if index >= 0 else 0)
        self.domain_filter.blockSignals(False)

    def refresh(self) -> None:
        selected_id = self.selected_problem_id()
        query = self.search.text().strip().casefold()
        status = self.status_filter.currentText().strip().casefold()
        domain = self.domain_filter.currentText().strip()

        self.list.clear()
        for problem in sorted(self.problems.values(), key=lambda p: (p.status != "open", p.domain, p.title)):
            if status and status != "all" and problem.status != status:
                continue
            if domain and domain != "All" and problem.domain != domain:
                continue
            if query:
                haystack = " ".join(
                    (
                        problem.problem_id,
                        problem.title,
                        problem.domain,
                        problem.collection,
                        problem.summary,
                        " ".join(problem.tags),
                    )
                ).casefold()
                if query not in haystack:
                    continue
            marker = "OPEN" if problem.status == "open" else problem.status.upper()
            item = QListWidgetItem(f"[{marker}] {problem.title} — {problem.domain}")
            item.setData(Qt.UserRole, problem.problem_id)
            self.list.addItem(item)
            if problem.problem_id == selected_id:
                self.list.setCurrentItem(item)

        if self.list.currentItem() is None and self.list.count():
            self.list.setCurrentRow(0)
        if not self.list.count():
            self.details.setPlainText("No problems match the current filters.")

    def selected_problem_id(self) -> str | None:
        item = self.list.currentItem()
        return None if item is None else str(item.data(Qt.UserRole))

    def selected_problem(self) -> OpenProblem | None:
        problem_id = self.selected_problem_id()
        return self.problems.get(problem_id) if problem_id else None

    def _selection_changed(self, current, previous) -> None:
        problem = self.selected_problem()
        if problem is None:
            return
        self.details.setPlainText(
            "\n".join(
                [
                    problem.title,
                    f"Status: {problem.status}",
                    f"Domain: {problem.domain}",
                    f"Collection: {problem.collection}",
                    f"Authority: {problem.authority}",
                    f"Last verified: {problem.last_verified}",
                    f"Source: {problem.source_url}",
                    f"Tags: {', '.join(problem.tags) or 'none'}",
                    "",
                    problem.summary,
                    "",
                    "Research navigation only. Play does not create proof or resolution status.",
                ]
            )
        )

    def import_selected(self) -> None:
        problem = self.selected_problem()
        if problem is not None:
            self.import_callback(problem)

    def play_selected(self) -> None:
        problem = self.selected_problem()
        if problem is not None:
            self.play_callback(problem)

    def import_catalog_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import CACE Open Problem Catalog",
            "",
            "CACE Open Problem Catalog (*.json);;JSON (*.json)",
        )
        if not path:
            return
        try:
            catalog = OpenProblemCatalog.load_path(Path(path))
            # Validate conflicts before accepting the catalog.
            merge_catalogs((*self.catalogs, catalog))
        except Exception as exc:
            self.details.setPlainText(f"Catalog import failed: {type(exc).__name__}: {exc}")
            return
        self.catalogs.append(catalog)
        self._rebuild_problem_map()
        self._refresh_domains()
        self.refresh()
        self.details.append(
            f"\nImported catalog {catalog.title!r} with {len(catalog.problems)} problem(s)."
        )
