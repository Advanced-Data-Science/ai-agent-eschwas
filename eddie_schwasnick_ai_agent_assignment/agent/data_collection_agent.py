import os
import json
import time
import random
import logging
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import requests


class DataCollectionAgent:
    """
    AI Data Collection Agent for Polygon.io (example endpoint: /v3/reference/tickers)

    Meets the assignment requirements:
      1) Configuration Management (load_config)
      2) Intelligent Collection Strategy (collect_data + adaptive loop)
      3) Data Quality Assessment (assess_data_quality + checks)
      4) Adaptive Strategy (adjust_strategy)
      5) Respectful Collection (respectful_delay + check_rate_limits)
    """

    def __init__(self, config_file: str):
        """Initialize agent with configuration from your DMP"""
        self.config = self.load_config(config_file)
        self.setup_logging()
        self.logger.info("Initializing DataCollectionAgent")

        # Secure key: env first, then config fallback
        self.api_key = os.getenv("POLYGON_API_KEY") or self.config.get("polygon_api_key")
        if not self.api_key:
            raise ValueError("No API key found. Set POLYGON_API_KEY env var or 'polygon_api_key' in config.json.")

        # Runtime state
        self.data_store: List[Dict[str, Any]] = []
        self.collection_stats = {
            'start_time': datetime.now(timezone.utc).isoformat(),
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'data_quality_score': 0.0,
            'last_quality_score': 0.0,
            'pages_fetched': 0,
            'apis_used': ["polygon"]
        }
        self.delay_multiplier = 1.0
        self._seen_hashes = set()
        self._last_status_code = None
        self._last_headers: Dict[str, str] = {}
        self._cursor_next_url: Optional[str] = None  # pagination via next_url if present

    # -------------------------
    # (1) CONFIG MANAGEMENT
    # -------------------------
    def load_config(self, config_file: str) -> Dict[str, Any]:
        """Load collection parameters from DMP"""
        with open(config_file, "r") as f:
            cfg = json.load(f)

        # Sensible defaults if not provided in your DMP/config
        cfg.setdefault("base_url", "https://api.polygon.io")
        cfg.setdefault("endpoint", "/v3/reference/tickers")
        cfg.setdefault("params", {"active": "true", "limit": 100})
        cfg.setdefault("max_pages", 3)                 # how many pages (batches) to fetch
        cfg.setdefault("target_records", 250)          # stop once we have roughly this many
        cfg.setdefault("base_delay", 1.0)              # seconds, will be scaled by delay_multiplier
        cfg.setdefault("retry", {"tries": 3, "backoff_seconds": 1.5})
        cfg.setdefault("required_fields", ["ticker", "name"])
        cfg.setdefault("fields_to_keep", ["ticker", "name", "market", "locale", "primary_exchange"])
        cfg.setdefault("dedupe_key_fields", ["ticker"])
        cfg.setdefault("respect_rpm", 4)               # desired requests per minute budget (soft)
        cfg.setdefault("output", {
            "json_path": "agent_output.json",
            "log_path": "data_collection.log"
        })
        return cfg

    def setup_logging(self):
        """Setup logging for the agent"""
        log_path = self.config.get("output", {}).get("log_path", "data_collection.log")
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    # -------------------------
    # (2) INTELLIGENT STRATEGY
    # -------------------------
    def collect_data(self):
        """Main collection loop with adaptive strategy"""
        self.logger.info("Starting data collection")
        while not self.collection_complete():
            # 1) Assess quality
            quality_score = self.assess_data_quality()
            self.collection_stats['last_quality_score'] = quality_score

            # 2) Adapt if success rate is low/high
            if self.get_success_rate() < 0.8:
                self.adjust_strategy()
            else:
                # still allow mild positive feedback
                if self.get_success_rate() > 0.9:
                    self.delay_multiplier = max(0.5, self.delay_multiplier * 0.9)

            # 3) Make request (with rate limiting + retries)
            data = self.make_api_request()

            # 4) Process + validate + store
            if data:
                processed = self.process_data(data)
                if self.validate_data(processed):
                    self.store_data(processed)

            # 5) Respectful delay
            self.respectful_delay()

        self.logger.info("Collection complete")

    def collection_complete(self) -> bool:
        """Stop when we hit target records OR max pages."""
        enough_records = len(self.data_store) >= int(self.config["target_records"])
        too_many_pages = self.collection_stats["pages_fetched"] >= int(self.config["max_pages"])
        return enough_records or too_many_pages

    def make_api_request(self) -> Optional[Dict[str, Any]]:
        """Perform one API call to Polygon (supports next_url pagination if provided)."""
        tries = int(self.config["retry"]["tries"])
        backoff = float(self.config["retry"]["backoff_seconds"])
        self.collection_stats["total_requests"] += 1

        for attempt in range(1, tries + 1):
            try:
                if self._cursor_next_url:
                    # next_url already includes query; still attach apiKey
                    url = self._cursor_next_url
                    params = {"apiKey": self.api_key}
                else:
                    url = self.config["base_url"] + self.config["endpoint"]
                    params = dict(self.config["params"])
                    params["apiKey"] = self.api_key

                resp = requests.get(url, params=params, timeout=10)
                self._last_status_code = resp.status_code
                self._last_headers = dict(resp.headers)

                if resp.status_code == 429:
                    self.logger.warning("429 rate limit hit; backing off...")
                    self.collection_stats["failed_requests"] += 1
                    time.sleep(backoff * attempt)
                    continue

                resp.raise_for_status()
                self.collection_stats["successful_requests"] += 1

                data = resp.json()
                # capture next_url if present
                self._cursor_next_url = data.get("next_url")
                self.collection_stats["pages_fetched"] += 1
                return data

            except requests.exceptions.RequestException as e:
                self.collection_stats["failed_requests"] += 1
                self.logger.error(f"Request attempt {attempt}/{tries} failed: {e}")
                if attempt < tries:
                    time.sleep(backoff * attempt)

        return None

    def process_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract results and trim to fields_to_keep; de-dup inside store_data."""
        results = data.get("results", [])
        keep = self.config["fields_to_keep"]
        if not results:
            return []

        processed = []
        for rec in results:
            if keep:
                processed.append({k: rec.get(k) for k in keep})
            else:
                processed.append(rec)
        return processed

    def validate_data(self, batch: List[Dict[str, Any]]) -> bool:
        """Basic validation: require all 'required_fields' present and not empty."""
        required = self.config["required_fields"]
        valid = 0
        for rec in batch:
            if all(rec.get(f) not in (None, "") for f in required):
                valid += 1
        # simple signal: at least 60% of batch valid
        return (valid / max(1, len(batch))) >= 0.6

    def store_data(self, batch: List[Dict[str, Any]]):
        """Append unique records only (hash by dedupe_key_fields)."""
        key_fields = self.config["dedupe_key_fields"]
        added = 0
        for rec in batch:
            key = "|".join(str(rec.get(k, "")) for k in key_fields)
            h = hashlib.sha256(key.encode("utf-8")).hexdigest()
            if h in self._seen_hashes:
                continue
            self._seen_hashes.add(h)
            self.data_store.append(rec)
            added += 1
        self.logger.info(f"Stored {added} new records (total: {len(self.data_store)})")

    # -------------------------
    # (3) DATA QUALITY
    # -------------------------
    def assess_data_quality(self) -> float:
        """Evaluate the quality of collected data"""
        if not self.data_store:
            return 0.0

        metrics = {
            'completeness': self.check_completeness(),
            'accuracy': self.check_accuracy(),
            'consistency': self.check_consistency(),
            'timeliness': self.check_timeliness()
        }
        score = sum(metrics.values()) / len(metrics)
        self.collection_stats["data_quality_score"] = score
        self.logger.info(f"Quality metrics: {metrics} -> score={score:.2f}")
        return score

    def check_completeness(self) -> float:
        """% of records where all required fields are present and non-empty."""
        req = self.config["required_fields"]
        ok = 0
        for rec in self.data_store:
            if all(rec.get(f) not in (None, "") for f in req):
                ok += 1
        return ok / max(1, len(self.data_store))

    def check_accuracy(self) -> float:
        """
        Placeholder accuracy check:
          - For Polygon tickers, ensure ticker looks like A-Z/.- chars and name not empty.
        """
        ok = 0
        for rec in self.data_store:
            ticker = str(rec.get("ticker", ""))
            name = str(rec.get("name", ""))
            if ticker and name and all(ch.isalnum() or ch in ".-" for ch in ticker):
                ok += 1
        return ok / max(1, len(self.data_store))

    def check_consistency(self) -> float:
        """
        Simple consistency check:
          - Fields that should be strings are strings.
        """
        ok = 0
        total = len(self.data_store)
        for rec in self.data_store:
            types_ok = isinstance(rec.get("ticker", ""), str) and isinstance(rec.get("name", ""), str)
            if types_ok:
                ok += 1
        return ok / max(1, total)

    def check_timeliness(self) -> float:
        """
        Timeliness stub for static reference data:
          - Always 1.0 (fresh) for this endpoint.
          - If you switch to aggregates/trades, compare record timestamps to 'now'.
        """
        return 1.0

    # -------------------------
    # (4) ADAPTIVE STRATEGY
    # -------------------------
    def adjust_strategy(self):
        """Modify collection approach based on performance"""
        sr = self.get_success_rate()
        if sr < 0.5:
            self.delay_multiplier = min(8.0, self.delay_multiplier * 2.0)
            self.try_fallback_api()
        elif sr < 0.8:
            self.delay_multiplier = min(4.0, self.delay_multiplier * 1.5)
        elif sr > 0.9:
            self.delay_multiplier = max(0.5, self.delay_multiplier * 0.8)

        self.log_strategy_change(sr)

    def get_success_rate(self) -> float:
        total = self.collection_stats["total_requests"]
        success = self.collection_stats["successful_requests"]
        return (success / total) if total else 0.0

    def try_fallback_api(self):
        """
        Example fallback: if current endpoint struggles, switch to a lighter one.
        (You can customize this to another Polygon endpoint you prefer.)
        """
        if self.config["endpoint"] != "/v3/reference/tickers":
            return
        self.logger.warning("Switching to fallback endpoint (still Polygon) due to low success rate.")
        self.config["endpoint"] = "/v3/reference/tickers"
        # reduce page size to be gentler
        self.config["params"]["limit"] = max(25, int(self.config["params"].get("limit", 100)) // 2)

    def log_strategy_change(self, success_rate: float):
        self.logger.info(
            f"Strategy adjusted: delay_multiplier={self.delay_multiplier:.2f}, "
            f"success_rate={success_rate:.2f}, last_status={self._last_status_code}"
        )

    # -------------------------
    # (5) RESPECTFUL COLLECTION
    # -------------------------
    def respectful_delay(self):
        """Implement respectful rate limiting with jitter and RPM budget."""
        # Honor an RPM budget (soft)
        rpm = float(self.config.get("respect_rpm", 4))
        min_delay_from_rpm = max(60.0 / max(rpm, 0.1), 0.5)  # seconds/request
        base_delay = float(self.config.get('base_delay', 1.0))
        delay = max(base_delay, min_delay_from_rpm) * self.delay_multiplier

        # Add jitter to avoid thundering herd
        jitter = random.uniform(0.8, 1.3)
        final_sleep = delay * jitter

        # If headers expose remaining limits, slow down preemptively
        self.check_rate_limits()

        self.logger.info(f"Sleeping {final_sleep:.2f}s (respectful delay)")
        time.sleep(final_sleep)

    def check_rate_limits(self):
        """Monitor and respect API rate limits if headers are provided (best-effort)."""
        # Many APIs include headers like: X-RateLimit-Remaining, X-RateLimit-Reset, etc.
        # Polygon may not always return standard ones for your plan; we handle best-effort.
        remaining = None
        for k, v in self._last_headers.items():
            if k.lower().endswith("ratelimit-remaining"):
                try:
                    remaining = float(v)
                except Exception:
                    remaining = None

        if remaining is not None and remaining < 2:
            # If we’re nearly out of calls, bump multiplier
            self.delay_multiplier = min(8.0, self.delay_multiplier * 1.5)
            self.logger.warning("Near rate limit; increasing delay multiplier.")

    # -------------------------
    # SAVE & REPORT
    # -------------------------
    def save_outputs(self):
        """Persist results and stats to disk."""
        out_json = self.config["output"]["json_path"]
        with open(out_json, "w") as f:
            json.dump(self.data_store, f, indent=2)
        self.logger.info(f"Saved JSON: {out_json}")

        # Also save a concise summary for your submission
        summary_path = "agent_summary.json"
        with open(summary_path, "w") as f:
            json.dump(self.summary(), f, indent=2)
        self.logger.info(f"Saved summary: {summary_path}")

    def summary(self) -> Dict[str, Any]:
        return {
            **self.collection_stats,
            "records_collected": len(self.data_store),
            "endpoint": self.config["endpoint"],
            "kept_fields": self.config["fields_to_keep"],
            "delay_multiplier": self.delay_multiplier
        }
    # --------- PART 5: Documentation & QA ---------

    def generate_metadata(self):
        """Create comprehensive metadata for collected dataset"""
        metadata = {
            "collection_info": {
                "collection_date": datetime.now(timezone.utc).isoformat(),
                "agent_version": "1.0",
                "collector": "YourName",
                "total_records": len(self.data_store)
            },
            "data_sources": self.get_sources_used(),
            "quality_metrics": self.calculate_final_quality_metrics(),
            "processing_history": self.get_processing_log(max_lines=200),
            "variables": self.generate_data_dictionary()
        }
        with open("dataset_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        self.logger.info("Saved dataset_metadata.json")

    def get_sources_used(self):
        """Summarize APIs/endpoints used during the run."""
        return {
            "provider": "Polygon.io",
            "base_url": self.config.get("base_url"),
            "endpoint": self.config.get("endpoint"),
            "params": self.config.get("params", {}),
            "apis_used": self.collection_stats.get("apis_used", [])
        }

    def calculate_final_quality_metrics(self):
        """Return final quality metrics using existing checks."""
        return {
            "overall_quality_score": self.collection_stats.get("data_quality_score", 0.0),
            "completeness": self.check_completeness(),
            "accuracy": self.check_accuracy(),
            "consistency": self.check_consistency(),
            "timeliness": self.check_timeliness()
        }

    def get_processing_log(self, max_lines=200):
        """Return tail of the log file for lineage / processing history."""
        log_path = self.config.get("output", {}).get("log_path", "data_collection.log")
        try:
            with open(log_path, "r") as f:
                lines = f.readlines()[-max_lines:]
            return [ln.strip() for ln in lines]
        except Exception:
            return ["No log available"]

    def generate_data_dictionary(self):
        """Auto-generate variable descriptions from fields_to_keep."""
        # You can expand descriptions as needed.
        descriptions = {
            "ticker": "Unique symbol for the listed security or instrument.",
            "name": "Company or fund name associated with the ticker.",
            "market": "Market type (e.g., stocks, crypto, fx).",
            "locale": "Geographic locale of the listing (e.g., us).",
            "primary_exchange": "Primary exchange code where the instrument is listed."
        }
        vars_kept = self.config.get("fields_to_keep", [])
        if not vars_kept:
            # If keeping all, infer from first record’s keys.
            keys = sorted(self.data_store[0].keys()) if self.data_store else []
            vars_kept = keys
        return [
            {
                "name": k,
                "type": "string",       # simple default; refine if you add numeric fields
                "description": descriptions.get(k, "No description provided.")
            }
            for k in vars_kept
        ]

    def generate_quality_report(self):
        """Create detailed quality assessment report"""
        report = {
            "summary": {
                "total_records": len(self.data_store),
                "collection_success_rate": self.get_success_rate(),
                "overall_quality_score": self.collection_stats.get("data_quality_score", 0.0)
            },
            "completeness_analysis": self.analyze_completeness(),
            "data_distribution": self.analyze_distribution(),
            "anomaly_detection": self.detect_anomalies(),
            "recommendations": self.generate_recommendations()
        }

        with open("quality_report.json", "w") as f:
            json.dump(report, f, indent=2)
        self.logger.info("Saved quality_report.json")

        # Also produce a human-readable version
        self.create_readable_report(report)

    def analyze_completeness(self):
        """Percent present for each kept field."""
        if not self.data_store:
            return {}
        fields = sorted({k for rec in self.data_store for k in rec.keys()})
        totals = {k: 0 for k in fields}
        n = len(self.data_store)
        for rec in self.data_store:
            for k in fields:
                if rec.get(k) not in (None, ""):
                    totals[k] += 1
        return {k: totals[k] / n for k in fields}

    def analyze_distribution(self):
        """Simple distributions for categorical fields commonly present."""
        from collections import Counter
        dist = {}
        for key in ["market", "locale", "primary_exchange"]:
            vals = [rec.get(key) for rec in self.data_store if key in rec]
            dist[key] = dict(Counter(vals).most_common(15))
        return dist

    def detect_anomalies(self):
        """Basic anomaly checks: duplicates and invalid tickers."""
        anomalies = {
            "duplicate_tickers": [],
            "invalid_ticker_chars": []
        }
        seen = set()
        dupes = set()
        for rec in self.data_store:
            t = rec.get("ticker")
            if t in seen:
                dupes.add(t)
            else:
                seen.add(t)
            # simple char rule: alnum, dot, hyphen
            if t and not all(ch.isalnum() or ch in ".-" for ch in t):
                anomalies["invalid_ticker_chars"].append(t)
        anomalies["duplicate_tickers"] = sorted(list(dupes))[:50]
        return anomalies

    def generate_recommendations(self):
        """Text recommendations based on quality & rate limiting behavior."""
        sr = self.get_success_rate()
        quality = self.collection_stats.get("data_quality_score", 0.0)
        recs = []
        if sr < 0.8:
            recs.append("Increase delay multiplier and/or reduce per-page limit to improve success rate.")
        else:
            recs.append("Success rate is healthy; consider modestly increasing request rate.")

        if quality < 0.95:
            recs.append("Enhance validation rules or required fields to improve quality.")
        else:
            recs.append("Quality metrics look strong; consider enriching with additional fields.")
        return recs

    def create_readable_report(self, report: Dict[str, Any]):
        """Write a simple Markdown summary of the QA report."""
        lines = []
        lines.append("# Data Quality Report\n")
        lines.append("## Summary")
        lines.append(f"- Total records: {report['summary']['total_records']}")
        lines.append(f"- Success rate: {report['summary']['collection_success_rate']:.2f}")
        lines.append(f"- Overall quality score: {report['summary']['overall_quality_score']:.2f}\n")

        lines.append("## Completeness by Field")
        for k, v in report["completeness_analysis"].items():
            lines.append(f"- {k}: {v:.2f}")

        lines.append("\n## Distributions (Top Values)")
        for k, dist in report["data_distribution"].items():
            lines.append(f"- **{k}**:")
            for val, cnt in dist.items():
                lines.append(f"  - {val}: {cnt}")

        lines.append("\n## Detected Anomalies")
        lines.append(f"- Duplicate tickers (first 50): {', '.join(report['anomaly_detection']['duplicate_tickers']) or 'None'}")
        lines.append(f"- Invalid ticker chars (examples): {', '.join(report['anomaly_detection']['invalid_ticker_chars'][:20]) or 'None'}")

        lines.append("\n## Recommendations")
        for r in report["recommendations"]:
            lines.append(f"- {r}")

        with open("quality_report.md", "w") as f:
            f.write("\n".join(lines))
        self.logger.info("Saved quality_report.md")

    def get_overall_quality_score(self):
        return self.collection_stats.get("data_quality_score", 0.0)

    def generate_collection_summary(self):
        """Produce a final human-readable collection summary (Markdown)."""
        s = self.summary()
        lines = []
        lines.append("# Collection Summary\n")
        lines.append(f"- Start time (UTC): {s.get('start_time')}")
        lines.append(f"- Records collected: {s.get('records_collected')}")
        lines.append(f"- Total requests: {s.get('total_requests')}")
        lines.append(f"- Successful requests: {s.get('successful_requests')}")
        lines.append(f"- Failed requests: {s.get('failed_requests')}")
        lines.append(f"- Success rate: {self.get_success_rate():.2f}")
        lines.append(f"- Endpoint: {s.get('endpoint')}")
        lines.append(f"- Kept fields: {', '.join(s.get('kept_fields') or [])}")
        lines.append(f"- Overall quality score: {self.get_overall_quality_score():.2f}")
        lines.append(f"- Delay multiplier (final): {s.get('delay_multiplier'):.2f}\n")

        lines.append("## Issues Encountered")
        # very simple heuristics based on last status codes / failures
        if s.get("failed_requests", 0) > 0:
            lines.append("- Some requests failed (see data_collection.log for details).")
        else:
            lines.append("- No request failures detected.")

        lines.append("\n## Recommendations")
        for r in self.generate_recommendations():
            lines.append(f"- {r}")

        with open("collection_summary.md", "w") as f:
            f.write("\n".join(lines))
        self.logger.info("Saved collection_summary.md")


if __name__ == "__main__":
    # Example run:
    #   1) Create config.json from the template (see below) and put your real key there
    #      or set POLYGON_API_KEY env var.
    #   2) python data_agent.py
    agent = DataCollectionAgent("config.json")
    agent.collect_data()
    agent.save_outputs()
    agent.generate_metadata()
    agent.generate_quality_report()
    agent.generate_collection_summary()
    print("\n=== AGENT SUMMARY ===")
    print(json.dumps(agent.summary(), indent=2))
