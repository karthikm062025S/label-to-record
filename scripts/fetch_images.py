"""Phase 1: download each manifest image once (PLAN.md 3.1).

  python scripts/fetch_images.py

data/images/<gbifID>.jpg (gitignored). A file over 7 MB is downscaled with Pillow (longest side 3000 px) into
data/images_small/, and the model gets the small one. data/image_log.csv records what is sent per gbifID:
file, bytes, width, height, sha256, plus the source URL. Opens no curated field; only the URL.
"""
import struct

from common import DATA, http_get, load_manifest, sha256_bytes, write_csv

MAX_BYTES = 7 * 1024 * 1024
LONG_SIDE = 3000


def jpeg_size(b):
    """(width, height) from the first SOF marker of a JPEG, stdlib only."""
    i = 2
    while i < len(b) - 9:
        if b[i] != 0xFF:
            i += 1
            continue
        marker = b[i + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h, w = struct.unpack(">HH", b[i + 5:i + 9])
            return w, h
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        i += 2 + struct.unpack(">H", b[i + 2:i + 4])[0]
    return None, None


def downscale(src, dst):
    from PIL import Image  # only needed for files over 7 MB
    with Image.open(src) as im:
        im.thumbnail((LONG_SIDE, LONG_SIDE))
        im.convert("RGB").save(dst, "JPEG", quality=90)


def image_for(gbif_id):
    """Path of the file the model is sent for this record."""
    small = DATA / "images_small" / f"{gbif_id}.jpg"
    return small if small.exists() else DATA / "images" / f"{gbif_id}.jpg"


def main():
    (DATA / "images").mkdir(parents=True, exist_ok=True)
    log = []
    for row in load_manifest():
        g, url = row["gbifID"], row["image_url"]
        path = DATA / "images" / f"{g}.jpg"
        if not path.exists():
            status, headers, body = http_get(url, timeout=120)
            if status != 200:
                raise RuntimeError(f"{g}: HTTP {status} for {url}")
            path.write_bytes(body)
        if path.stat().st_size > MAX_BYTES and not (DATA / "images_small" / f"{g}.jpg").exists():
            (DATA / "images_small").mkdir(exist_ok=True)
            downscale(path, DATA / "images_small" / f"{g}.jpg")
        sent = image_for(g)
        b = sent.read_bytes()
        w, h = jpeg_size(b)
        log.append({"gbifID": g, "file_sent": sent.relative_to(DATA.parent).as_posix(), "bytes": len(b),
                    "width": w, "height": h, "sha256": sha256_bytes(b), "original_bytes": path.stat().st_size,
                    "image_url": url})
        print(f"{len(log):3} {g} {len(b):>9} bytes {w}x{h}")
    write_csv(DATA / "image_log.csv", log, list(log[0].keys()))
    print(f"{len(log)} images; {sum(1 for x in log if 'images_small' in x['file_sent'])} downscaled")


if __name__ == "__main__":
    main()
