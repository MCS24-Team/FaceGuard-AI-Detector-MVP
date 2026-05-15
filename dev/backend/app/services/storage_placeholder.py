from __future__ import annotations

from pymongo import MongoClient
from pymongo.errors import PyMongoError


class StoragePlaceholder:
	"""Lightweight persistence for upload counters (no-op when disabled)."""

	def __init__(
		self,
		enabled: bool = False,
		database_url: str = "",
		database_name: str = "",
		upload_collection: str = "uploads",
		counter_document_id: str = "upload_counter",
	) -> None:
		self.enabled = enabled
		self.database_url = database_url
		self.database_name = database_name
		self.upload_collection = upload_collection
		self.counter_document_id = counter_document_id
		self._client: MongoClient | None = None

	def increment_upload_count(self) -> None:
		if not self.enabled:
			return

		try:
			collection = self._get_uploads_collection()
			collection.update_one(
				{"_id": self.counter_document_id},
				{"$inc": {"total_uploads": 1}},
				upsert=True,
			)
		except PyMongoError:
			return

	def _get_uploads_collection(self):
		if self._client is None:
			self._client = MongoClient(self.database_url, serverSelectionTimeoutMS=5000)
		database = self._client[self.database_name]
		return database[self.upload_collection]
