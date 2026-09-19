from __future__ import annotations

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QComboBox,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMessageBox,
        QPushButton,
        QSplitter,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - GUI-only module
    raise RuntimeError("GUI requires PySide6. Install with: pip install -e '.[gui]'") from exc

from cace_studio.ai.research_ideas import IDEA_STATUSES, ResearchIdeaStore


class ResearchIdeasWidget(QWidget):
    """Editable local research notebook.

    ResearchIdea entries are planning artifacts only; status progression is not
    proof qualification and never mutates formal/verification state.
    """

    def __init__(self, store: ResearchIdeaStore, parent=None) -> None:
        super().__init__(parent)
        self.store = store
        self.current_idea_id: str | None = None
        self._loading = False

        self.filter_status = QComboBox()
        self.filter_status.addItem("All statuses", "")
        for status in IDEA_STATUSES:
            self.filter_status.addItem(status, status)
        self.filter_status.currentIndexChanged.connect(self.refresh)

        self.idea_list = QListWidget()
        self.idea_list.currentItemChanged.connect(self._selection_changed)

        new_button = QPushButton("New Idea")
        new_button.clicked.connect(self.new_idea)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Research notebook"))
        left_layout.addWidget(self.filter_status)
        left_layout.addWidget(self.idea_list)
        left_layout.addWidget(new_button)

        self.title = QLineEdit()
        self.status = QComboBox()
        for status in IDEA_STATUSES:
            self.status.addItem(status, status)

        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Observations, rationale, caveats, links to local work…")

        self.hypotheses = QTextEdit()
        self.hypotheses.setPlaceholderText("One hypothesis per line.")

        self.proposed_experiment = QTextEdit()
        self.proposed_experiment.setPlaceholderText(
            "Describe the smallest reproducible experiment and falsification criteria."
        )

        self.modules = QTextEdit()
        self.modules.setMaximumHeight(90)
        self.modules.setPlaceholderText("One CACE module id per line (or comma-separated).")

        self.source = QLabel("Manual idea.")
        self.source.setWordWrap(True)

        self.lifecycle = QLabel(
            "Lifecycle: Idea → Testable → Experimented → Promising → Proof Candidate. "
            "These are research workflow labels, not formal proof status."
        )
        self.lifecycle.setWordWrap(True)

        self.save_button = QPushButton("Save Idea")
        self.save_button.clicked.connect(self.save_current)
        self.advance_button = QPushButton("Advance Status →")
        self.advance_button.clicked.connect(self.advance_current)
        self.delete_button = QPushButton("Delete Idea")
        self.delete_button.clicked.connect(self.delete_current)

        actions = QHBoxLayout()
        actions.addWidget(self.save_button)
        actions.addWidget(self.advance_button)
        actions.addWidget(self.delete_button)
        actions.addStretch()

        editor = QWidget()
        form = QFormLayout(editor)
        form.addRow("Title", self.title)
        form.addRow("Status", self.status)
        form.addRow("Notes", self.notes)
        form.addRow("Hypotheses", self.hypotheses)
        form.addRow("Proposed experiment", self.proposed_experiment)
        form.addRow("Associated modules", self.modules)
        form.addRow("Source", self.source)
        form.addRow(self.lifecycle)
        form.addRow(actions)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(editor)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        root = QVBoxLayout(self)
        root.addWidget(splitter)

        self.refresh()

    @staticmethod
    def _parse_lines(text: str) -> tuple[str, ...]:
        values = []
        seen = set()
        for line in text.replace(",", "\n").splitlines():
            value = line.strip()
            if not value or value in seen:
                continue
            seen.add(value)
            values.append(value)
        return tuple(values)

    def refresh(self, select_id: str | None = None) -> None:
        if self._loading:
            return
        self._loading = True
        try:
            wanted = select_id or self.current_idea_id
            status_filter = str(self.filter_status.currentData() or "")
            self.idea_list.clear()
            for idea in self.store.list(status=status_filter or None):
                item = QListWidgetItem(f"[{idea.status}] {idea.title}")
                item.setData(Qt.UserRole, idea.idea_id)
                item.setToolTip(f"Updated {idea.updated_utc}")
                self.idea_list.addItem(item)
                if wanted and idea.idea_id == wanted:
                    self.idea_list.setCurrentItem(item)
            if self.idea_list.count() and self.idea_list.currentItem() is None:
                self.idea_list.setCurrentRow(0)
            if not self.idea_list.count():
                self.current_idea_id = None
                self._clear_editor()
        finally:
            self._loading = False
        item = self.idea_list.currentItem()
        if item is not None:
            self._load_idea(str(item.data(Qt.UserRole)))

    def select_idea(self, idea_id: str) -> None:
        # An idea may be hidden by the current filter; show all so the newly
        # kept idea is always visible immediately.
        if self.filter_status.currentData():
            self.filter_status.setCurrentIndex(0)
        self.refresh(select_id=idea_id)

    def _selection_changed(self, current, previous) -> None:
        if self._loading or current is None:
            return
        self._load_idea(str(current.data(Qt.UserRole)))

    def _load_idea(self, idea_id: str) -> None:
        idea = self.store.get(idea_id)
        if idea is None:
            self._clear_editor()
            return
        self.current_idea_id = idea.idea_id
        self._loading = True
        try:
            self.title.setText(idea.title)
            status_index = self.status.findData(idea.status)
            self.status.setCurrentIndex(max(0, status_index))
            self.notes.setPlainText(idea.notes)
            self.hypotheses.setPlainText("\n".join(idea.hypotheses))
            self.proposed_experiment.setPlainText(idea.proposed_experiment)
            self.modules.setPlainText("\n".join(idea.associated_modules))
            if idea.source_candidate_id:
                query_note = (
                    f"; source query hash={idea.source_query_sha256[:12]}…"
                    if idea.source_query_sha256
                    else ""
                )
                self.source.setText(
                    f"Grow candidate {idea.source_candidate_id}; "
                    f"targets={', '.join(idea.source_target_ids)}{query_note}"
                )
            else:
                self.source.setText("Manual idea.")
            self.save_button.setEnabled(True)
            self.advance_button.setEnabled(idea.status != "Proof Candidate")
            self.delete_button.setEnabled(True)
        finally:
            self._loading = False

    def _clear_editor(self) -> None:
        self.title.clear()
        self.status.setCurrentIndex(0)
        self.notes.clear()
        self.hypotheses.clear()
        self.proposed_experiment.clear()
        self.modules.clear()
        self.source.setText("No idea selected.")
        self.save_button.setEnabled(False)
        self.advance_button.setEnabled(False)
        self.delete_button.setEnabled(False)

    def new_idea(self) -> None:
        idea = self.store.create(title="Untitled Research Idea")
        self.select_idea(idea.idea_id)
        self.title.selectAll()
        self.title.setFocus()

    def save_current(self) -> None:
        if not self.current_idea_id:
            return
        try:
            idea = self.store.update(
                self.current_idea_id,
                title=self.title.text(),
                status=str(self.status.currentData()),
                notes=self.notes.toPlainText(),
                hypotheses=self._parse_lines(self.hypotheses.toPlainText()),
                proposed_experiment=self.proposed_experiment.toPlainText(),
                associated_modules=self._parse_lines(self.modules.toPlainText()),
            )
        except (KeyError, ValueError) as exc:
            QMessageBox.warning(self, "Could not save research idea", str(exc))
            return
        self.refresh(select_id=idea.idea_id)

    def advance_current(self) -> None:
        if not self.current_idea_id:
            return
        try:
            idea = self.store.advance_status(self.current_idea_id)
        except KeyError as exc:
            QMessageBox.warning(self, "Could not advance research idea", str(exc))
            return
        self.refresh(select_id=idea.idea_id)

    def delete_current(self) -> None:
        if not self.current_idea_id:
            return
        idea = self.store.get(self.current_idea_id)
        if idea is None:
            return
        answer = QMessageBox.question(
            self,
            "Delete research idea?",
            f"Delete '{idea.title}' from the local research notebook?\n\n"
            "This does not affect experiments, proofs, or verification evidence.",
        )
        if answer != QMessageBox.Yes:
            return
        self.store.delete(idea.idea_id)
        self.current_idea_id = None
        self.refresh()
