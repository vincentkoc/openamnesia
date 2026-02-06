"""Scalable ingestion components (trawling, spooling)."""

from amnesia.ingest.spool import JsonlSpool, SpoolSegment
from amnesia.ingest.trawl import IncrementalFileTrawler, TrawlState, TrawlStats

__all__ = [
    "IncrementalFileTrawler",
    "JsonlSpool",
    "SpoolSegment",
    "TrawlState",
    "TrawlStats",
]
