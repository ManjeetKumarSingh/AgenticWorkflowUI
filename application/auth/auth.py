import json
import hashlib
import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional

AUTH_DIR = Path(__file__).parent
USERS_FILE = AUTH_DIR / "users.json"

ROLE_PERMISSIONS = {
    "admin": ["run_workflow", "create_workflow", "approve_workflow", "chat", "vision", "manage_users"],
    "user": ["run_workflow", "create_workflow", "chat", "vision"],
    "viewer": ["chat"],
}

ALL_ROLES = list(ROLE_PERMISSIONS.keys())


def _hash_password(password: str, salt: Optional[str] = None) -> tuple:
    salt = salt or secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return key.hex(), salt


class AuthManager:
    def __init__(self, users_file: Optional[str] = None):
        self.users_file = Path(users_file) if users_file else USERS_FILE
        self._users: dict = {}
        self._load()

    def _load(self):
        if self.users_file.exists():
            with open(self.users_file) as f:
                self._users = json.load(f)
        else:
            self._users = {}
            self._save()

    def _save(self):
        self.users_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.users_file, "w") as f:
            json.dump(self._users, f, indent=2)

    def register(self, username: str, password: str, email: str = "", role: str = "user") -> Optional[str]:
        username = username.strip().lower()
        email = email.strip().lower()
        if not username or not password:
            return "Username and password are required."
        if len(password) < 4:
            return "Password must be at least 4 characters."
        if username in self._users:
            return "Username already exists."
        if role not in ALL_ROLES:
            return f"Invalid role. Choose from: {', '.join(ALL_ROLES)}"

        pw_hash, salt = _hash_password(password)
        # First user is admin
        if not self._users:
            role = "admin"

        self._users[username] = {
            "username": username,
            "email": email,
            "password_hash": pw_hash,
            "salt": salt,
            "role": role,
            "created_at": datetime.now().isoformat(),
        }
        self._save()
        return None  # success

    def login(self, username: str, password: str) -> Optional[dict]:
        username = username.strip().lower()
        user = self._users.get(username)
        if not user:
            return None
        pw_hash, _ = _hash_password(password, user["salt"])
        if pw_hash != user["password_hash"]:
            return None
        return {
            "username": user["username"],
            "email": user.get("email", ""),
            "role": user["role"],
        }

    def get_user(self, username: str) -> Optional[dict]:
        username = username.strip().lower()
        raw = self._users.get(username)
        if not raw:
            return None
        return {"username": raw["username"], "email": raw.get("email", ""), "role": raw["role"]}

    def has_permission(self, user: Optional[dict], permission: str) -> bool:
        if not user:
            return False
        role = user.get("role", "")
        perms = ROLE_PERMISSIONS.get(role, [])
        return permission in perms

    def list_users(self) -> list[dict]:
        return [
            {"username": u["username"], "email": u.get("email", ""), "role": u["role"], "created_at": u["created_at"]}
            for u in self._users.values()
        ]

    def update_role(self, username: str, new_role: str) -> Optional[str]:
        username = username.strip().lower()
        if username not in self._users:
            return "User not found."
        if new_role not in ALL_ROLES:
            return f"Invalid role. Choose from: {', '.join(ALL_ROLES)}"
        self._users[username]["role"] = new_role
        self._save()
        return None
