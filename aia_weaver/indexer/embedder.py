import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Optional
from fastembed import TextEmbedding

logger = logging.getLogger("aia_weaver.embedder")

# Global worker instance for ProcessPoolExecutor
_embedding_model: Optional[TextEmbedding] = None


def _init_worker():
    """Initializes the fastembed model once per process pool worker."""
    global _embedding_model
    # BAAI/bge-small-en-v1.5 generates 384-dim vectors efficiently on CPU
    _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")


def _generate_embedding_sync(text: str) -> list[float]:
    """Synchronous CPU worker task that runs ONNX embedding generation."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

    # fastembed returns a generator of numpy arrays; convert first result to list
    embeddings = list(_embedding_model.embed([text]))
    return embeddings[0].tolist()


class LocalEmbedder:
    def __init__(self, max_workers: int = 2):
        # Offload heavy math to separate CPU processes to keep main loop responsive
        self.executor = ProcessPoolExecutor(
            max_workers=max_workers, initializer=_init_worker
        )

    async def embed_text(self, text: str) -> list[float]:
        """Asynchronously dispatches text embedding calculation to the process pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self.executor, _generate_embedding_sync, text
        )

    async def embed_file(self, file_path: str) -> Optional[list[float]]:
        """Reads local text file contents and calculates its vector embedding."""
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            logger.warning(f"File not found for embedding: {file_path}")
            return None

        # Basic guard: Don't read massive binary files
        if path.stat().st_size > 2 * 1024 * 1024:  # Skip files > 2MB
            logger.warning(f"File too large for fast embedding (>2MB): {file_path}")
            return None

        try:
            # Non-blocking file reading
            content = await asyncio.to_thread(
                path.read_text, encoding="utf-8", errors="ignore"
            )
            if not content.strip():
                logger.debug(f"File empty, skipping embedding: {file_path}")
                return None

            # Generate vector
            vector = await self.embed_text(content)
            logger.info(
                f"Generated {len(vector)}-dim vector embedding for: {path.name}"
            )
            return vector

        except Exception as e:
            logger.error(f"Failed to generate embedding for {file_path}: {e}")
            return None

    def close(self) -> None:
        """Gracefully shuts down the background process pool without noisy tracebacks."""
        if self.executor:
            # wait=False prevents main process from blocking indefinitely on exit
            # cancel_futures=True drops any queued tasks
            self.executor.shutdown(wait=False, cancel_futures=True)
            logger.info("LocalEmbedder process pool executor closed.")