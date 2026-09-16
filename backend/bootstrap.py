import time

from backend.config import settings
from backend.rag import ingest
from backend.seed import seed

if __name__ == "__main__":
    settings().validate_runtime()
    if settings().seed_demo:
        seed()
    for attempt in range(5):
        try:
            print(f"Indexed {ingest()} knowledge documents")
            break
        except Exception:
            if attempt == 4:
                raise
            time.sleep(min(10, 2**attempt))
