"""Compositor for boolean and boolean-derived operations.

Two slots (``Object`` / ``Tool``) populate every action. Three groups:

- **Classic**: cut, fuse, intersect, fragment, fragment_all. All four
  primitives + the shortcut over every volume.
- **Derived**: imprint, split, self_intersect, xor. These reuse the
  ``Object`` / ``Tool`` slots but call dedicated Session methods that
  set the right gmsh flags or compose multiple OCC calls into a single
  timeline step.
- **Parametric**: section (plane point + normal), hollow (thickness +
  optional open faces). These bring their own inputs because they do
  not fit the two-slot pattern.

Implementation note: every action is dispatched through
``viewer.run_method(<name>, ...)``, which calls ``api.Session.<name>``
and emits ``documentChanged`` so the rest of the viewer (model tree,
scene, history) refreshes automatically. The dock never touches gmsh
directly.
"""
from __future__ import annotations

from ..deps import require_dependencies


# Keys for run_method dispatch — kept in one place so the buttons cannot
# drift from the Session method names.
_CLASSIC_OPS = ("cut", "fuse", "intersect", "fragment")
_DERIVED_OPS = ("imprint", "split", "xor")


class BooleanDock:
    def __init__(self, viewer_session, parent=None) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        QtCore = deps["QtCore"]
        self.viewer = viewer_session
        self._QtWidgets = QtWidgets
        self._QtCore = QtCore

        self.dock = QtWidgets.QDockWidget("Booleans", parent)

        # Wrap the dock body in a QScrollArea — there is enough content
        # now that on smaller screens the parametric section can fall
        # below the fold.
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        self._object_uuids: list[str] = []
        self._tool_uuids: list[str] = []

        hint = QtWidgets.QLabel(
            "1) Select entities in the Model tree "
            "(Ctrl/Shift = multiple).\n"
            "2) Press Add selection on Object or Tool.\n"
            "3) Run the operation."
        )
        hint.setProperty("role", "hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # ── Slots: Object / Tool ────────────────────────────────────
        layout.addWidget(self._titled("Object"))
        self.object_list = QtWidgets.QListWidget()
        self.object_list.setMaximumHeight(110)
        layout.addWidget(self.object_list)
        btns_o = QtWidgets.QHBoxLayout()
        self.btn_add_obj = QtWidgets.QPushButton("Add selection")
        self.btn_clear_obj = QtWidgets.QPushButton("Clear")
        btns_o.addWidget(self.btn_add_obj)
        btns_o.addWidget(self.btn_clear_obj)
        layout.addLayout(btns_o)

        layout.addWidget(self._titled("Tool"))
        self.tool_list = QtWidgets.QListWidget()
        self.tool_list.setMaximumHeight(110)
        layout.addWidget(self.tool_list)
        btns_t = QtWidgets.QHBoxLayout()
        self.btn_add_tool = QtWidgets.QPushButton("Add selection")
        self.btn_clear_tool = QtWidgets.QPushButton("Clear")
        btns_t.addWidget(self.btn_add_tool)
        btns_t.addWidget(self.btn_clear_tool)
        layout.addLayout(btns_t)

        # Flags that the classic primitives consume; the derived ops
        # ignore them (their flags are hard-coded in Session).
        self.chk_remove_obj = QtWidgets.QCheckBox("remove object")
        self.chk_remove_obj.setChecked(True)
        self.chk_remove_tool = QtWidgets.QCheckBox("remove tool")
        self.chk_remove_tool.setChecked(True)
        layout.addWidget(self.chk_remove_obj)
        layout.addWidget(self.chk_remove_tool)

        # ── Classic operations ──────────────────────────────────────
        layout.addWidget(self._titled("Classic"))
        actions = QtWidgets.QGridLayout()
        self.btn_cut = QtWidgets.QPushButton("Cut")
        self.btn_cut.setToolTip("A − B: subtract Tool from Object.")
        self.btn_fuse = QtWidgets.QPushButton("Fuse")
        self.btn_fuse.setToolTip("A ∪ B: union of Object and Tool.")
        self.btn_intersect = QtWidgets.QPushButton("Intersect")
        self.btn_intersect.setToolTip("A ∩ B: keep only the overlap.")
        self.btn_fragment = QtWidgets.QPushButton("Fragment")
        self.btn_fragment.setToolTip(
            "Split Object against Tool, producing conformal interfaces."
        )
        self.btn_fragment_all = QtWidgets.QPushButton("Fragment all (3D)")
        self.btn_fragment_all.setToolTip(
            "Fragment every volume in the model against each other."
        )
        actions.addWidget(self.btn_cut, 0, 0)
        actions.addWidget(self.btn_fuse, 0, 1)
        actions.addWidget(self.btn_intersect, 1, 0)
        actions.addWidget(self.btn_fragment, 1, 1)
        actions.addWidget(self.btn_fragment_all, 2, 0, 1, 2)
        layout.addLayout(actions)

        # ── Derived operations ──────────────────────────────────────
        layout.addWidget(self._titled("Derived"))
        derived = QtWidgets.QGridLayout()
        self.btn_imprint = QtWidgets.QPushButton("Imprint")
        self.btn_imprint.setToolTip(
            "Mark shared interfaces without consuming Object or Tool. "
            "Useful for tie / cohesive contact (FEM)."
        )
        self.btn_split = QtWidgets.QPushButton("Split")
        self.btn_split.setToolTip(
            "Cut Object with Tool and keep every resulting piece."
        )
        self.btn_xor = QtWidgets.QPushButton("XOR")
        self.btn_xor.setToolTip(
            "Symmetric difference: (Object ∪ Tool) \\ (Object ∩ Tool)."
        )
        self.btn_self_intersect = QtWidgets.QPushButton("Self-intersect")
        self.btn_self_intersect.setToolTip(
            "Resolve auto-intersections inside the Object set "
            "(Tool is ignored)."
        )
        derived.addWidget(self.btn_imprint, 0, 0)
        derived.addWidget(self.btn_split, 0, 1)
        derived.addWidget(self.btn_xor, 1, 0)
        derived.addWidget(self.btn_self_intersect, 1, 1)
        layout.addLayout(derived)

        # ── Parametric operations: Section ──────────────────────────
        layout.addWidget(self._titled("Section (plane cut)"))
        section_form = QtWidgets.QFormLayout()
        section_form.setContentsMargins(0, 0, 0, 0)

        self.section_point = self._xyz_row(default=(0.0, 0.0, 0.0))
        section_form.addRow("point:", self.section_point["widget"])

        self.section_normal = self._xyz_row(default=(0.0, 0.0, 1.0))
        section_form.addRow("normal:", self.section_normal["widget"])

        # Auto-size by default; user can override.
        extent_row = QtWidgets.QHBoxLayout()
        extent_row.setContentsMargins(0, 0, 0, 0)
        self.chk_section_auto = QtWidgets.QCheckBox("auto")
        self.chk_section_auto.setChecked(True)
        self.spin_section_extent = QtWidgets.QDoubleSpinBox()
        self.spin_section_extent.setDecimals(4)
        self.spin_section_extent.setRange(0.0, 1.0e9)
        self.spin_section_extent.setSingleStep(1.0)
        self.spin_section_extent.setEnabled(False)
        self.chk_section_auto.toggled.connect(
            lambda v: self.spin_section_extent.setEnabled(not v)
        )
        extent_row.addWidget(self.chk_section_auto)
        extent_row.addWidget(self.spin_section_extent)
        section_form.addRow("extent:", _wrap(extent_row, QtWidgets))

        layout.addLayout(section_form)
        self.btn_section = QtWidgets.QPushButton("Section selected volumes")
        self.btn_section.setToolTip(
            "Slice the volumes currently in the Object slot with the "
            "plane defined by point + normal. Volumes are preserved; "
            "the cross section appears as new 2D surfaces."
        )
        layout.addWidget(self.btn_section)

        # ── Parametric operations: Hollow ───────────────────────────
        layout.addWidget(self._titled("Hollow (shell)"))
        hollow_form = QtWidgets.QFormLayout()
        hollow_form.setContentsMargins(0, 0, 0, 0)
        self.spin_hollow_thickness = QtWidgets.QDoubleSpinBox()
        self.spin_hollow_thickness.setDecimals(6)
        self.spin_hollow_thickness.setRange(-1.0e6, 1.0e6)
        self.spin_hollow_thickness.setValue(-1.0)
        self.spin_hollow_thickness.setSingleStep(0.1)
        hollow_form.addRow("thickness:", self.spin_hollow_thickness)
        layout.addLayout(hollow_form)

        hint_hollow = QtWidgets.QLabel(
            "Object = volumes to shell. Tool (optional) = faces to "
            "leave open. Negative thickness offsets inward, positive "
            "offsets outward."
        )
        hint_hollow.setProperty("role", "hint")
        hint_hollow.setWordWrap(True)
        layout.addWidget(hint_hollow)

        self.btn_hollow = QtWidgets.QPushButton("Hollow selected volumes")
        self.btn_hollow.setToolTip(
            "Replace each volume in the Object slot with a thick shell. "
            "Faces in the Tool slot (if any) become the open sides."
        )
        layout.addWidget(self.btn_hollow)

        layout.addStretch(1)
        scroll.setWidget(widget)
        self.dock.setWidget(scroll)

        # ── Wiring ──────────────────────────────────────────────────
        self.btn_add_obj.clicked.connect(
            lambda: self._add_selection(self._object_uuids, self.object_list)
        )
        self.btn_clear_obj.clicked.connect(
            lambda: self._clear(self._object_uuids, self.object_list)
        )
        self.btn_add_tool.clicked.connect(
            lambda: self._add_selection(self._tool_uuids, self.tool_list)
        )
        self.btn_clear_tool.clicked.connect(
            lambda: self._clear(self._tool_uuids, self.tool_list)
        )

        # Classic — they share remove_object / remove_tool flags.
        self.btn_cut.clicked.connect(lambda: self._run_classic("cut"))
        self.btn_fuse.clicked.connect(lambda: self._run_classic("fuse"))
        self.btn_intersect.clicked.connect(
            lambda: self._run_classic("intersect")
        )
        self.btn_fragment.clicked.connect(
            lambda: self._run_classic("fragment")
        )
        self.btn_fragment_all.clicked.connect(
            lambda: self.viewer.run_method("fragment_all", dim=3)
        )

        # Derived — Session handles the flag semantics internally.
        self.btn_imprint.clicked.connect(
            lambda: self._run_derived("imprint", needs_tool=True)
        )
        self.btn_split.clicked.connect(
            lambda: self._run_derived("split", needs_tool=True)
        )
        self.btn_xor.clicked.connect(
            lambda: self._run_derived("xor", needs_tool=True)
        )
        self.btn_self_intersect.clicked.connect(self._run_self_intersect)

        # Parametric
        self.btn_section.clicked.connect(self._run_section)
        self.btn_hollow.clicked.connect(self._run_hollow)

        viewer_session.documentChanged.connect(self._purge_invalid)

    # ── helpers ─────────────────────────────────────────────────────

    def _titled(self, text: str):
        QtWidgets = self._QtWidgets
        lab = QtWidgets.QLabel(text)
        lab.setProperty("role", "title")
        return lab

    def _xyz_row(self, *, default: tuple[float, float, float]) -> dict:
        """Build a horizontal 3-spinbox row for entering a point or
        a normal vector. Returns a dict with the wrapping widget and
        the three QDoubleSpinBox so callers can read values back."""
        QtWidgets = self._QtWidgets
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        spins: list = []
        for axis, value in zip("xyz", default):
            label = QtWidgets.QLabel(axis)
            label.setProperty("role", "hint")
            row.addWidget(label)
            spin = QtWidgets.QDoubleSpinBox()
            spin.setDecimals(4)
            spin.setRange(-1.0e9, 1.0e9)
            spin.setSingleStep(0.1)
            spin.setValue(float(value))
            spin.setMinimumWidth(64)
            row.addWidget(spin)
            spins.append(spin)
        return {"widget": _wrap(row, QtWidgets), "spins": spins}

    def _xyz_value(self, row: dict) -> tuple[float, float, float]:
        spins = row["spins"]
        return (
            float(spins[0].value()),
            float(spins[1].value()),
            float(spins[2].value()),
        )

    def _add_selection(self, store: list, list_widget) -> None:
        ents = self.viewer.get_selected_entities()
        if not ents:
            self.viewer.statusMessage.emit(
                "Select entities in the Model tree or in the scene."
            )
            return
        added = 0
        for e in ents:
            if e.uuid in store:
                continue
            store.append(e.uuid)
            list_widget.addItem(f"({e.dim},{e.tag}) {e.name or e.kind}")
            added += 1
        self._publish_slots()
        self.viewer.clear_multi_selection()
        self.viewer.statusMessage.emit(
            f"+{added} entities ({len(store)} total)."
        )

    def _clear(self, store: list, list_widget) -> None:
        store.clear()
        list_widget.clear()
        self._publish_slots()

    def _publish_slots(self) -> None:
        """Reflect current uuids in the viewer so the blue / orange
        tint is applied in the scene."""
        self.viewer.set_boolean_object(self._object_uuids)
        self.viewer.set_boolean_tool(self._tool_uuids)

    # ── action dispatch ─────────────────────────────────────────────

    def _require_object(self, op_label: str) -> bool:
        if not self._object_uuids:
            self.viewer.statusMessage.emit(
                f"{op_label}: define at least one Object before running."
            )
            return False
        return True

    def _reset_slots(self) -> None:
        self._object_uuids.clear()
        self._tool_uuids.clear()
        self.object_list.clear()
        self.tool_list.clear()
        # run_method already emits documentChanged which clears the
        # viewer-side boolean slots; we only need to refresh dock visuals.

    def _run_classic(self, kind: str) -> None:
        if not self._require_object(kind):
            return
        kwargs = dict(
            object=tuple(self._object_uuids),
            tool=tuple(self._tool_uuids),
            remove_object=self.chk_remove_obj.isChecked(),
            remove_tool=self.chk_remove_tool.isChecked(),
        )
        self.viewer.run_method(kind, **kwargs)
        self._reset_slots()

    def _run_derived(self, kind: str, *, needs_tool: bool) -> None:
        if not self._require_object(kind):
            return
        if needs_tool and not self._tool_uuids:
            self.viewer.statusMessage.emit(
                f"{kind}: also define at least one Tool entity."
            )
            return
        kwargs = dict(
            object=tuple(self._object_uuids),
            tool=tuple(self._tool_uuids),
        )
        self.viewer.run_method(kind, **kwargs)
        self._reset_slots()

    def _run_self_intersect(self) -> None:
        if not self._require_object("self_intersect"):
            return
        # Self-intersect ignores Tool; the user only needs Object.
        self.viewer.run_method(
            "self_intersect",
            object=tuple(self._object_uuids),
        )
        self._reset_slots()

    def _run_section(self) -> None:
        if not self._require_object("section"):
            return
        # Only volumes (dim=3) make sense for a plane slice.
        doc = self.viewer.api.document
        volume_uuids = []
        for uuid in self._object_uuids:
            e = doc.find_by_uuid(uuid)
            if e is not None and e.dim == 3:
                volume_uuids.append(uuid)
        if not volume_uuids:
            self.viewer.statusMessage.emit(
                "section: the Object slot has no volume (dim=3)."
            )
            return
        extent = (
            None if self.chk_section_auto.isChecked()
            else float(self.spin_section_extent.value())
        )
        self.viewer.run_method(
            "section",
            volume=tuple(volume_uuids),
            point=self._xyz_value(self.section_point),
            normal=self._xyz_value(self.section_normal),
            extent=extent,
        )
        self._reset_slots()

    def _run_hollow(self) -> None:
        if not self._require_object("hollow"):
            return
        doc = self.viewer.api.document
        volume_uuids = []
        for uuid in self._object_uuids:
            e = doc.find_by_uuid(uuid)
            if e is not None and e.dim == 3:
                volume_uuids.append(uuid)
        if not volume_uuids:
            self.viewer.statusMessage.emit(
                "hollow: the Object slot has no volume (dim=3)."
            )
            return
        # Tool slot, if any, lists faces to leave open.
        face_uuids = []
        for uuid in self._tool_uuids:
            e = doc.find_by_uuid(uuid)
            if e is not None and e.dim == 2:
                face_uuids.append(uuid)
        thickness = float(self.spin_hollow_thickness.value())
        if thickness == 0.0:
            self.viewer.statusMessage.emit("hollow: thickness must be non-zero.")
            return
        self.viewer.run_method(
            "hollow",
            volume=tuple(volume_uuids),
            thickness=thickness,
            open_faces=tuple(face_uuids),
        )
        self._reset_slots()

    def _purge_invalid(self) -> None:
        doc = self.viewer.api.document
        changed = False
        for store, widget in ((self._object_uuids, self.object_list),
                              (self._tool_uuids, self.tool_list)):
            valid = [u for u in store if doc.find_by_uuid(u) is not None]
            if valid != store:
                store[:] = valid
                widget.clear()
                for u in valid:
                    e = doc.find_by_uuid(u)
                    widget.addItem(f"({e.dim},{e.tag}) {e.name or e.kind}")
                changed = True
        if changed:
            self._publish_slots()


def _wrap(layout, QtWidgets):
    w = QtWidgets.QWidget()
    w.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)
    return w
