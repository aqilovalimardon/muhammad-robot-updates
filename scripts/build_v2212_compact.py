#!/usr/bin/env python3
"""v2.2.12: compress v2.2.11 animation archive to fit existing <=100-entry validator.

The stable on-device updater correctly refuses releases with more than 100 ZIP
entries. v2.2.11 accidentally has 184 entries (144 living + 36 classic + 4 code).
This release retains 9 independently addressable expressions with 8 frames each
(72 images) and 8 classic backup frames, for 84 entries. No update bypass.
"""
from pathlib import Path
import hashlib, json, sys, zipfile

SOURCE_DIGEST="d56ed185d77f1095b50c4f46881bf15698aa85bd96f85eeca569eea38e685806"
FRAME_COUNT=8
EXPRESSIONS=9
CLASSIC_SELECTED=[0,4,9,13,18,22,27,31]
OLD_LOOKUP="index=(variant*16+(self.t//2)%16)%len(self.frames)"
NEW_LOOKUP="index=(variant*8+(self.t//2)%8)%len(self.frames)"
def build(src,dest):
    src=Path(src);dest=Path(dest)
    if hashlib.sha256(src.read_bytes()).hexdigest()!=SOURCE_DIGEST:
        raise ValueError("Source must be the exact immutable v2.2.11 release")
    dest.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(src) as archive:
        if archive.testzip() is not None: raise ValueError("Source archive corrupted")
        names=archive.namelist()
        if len(names)!=184 or len(set(names))!=len(names):
            raise ValueError("Unexpected source archive layout")
        normal={p for p in names if not (p.startswith("app/assets/frame_") or p.startswith("app/assets_classic/frame_"))}
        if "app/robot_app.py" not in normal or "app/robot_core.py" not in normal:
            raise ValueError("Required app files missing")
        if len(normal)!=4:
            raise ValueError("Unexpected count of non-frame files: "+str(len(normal)))
        payload={}
        # Copy non-animation code unchanged except explicit version/index correction.
        for path in sorted(normal):
            raw=archive.read(path)
            if path=="app/robot_app.py":
                code=raw.decode("utf-8")
                if code.count(OLD_LOOKUP)!=1:
                    raise ValueError("Source gaze mapping not found")
                code=code.replace(OLD_LOOKUP,NEW_LOOKUP)
                compile(code,path,"exec")
                raw=code.encode("utf-8")
            elif path=="app/robot_core.py":
                code=raw.decode("utf-8")
                old="APP_VERSION = '2.2.11'"
                if code.count(old)!=1:raise ValueError("Unexpected source version")
                code=code.replace(old,"APP_VERSION = '2.2.12'")
                compile(code,path,"exec")
                raw=code.encode("utf-8")
            payload[path]=raw

        for expression in range(EXPRESSIONS):
            for k in range(FRAME_COUNT):
                name=f"app/assets/frame_{expression*FRAME_COUNT+k:03d}.png"
                source=f"app/assets/frame_{expression*16+k*2:03d}.png"
                if source not in names:
                    raise ValueError("Missing animation keyframe "+source)
                payload[name]=archive.read(source)

        for i,k in enumerate(CLASSIC_SELECTED):
            source=f"app/assets_classic/frame_{k:02d}.png"
            target=f"app/assets_classic/frame_{i:02d}.png"
            if source not in names:raise ValueError("Missing classic keyframe "+source)
            payload[target]=archive.read(source)

    if len(payload)!=84 or len(set(payload))!=len(payload):
        raise ValueError(f"Package must contain 84 unique entries, got {len(payload)}")
    if any(not p.startswith("app/") or ".." in Path(p).parts for p in payload):
        raise ValueError("Unsafe ZIP path")
    with zipfile.ZipFile(dest,"w",compression=zipfile.ZIP_DEFLATED) as out:
        for path,data in sorted(payload.items()):
            out.writestr(path,data)
    with zipfile.ZipFile(dest) as z:
        if z.testzip() is not None or len(z.infolist())>100:
            raise ValueError("Failed existing device ZIP limit")
        assert len(z.namelist())==84
        assert b"variant*8" in z.read("app/robot_app.py")
        assert b"2.2.12" in z.read("app/robot_core.py")
    manifest={"version":"2.2.12","zip":dest.name,
              "sha256":hashlib.sha256(dest.read_bytes()).hexdigest()}
    (dest.parent/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print("PASS: compact package",len(payload),"entries, exact SHA and existing on-device validator compatible",json.dumps(manifest))
if __name__=="__main__":
    if len(sys.argv)!=3:
        raise SystemExit("Usage: build_v2212_compact.py v2211.zip output.zip")
    build(sys.argv[1],sys.argv[2])
