import subprocess
import logging
import os
from pathlib import Path
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("aia_weaver")

class ThumbnailManager:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        os.makedirs(os.path.expanduser("~/.cache/aether/thumbnails"), exist_ok=True)
        self.max_size_bytes = 500 * 1024 * 1024
        self.target_size_bytes = 400 * 1024 * 1024
        self.executor = ThreadPoolExecutor(max_workers=2)

    def generate_thumbnail(self, file_path: Path, file_hash: str) -> str | None:
        ext = file_path.suffix.lower()
        if ext not in ('.png', '.jpg', '.jpeg', '.webp'):
            if ext == '.pdf':
                thumb_path = self.cache_dir / f"{file_hash}.webp"
                if thumb_path.exists() and os.path.getsize(str(thumb_path)) > 0:
                    thumb_path.touch()
                    return str(thumb_path)
                try:
                    result = subprocess.run(
                        [
                            "convert", "-density", "150", "-colorspace", "sRGB", 
                            f"{file_path}[0]", "-background", "white", "-flatten", 
                            "-alpha", "remove", "-resize", "400x400>", str(thumb_path)
                        ],
                        check=True, capture_output=True
                    )
                    if thumb_path.exists() and os.path.getsize(str(thumb_path)) > 0:
                        logger.info(f"Successfully generated PDF thumbnail to disk: {thumb_path}")
                        return str(thumb_path)
                except subprocess.CalledProcessError as e:
                    logger.error(f"Thumbnail generation failed: {e.stderr.decode('utf-8', errors='ignore')}")
                except Exception as e:
                    logger.error(f"Thumbnail generation failed: {e}")
            return None

        thumb_path = self.cache_dir / f"{file_hash}.webp"
        if thumb_path.exists() and os.path.getsize(str(thumb_path)) > 0:
            thumb_path.touch()
            return str(thumb_path)
        try:
            with Image.open(file_path) as img:
                img.thumbnail((400, 400))
                img = img.convert("RGBA")
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                bg.save(thumb_path, "WEBP", quality=85)
            if thumb_path.exists() and os.path.getsize(str(thumb_path)) > 0:
                logger.info(f"Successfully generated Image thumbnail to disk: {thumb_path}")
                return str(thumb_path)
            return None
        except Exception as e:
            logger.error(f"Thumbnail generation failed: {e}")
            return None

    def enforce_cache_limits(self):
        try:
            files = []
            total_size = 0
            for p in self.cache_dir.glob("*"):
                if p.is_file():
                    stat = p.stat()
                    total_size += stat.st_size
                    files.append((p, stat.st_atime, stat.st_size))

            if total_size > self.max_size_bytes:
                files.sort(key=lambda x: x[1])  # Sort by atime ascending
                for p, atime, size in files:
                    p.unlink(missing_ok=True)
                    total_size -= size
                    if total_size <= self.target_size_bytes:
                        break
        except Exception as e:
            logger.error(f"Error enforcing cache limits: {e}")
