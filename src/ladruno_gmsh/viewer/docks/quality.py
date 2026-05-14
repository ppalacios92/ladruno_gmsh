"""Quality histograms and threshold filtering."""
from __future__ import annotations

from ..deps import require_dependencies


_METRICS = ["minSICN", "minSIGE", "minSJ", "gamma", "eta",
            "innerRadius", "outerRadius", "volume"]


class QualityDock:
    def __init__(self, viewer_session, parent=None) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        self.viewer = viewer_session

        self.dock = QtWidgets.QDockWidget("Quality", parent)
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        self.combo_metric = QtWidgets.QComboBox()
        self.combo_metric.addItems(_METRICS)
        layout.addRow("metric:", self.combo_metric)

        self.spin_threshold = QtWidgets.QDoubleSpinBox()
        self.spin_threshold.setDecimals(4)
        self.spin_threshold.setRange(-1.0, 10.0)
        self.spin_threshold.setSingleStep(0.05)
        self.spin_threshold.setValue(0.1)
        layout.addRow("threshold:", self.spin_threshold)

        self.btn_compute = QtWidgets.QPushButton("Compute")
        layout.addRow("", self.btn_compute)

        self.lbl_stats = QtWidgets.QLabel("min/median/max/n: -")
        self.lbl_stats.setWordWrap(True)
        layout.addRow(self.lbl_stats)

        self.lbl_below = QtWidgets.QLabel("Elements below threshold: -")
        layout.addRow(self.lbl_below)

        self.hist_view = QtWidgets.QPlainTextEdit()
        self.hist_view.setReadOnly(True)
        self.hist_view.setMaximumHeight(160)
        self.hist_view.setStyleSheet("font-family: Consolas, monospace;")
        layout.addRow(self.hist_view)

        self.dock.setWidget(widget)
        self.btn_compute.clicked.connect(self._compute)

    def _compute(self) -> None:
        metric = self.combo_metric.currentText()
        self.viewer.state.quality_metric = metric
        try:
            q = self.viewer.api.diagnostics.quality(metric=metric)
        except Exception as exc:
            self.viewer.statusMessage.emit(f"quality failed: {exc}")
            return
        if q.count == 0:
            self.lbl_stats.setText("min/median/max/n: 0 (no mesh)")
            self.lbl_below.setText("Elements below threshold: -")
            self.hist_view.setPlainText("(generate the mesh first)")
            return

        thr = self.spin_threshold.value()
        below = q.count_below(thr)
        self.lbl_stats.setText(
            f"min={q.min:.4f}  median={q.median:.4f}  "
            f"max={q.max:.4f}  n={q.count}"
        )
        self.lbl_below.setText(f"Elements with {metric} < {thr:g}: {below}")

        counts, edges = q.histogram(bins=20)
        max_count = int(counts.max()) if counts.size else 0
        if max_count == 0:
            self.hist_view.setPlainText("(no data)")
            return
        lines = []
        for c, lo, hi in zip(counts, edges[:-1], edges[1:]):
            bar = "#" * int(40 * (c / max_count))
            lines.append(f"[{lo:8.4f}, {hi:8.4f}) {int(c):>6d}  {bar}")
        self.hist_view.setPlainText("\n".join(lines))
