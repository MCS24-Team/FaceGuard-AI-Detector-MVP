from __future__ import annotations

from collections import Counter
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

		try:
			users.update_one(
				{"_id": user["_id"]},
				{"$set": {"last_login_at": datetime.now(timezone.utc)}},
				upsert=False,
			)
		except PyMongoError:
			pass

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
					"auth_provider": "email",
					"upload_count": 0,
					"analysis_counts": {"real": 0, "fake": 0},
					"risk_counts": {"low": 0, "medium": 0, "high": 0},
					"analysis_history": [],
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
					"upload_count": 0,
					"analysis_counts": {"real": 0, "fake": 0},
					"risk_counts": {"low": 0, "medium": 0, "high": 0},
					"analysis_history": [],
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

	def record_analysis_result(
		self,
		email: str,
		label: str,
		fake_probability: float,
		confidence: float,
		model_name: str,
	) -> None:
		if not self.enabled:
			return

		normalized_email = email.strip().lower()
		if not normalized_email:
			return

		label_upper = label.strip().upper()
		label_key = "fake" if label_upper == "FAKE" else "real"
		risk_level = self._risk_level(fake_probability)
		now = datetime.now(timezone.utc)
		entry = {
			"created_at": now,
			"label": label_upper,
			"fake_probability": float(fake_probability),
			"confidence": float(confidence),
			"model_name": model_name,
			"risk_level": risk_level,
		}

		try:
			users = self._get_users_collection()
			users.update_one(
				{
					"email": {
						"$regex": f"^{re.escape(normalized_email)}$",
						"$options": "i",
					}
				},
				{
					"$inc": {
						"upload_count": 1,
						f"analysis_counts.{label_key}": 1,
						f"risk_counts.{risk_level}": 1,
					},
					"$set": {"last_analysis_at": now},
					"$push": {
						"analysis_history": {
							"$each": [entry],
							"$position": 0,
							"$slice": 100,
						}
					},
				},
				upsert=False,
			)
		except PyMongoError:
			return

	def get_user_profile(self, email: str) -> tuple[bool, dict | str, int]:
		if not self.enabled:
			return (
				False,
				"Profile is disabled. Set FACEGUARD_ENABLE_DATABASE=true and configure MongoDB settings.",
				503,
			)

		normalized_email = email.strip().lower()
		if not normalized_email:
			return False, "Email is required.", 400

		try:
			users = self._get_users_collection()
			user = users.find_one(
				{
					"email": {
						"$regex": f"^{re.escape(normalized_email)}$",
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
			return False, "No profile found for this email.", 404

		return True, self._build_profile_payload(user), 200

	def _get_users_collection(self) -> Collection:
		if self._client is None:
			self._client = MongoClient(self.database_url, serverSelectionTimeoutMS=5000)

		database = self._client[self.database_name]
		return database[self.users_collection]

	@staticmethod
	def _risk_level(fake_probability: float) -> str:
		if fake_probability >= 0.67:
			return "high"
		if fake_probability >= 0.34:
			return "medium"
		return "low"

	def _build_profile_payload(self, user: dict) -> dict:
		history = user.get("analysis_history") or []
		analysis_counts = user.get("analysis_counts") or {}
		risk_counts = user.get("risk_counts") or {}

		real_count = int(analysis_counts.get("real", 0))
		fake_count = int(analysis_counts.get("fake", 0))
		if not real_count and not fake_count:
			real_count = sum(1 for item in history if item.get("label") == "REAL")
			fake_count = sum(1 for item in history if item.get("label") == "FAKE")

		low_risk = int(risk_counts.get("low", 0))
		medium_risk = int(risk_counts.get("medium", 0))
		high_risk = int(risk_counts.get("high", 0))
		if not low_risk and not medium_risk and not high_risk:
			for item in history:
				level = item.get("risk_level") or self._risk_level(float(item.get("fake_probability", 0.0)))
				if level == "high":
					high_risk += 1
				elif level == "medium":
					medium_risk += 1
				else:
					low_risk += 1

		total_scans = int(user.get("upload_count") or real_count + fake_count or len(history))
		average_score = 0.0
		if history:
			average_score = round(
				sum(float(item.get("fake_probability", 0.0)) for item in history) / len(history) * 100,
				1,
			)

		recent_analyses = [self._serialize_analysis_item(item) for item in history[:10]]
		return {
			"email": str(user.get("email") or ""),
			"name": user.get("name"),
			"picture": user.get("picture"),
			"auth_provider": user.get("auth_provider") or ("google" if user.get("google_sub") else "email"),
			"created_at": self._iso(user.get("created_at")),
			"last_login_at": self._iso(user.get("last_login_at")),
			"stats": {
				"total_scans": total_scans,
				"real_count": real_count,
				"fake_count": fake_count,
				"low_risk_count": low_risk,
				"medium_risk_count": medium_risk,
				"high_risk_count": high_risk,
				"average_forgery_score": average_score,
				"last_analysis_at": self._iso(user.get("last_analysis_at")),
			},
			"activity_by_day": self._activity_by_day(history),
			"recent_analyses": recent_analyses,
		}

	def _activity_by_day(self, history: list[dict]) -> list[dict]:
		counts: Counter[str] = Counter()
		for item in history:
			created_at = item.get("created_at")
			if isinstance(created_at, datetime):
				day = created_at.date().isoformat()
			else:
				day = str(created_at or "")[:10]
			if day:
				counts[day] += 1

		days = sorted(counts.keys())[-7:]
		return [{"date": day, "count": counts[day]} for day in days]

	def _serialize_analysis_item(self, item: dict) -> dict:
		fake_probability = float(item.get("fake_probability", 0.0))
		return {
			"created_at": self._iso(item.get("created_at")) or "",
			"label": item.get("label") or "UNKNOWN",
			"fake_probability": fake_probability,
			"confidence": float(item.get("confidence", 0.0)),
			"model_name": item.get("model_name") or "unknown",
			"risk_level": item.get("risk_level") or self._risk_level(fake_probability),
		}

	@staticmethod
	def _iso(value: object) -> str | None:
		if isinstance(value, datetime):
			if value.tzinfo is None:
				value = value.replace(tzinfo=timezone.utc)
			return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
		if value:
			return str(value)
		return None

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
