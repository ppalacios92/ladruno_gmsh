"""Launch the Qt viewer on a STEP file from the geometria repo."""
from pathlib import Path

from ladruno_gmsh import open_model


def main() -> None:
    target = Path(r"C:\Dropbox\01. Brain\11. GitHub\geometria\01_ATLAS.stp")
    if not target.exists():
        raise SystemExit(f"Does not exist: {target}")

    session = open_model(target, units="mm", tolerance="auto")
    print(session)
    session.show()  # blocks until the window is closed


if __name__ == "__main__":
    main()
