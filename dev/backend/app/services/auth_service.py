from __future__ import annotations

from datetime import datetime, timezone
import re

import bcrypt
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError


class AuthService:
	def __init__(
		self,
		enabled: bool,
		database_url: str,
		database_name: str,
		users_collection: str,
	) -> None:
		self.enabled = enabled
		self.database_url = database_url
		self.database_name = database_name
		self.users_collection = users_collection
		self._client: MongoClient | None = None

	def authenticate(self, email: str, password: str) -> tuple[bool, str, int]:
		if not self.enabled:
			return (
				False,
				"Sign-in is disabled. Set FACEGUARD_ENABLE_DATABASE=true and configure MongoDB settings.",
				503,
			)

		try:
			users = self._get_users_collection()
			user = users.find_one(
				{
					"email": {
						"$regex": f"^{re.escape(email.strip())}$",
						"$options": "i",
					}
				}
			)
		except PyMongoError as exc:
			return (
				False,
				f"Database connection failed ({exc.__class__.__name__}). Verify FACEGUARD_DATABASE_URL and MongoDB network access.",
				503,
			)

		if not user:
			return False, "No account found for this email.", 401

		if not self._verify_password(password, user):
			return False, "Invalid email or password.", 401

		return True, "Sign in successful.", 200

	def register(self, email: str, password: str) -> tuple[bool, str, int]:
		if not self.enabled:
			return (
				False,
				"Sign-up is disabled. Set FACEGUARD_ENABLE_DATABASE=true and configure MongoDB settings.",
				503,
			)

		normalized_email = email.strip().lower()

		try:
			users = self._get_users_collection()
			existing_user = users.find_one(
				{
					"email": {
						"$regex": f"^{re.escape(normalized_email)}$",
						"$options": "i",
					}
				},
				{"_id": 1},
			)
			if existing_user:
				return False, "An account with this email already exists.", 409

			password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
			users.insert_one(
				{
					"email": normalized_email,
					"password_hash": password_hash,
					"created_at": datetime.now(timezone.utc),
				}
			)
		except PyMongoError as exc:
			return (
				False,
				f"Database connection failed ({exc.__class__.__name__}). Verify FACEGUARD_DATABASE_URL and MongoDB network access.",
				503,
			)

		return True, "Account created. You can now sign in.", 201

	def authenticate_google_user(
		self,
		email: str,
		google_sub: str,
		name: str | None = None,
		picture: str | None = None,
	) -> tuple[bool, str, int]:
		if not self.enabled:
			return (
				False,
				"Google sign-in is disabled. Set FACEGUARD_ENABLE_DATABASE=true and configure MongoDB settings.",
				503,
			)

		normalized_email = email.strip().lower()
		if not normalized_email or not google_sub:
			return False, "Google account details are incomplete.", 400

		try:
			users = self._get_users_collection()
			existing_user = users.find_one(
				{
					"$or": [
						{"google_sub": google_sub},
						{
							"email": {
								"$regex": f"^{re.escape(normalized_email)}$",
								"$options": "i",
							}
						},
					]
				}
			)

			now = datetime.now(timezone.utc)
			google_profile = {
				"email": normalized_email,
				"google_sub": google_sub,
				"auth_provider": "google",
				"name": name,
				"picture": picture,
				"last_login_at": now,
			}

			if existing_user:
				users.update_one(
					{"_id": existing_user["_id"]},
					{"$set": google_profile},
					upsert=False,
				)
				return True, "Google sign in successful.", 200

			users.insert_one(
				{
					**google_profile,
					"created_at": now,
				}
			)
		except PyMongoError as exc:
			return (
				False,
				f"Database connection failed ({exc.__class__.__name__}). Verify FACEGUARD_DATABASE_URL and MongoDB network access.",
				503,
			)

		return True, "Google account created and signed in.", 201

	def increment_user_upload_count(self, email: str) -> None:
		if not self.enabled:
			return

		normalized_email = email.strip().lower()
		if not normalized_email:
			return

		try:
			users = self._get_users_collection()
			users.update_one(
				{
					"email": {
						"$regex": f"^{re.escape(normalized_email)}$",
						"$options": "i",
					}
				},
				{"$inc": {"upload_count": 1}},
				upsert=False,
			)
		except PyMongoError:
			return

	def _get_users_collection(self) -> Collection:
		if self._client is None:
			self._client = MongoClient(self.database_url, serverSelectionTimeoutMS=5000)

		database = self._client[self.database_name]
		return database[self.users_collection]

	@staticmethod
	def _verify_password(password: str, user: dict) -> bool:
		stored_hash = user.get("password_hash") or user.get("passwordHash")
		if isinstance(stored_hash, str) and stored_hash:
			try:
				return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
			except (TypeError, ValueError):
				return False

		stored_password = user.get("password")
		if isinstance(stored_password, str):
			return stored_password == password

		return False
