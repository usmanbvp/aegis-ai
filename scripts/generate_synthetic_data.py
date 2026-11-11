from __future__ import annotations

from pathlib import Path

from app.synthetic_data import write_dataset


if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parents[1] / "data"
    paths = write_dataset(output_dir)
    print("Synthetic dataset generated:")
    for name, path in paths.items():
        print(f"- {name}: {path}")
