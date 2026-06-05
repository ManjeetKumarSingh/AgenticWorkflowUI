import json
import os
from datetime import timedelta
from typing import Optional

from utils.loggers import logger

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CHAT_TTL = int(os.getenv("REDIS_CHAT_TTL", str(int(timedelta(days=7).total_seconds()))))
WORKFLOW_TTL = int(os.getenv("REDIS_WORKFLOW_TTL", str(int(timedelta(days=7).total_seconds()))))

try:
    import redis as _redis

    class _RedisClient:
        def __init__(self):
            self._client = None
            self._ok = False
            self._connect()

        def _connect(self):
            try:
                self._client = _redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=2, socket_connect_timeout=2)
                self._client.ping()
                self._ok = True
                info = self._client.info("server")
                redis_version = info.get("redis_version", "unknown")
                db_index = REDIS_URL.rstrip("/").split("/")[-1] if "/" in REDIS_URL.rstrip("/") else "0"
                logger.info("redis_client | 🔌 Connected to Redis v%s at %s (db=%s, socket_timeout=2s, decode_responses=True)", redis_version, REDIS_URL, db_index)
            except Exception as exc:
                self._ok = False
                self._client = None
                logger.warning("redis_client | Redis not available at %s — %s. Chat history will NOT be persisted. Start Redis with: redis-server", REDIS_URL, exc)

        @property
        def enabled(self) -> bool:
            return self._ok

        def _k(self, username: str, suffix: str) -> str:
            return f"user:{username}:{suffix}"

        def save_chat_history(self, username: str, history: list):
            if not self._ok or not username:
                logger.warning("redis_client | ❌ Chat NOT saved — Redis unavailable (ok=%s, user='%s')", self._ok, username)
                return
            try:
                key = self._k(username, "chat_history")
                msg_count = len(history)
                self._client.setex(key, CHAT_TTL, json.dumps(history, default=str))
                logger.info("redis_client | ✅ Saved %d messages to %s (TTL=%ds)", msg_count, key, CHAT_TTL)
            except Exception as exc:
                logger.error("redis_client | Failed to save chat_history for %s: %s", username, exc)

        def load_chat_history(self, username: str) -> list:
            if not self._ok or not username:
                logger.warning("redis_client | ❌ Chat NOT loaded — Redis unavailable (ok=%s, user='%s')", self._ok, username)
                return []
            try:
                key = self._k(username, "chat_history")
                data = self._client.get(key)
                if data:
                    history = json.loads(data)
                    logger.info("redis_client | ✅ Loaded %d messages from %s", len(history), key)
                    return history
                else:
                    logger.info("redis_client | No chat history found at %s (first login)", key)
                    return []
            except Exception as exc:
                logger.error("redis_client | Failed to load chat_history for %s: %s", username, exc)
                return []

        def save_last_workflow(self, username: str, workflow: dict):
            if not self._ok or not username:
                logger.warning("redis_client | ❌ Workflow NOT saved — Redis unavailable")
                return
            try:
                key = self._k(username, "last_workflow")
                wf_id = workflow.get("workflow_id", "unknown")
                self._client.setex(key, WORKFLOW_TTL, json.dumps(workflow, default=str))
                logger.info("redis_client | ✅ Saved workflow %s to %s (TTL=%ds)", wf_id, key, WORKFLOW_TTL)
            except Exception as exc:
                logger.error("redis_client | Failed to save workflow for %s: %s", username, exc)

        def load_last_workflow(self, username: str) -> Optional[dict]:
            if not self._ok or not username:
                logger.warning("redis_client | ❌ Workflow NOT loaded — Redis unavailable")
                return None
            try:
                key = self._k(username, "last_workflow")
                data = self._client.get(key)
                if data:
                    wf = json.loads(data)
                    logger.info("redis_client | ✅ Loaded workflow %s from %s", wf.get("workflow_id", "unknown"), key)
                    return wf
                else:
                    logger.info("redis_client | No workflow found at %s", key)
                    return None
            except Exception as exc:
                logger.error("redis_client | Failed to load workflow for %s: %s", username, exc)
                return None

        def save_last_workflow_id(self, username: str, wf_id: str):
            if not self._ok or not username:
                logger.warning("redis_client | ❌ Workflow ID NOT saved — Redis unavailable")
                return
            try:
                key = self._k(username, "last_workflow_id")
                self._client.setex(key, WORKFLOW_TTL, wf_id)
                logger.info("redis_client | ✅ Saved workflow_id %s to %s", wf_id, key)
            except Exception as exc:
                logger.error("redis_client | Failed to save workflow_id for %s: %s", username, exc)

        def load_last_workflow_id(self, username: str) -> Optional[str]:
            if not self._ok or not username:
                logger.warning("redis_client | ❌ Workflow ID NOT loaded — Redis unavailable")
                return None
            try:
                key = self._k(username, "last_workflow_id")
                data = self._client.get(key)
                if data:
                    logger.info("redis_client | ✅ Loaded workflow_id %s from %s", data, key)
                    return data
                else:
                    logger.info("redis_client | No workflow_id found at %s", key)
                    return None
            except Exception as exc:
                logger.error("redis_client | Failed to load workflow_id for %s: %s", username, exc)
                return None

        def delete_user_data(self, username: str):
            if not self._ok or not username:
                logger.warning("redis_client | ❌ User data NOT deleted — Redis unavailable")
                return
            try:
                for suffix in ("chat_history", "last_workflow", "last_workflow_id"):
                    key = self._k(username, suffix)
                    self._client.delete(key)
                    logger.info("redis_client | ✅ Deleted %s", key)
            except Exception as exc:
                logger.error("redis_client | Failed to delete data for %s: %s", username, exc)

    redis_client = _RedisClient()

except ImportError:

    class _NullClient:
        enabled = False

        def save_chat_history(self, *a, **kw):
            logger.warning("redis_client | ❌ Chat NOT saved — redis package not installed. Run: pip install redis")
        def load_chat_history(self, *a, **kw):
            logger.warning("redis_client | ❌ Chat NOT loaded — redis package not installed")
            return []
        def save_last_workflow(self, *a, **kw):
            logger.warning("redis_client | ❌ Workflow NOT saved — redis package not installed")
        def load_last_workflow(self, *a, **kw):
            logger.warning("redis_client | ❌ Workflow NOT loaded — redis package not installed")
            return None
        def save_last_workflow_id(self, *a, **kw):
            logger.warning("redis_client | ❌ Workflow ID NOT saved — redis package not installed")
        def load_last_workflow_id(self, *a, **kw):
            logger.warning("redis_client | ❌ Workflow ID NOT loaded — redis package not installed")
            return None
        def delete_user_data(self, *a, **kw):
            logger.warning("redis_client | ❌ User data NOT deleted — redis package not installed")

    redis_client = _NullClient()
