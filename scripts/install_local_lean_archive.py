from __future__ import annotations
import argparse, shutil, tarfile, zipfile, os
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description="Install an uploaded Lean 4 archive into CACE's local formal toolchain directory.")
    p.add_argument("archive")
    p.add_argument("--dest",default=None)
    ns=p.parse_args()

    archive=Path(ns.archive).resolve()
    if not archive.exists():
        raise SystemExit(f"archive not found: {archive}")

    project=Path(__file__).resolve().parents[1]
    dest=Path(ns.dest).resolve() if ns.dest else project/"formal"/"toolchain"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    name=archive.name.lower()
    if name.endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            z.extractall(dest)
    elif any(name.endswith(s) for s in (".tar.gz",".tgz",".tar.xz",".txz",".tar.zst",".tar")):
        with tarfile.open(archive) as t:
            t.extractall(dest,filter="data")
    else:
        raise SystemExit("supported archive formats: zip, tar, tar.gz/tgz, tar.xz/txz, tar.zst")

    candidates=[]
    for q in dest.rglob("lean"):
        if q.is_file() and q.parent.name=="bin":
            lake=q.parent/"lake"
            if lake.exists():
                candidates.append(q.parent)
    if not candidates:
        raise SystemExit("archive extracted, but no bin/lean + bin/lake pair was found")

    chosen=sorted(candidates,key=lambda x:len(x.parts))[0]
    print(f"CACE_LEAN_BIN={chosen}")
    print(f"lean={chosen/'lean'}")
    print(f"lake={chosen/'lake'}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
