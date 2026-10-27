"""
A checkable deck tree. Checking a deck includes all of its subdecks.
Filtered decks are left out: their cards are counted under their home decks.

(Shared by the Study Day and Trouble Spots tabs.)
"""

from __future__ import annotations

from aqt.qt import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    Qt,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

ID_ROLE = Qt.ItemDataRole.UserRole


class DeckPicker(QWidget):
    def __init__(self, col, selected_ids: list[int], parent=None):
        super().__init__(parent)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.hint = QLabel("Nothing checked = all decks.")
        self.hint.setStyleSheet("color: gray;")

        all_btn = QPushButton("Check all")
        none_btn = QPushButton("Clear")
        all_btn.clicked.connect(lambda: self._set_all(Qt.CheckState.Checked))
        none_btn.clicked.connect(lambda: self._set_all(Qt.CheckState.Unchecked))
        buttons = QHBoxLayout()
        buttons.addWidget(all_btn)
        buttons.addWidget(none_btn)
        buttons.addStretch()
        buttons.addWidget(self.hint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree)
        layout.addLayout(buttons)

        self._build(col, selected_ids)

    def _build(self, col, selected_ids: list[int]) -> None:
        flags = (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsAutoTristate
        )
        items: dict[str, QTreeWidgetItem] = {}
        by_id: dict[int, QTreeWidgetItem] = {}
        decks = col.decks.all_names_and_ids(
            skip_empty_default=True, include_filtered=False
        )
        for deck in sorted(decks, key=lambda d: d.name.split("::")):
            parts = deck.name.split("::")
            parent = items.get("::".join(parts[:-1]))
            item = QTreeWidgetItem(parent or self.tree, [parts[-1]])
            item.setFlags(flags)
            item.setData(0, ID_ROLE, deck.id)
            item.setCheckState(0, Qt.CheckState.Unchecked)
            items[deck.name] = item
            by_id[deck.id] = item

        # Parents first, so a checked parent can't later uncheck its children.
        def depth(item):
            d = 0
            while item.parent():
                item, d = item.parent(), d + 1
            return d

        chosen = [by_id[d] for d in selected_ids if d in by_id]
        for item in sorted(chosen, key=depth):
            item.setCheckState(0, Qt.CheckState.Checked)
            p = item.parent()
            while p:
                p.setExpanded(True)
                p = p.parent()

    def _set_all(self, state) -> None:
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setCheckState(0, state)

    def selected_ids(self) -> list[int]:
        """Topmost checked decks (their subdecks are implied)."""
        out: list[int] = []

        def walk(item):
            state = item.checkState(0)
            if state == Qt.CheckState.Checked:
                out.append(item.data(0, ID_ROLE))
            elif state == Qt.CheckState.PartiallyChecked:
                for i in range(item.childCount()):
                    walk(item.child(i))

        for i in range(self.tree.topLevelItemCount()):
            walk(self.tree.topLevelItem(i))
        return out


def choose_decks(col, selected_ids: list[int], parent=None, title="Choose decks"):
    """Modal picker. Returns the new selection, or None if cancelled."""
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(420, 480)
    picker = DeckPicker(col, selected_ids, dialog)
    box = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    box.accepted.connect(dialog.accept)
    box.rejected.connect(dialog.reject)
    layout = QVBoxLayout(dialog)
    layout.addWidget(picker)
    layout.addWidget(box)
    if dialog.exec():
        return picker.selected_ids()
    return None
