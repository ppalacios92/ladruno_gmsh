"""Full smoke test: pipeline + diagnostics over files from the geometria repo."""
from pathlib import Path

from ladruno_gmsh import open_model


REPO = Path(r"C:\Dropbox\01. Brain\11. GitHub\geometria")


def show(label, value):
    print(f"  {label:<30} {value}")


def main() -> None:
    path = REPO / "01.step"
    if not path.exists():
        print("fixture not available")
        return

    print(f"=== Loading {path.name} ===")
    with open_model(path, units="mm") as s:
        show("entities", len(s.entities))
        show("by_dim", {dim: sum(1 for e in s.entities if e.dim == dim)
                       for dim in (0, 1, 2, 3)})
        show("bbox_diag (mm)", f"{s.document.bbox_diagonal():.2f}")
        show("tolerance.linear", f"{s.tolerance.linear:.3e}")

        print("\n=== Heal + remove_duplicates + fragment_all ===")
        s.heal(make_solids=True)
        s.remove_all_duplicates()
        if len(s.volumes) > 1:
            s.fragment_all(dim=3)
            s.remove_all_duplicates()
        show("entities after cleanup", len(s.entities))
        show("volumes",  len(s.volumes))
        show("surfaces", len(s.surfaces))

        print("\n=== Mesh 3D ===")
        target = s.tolerance.linear * 1000.0
        s.mesh(size=target, dim=3, order=1, algorithm_3d="HXT")
        m = s.mesh_snapshot
        show("nodes",        m.n_nodes)
        show("elements",     m.n_elements)
        show("by type",      dict(m.elements_by_type))
        show("max_dim",      m.max_dim)

        print("\n=== Diagnostics ===")
        rep = s.diagnostics.report()
        print(rep.as_markdown())

        out_step = REPO.parent / "ladruno_gmsh" / "tmp_clean.step"
        out_msh = REPO.parent / "ladruno_gmsh" / "tmp_clean.msh"
        s.export(out_step)
        s.export(out_msh)
        print(f"\nexported: {out_step.name} and {out_msh.name}")


if __name__ == "__main__":
    main()
