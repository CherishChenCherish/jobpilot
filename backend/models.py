"""JobPilot database models."""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.Text)
    plan = db.Column(db.String(20), nullable=False, default="free")  # free | pro | team
    searches_used = db.Column(db.Integer, nullable=False, default=0)
    stripe_customer_id = db.Column(db.String(255))
    stripe_sub_id = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    searches = db.relationship("Search", back_populates="user", lazy="dynamic")
    subscription = db.relationship("Subscription", back_populates="user", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "google_id": self.google_id,
            "email": self.email,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "plan": self.plan,
            "searches_used": self.searches_used,
            "created_at": self.created_at.isoformat(),
        }


class Search(db.Model):
    __tablename__ = "searches"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    prefs_json = db.Column(db.JSON)   # user preferences / JD input
    results_json = db.Column(db.JSON)  # matched jobs + recommended resume
    audit_json = db.Column(db.JSON)    # match quality scores

    user = db.relationship("User", back_populates="searches")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "prefs": self.prefs_json,
            "results": self.results_json,
            "audit": self.audit_json,
        }


class CachedJob(db.Model):
    """Pre-verified job cache. Refreshed daily."""
    __tablename__ = "cached_jobs"

    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    apply_url = db.Column(db.Text, nullable=False, unique=True)
    job_board = db.Column(db.String(50))  # greenhouse | lever | direct
    location = db.Column(db.String(255))
    remote = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(50), default="open")  # open | closed | unverified
    confidence = db.Column(db.String(20), default="high")
    ghost_risk = db.Column(db.String(20), default="low")
    posting_age_days = db.Column(db.Integer)
    description = db.Column(db.Text)
    degree_required = db.Column(db.String(100))
    visa_sponsorship = db.Column(db.String(50))
    recommended_cv = db.Column(db.String(50))
    categories = db.Column(db.JSON)  # ["DS/ML", "Health Informatics"]
    match_reason = db.Column(db.Text)
    key_requirements = db.Column(db.JSON)
    company_size = db.Column(db.String(20))
    region = db.Column(db.String(10), default="US", index=True)  # US, CA, HK, CN, UK, AU
    language = db.Column(db.String(5), default="EN")  # EN, CN
    discovery_source = db.Column(db.String(30), default="greenhouse")  # greenhouse, lever, web_discovery
    date_added = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_verified_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True, index=True)

    REGION_FLAGS = {"US": "\U0001F1FA\U0001F1F8", "CA": "\U0001F1E8\U0001F1E6",
                    "UK": "\U0001F1EC\U0001F1E7", "AU": "\U0001F1E6\U0001F1FA",
                    "HK": "\U0001F1ED\U0001F1F0", "CN": "\U0001F1E8\U0001F1F3"}

    def to_dict(self):
        flag = self.REGION_FLAGS.get(self.region or "US", "")
        is_cn = (self.region == "CN")
        return {
            "company": self.company,
            "title": self.title,
            "apply_url": self.apply_url,
            "job_board": self.job_board or "",
            "location": self.location or "",
            "remote": self.remote or False,
            "description_snippet": self.description or "",
            "degree_required": self.degree_required or "",
            "visa_sponsorship": self.visa_sponsorship or "",
            "recommended_cv": self.recommended_cv or "V1-DS",
            "categories": self.categories or [],
            "match_reason": self.match_reason or "",
            "key_requirements": self.key_requirements or [],
            "company_size": self.company_size or "mid",
            "region": self.region or "US",
            "region_flag": flag,
            "language": self.language or "EN",
            "discovery_source": self.discovery_source or "greenhouse",
            "is_cn": is_cn,
            "posting_date": self.last_verified_at.strftime("%Y-%m-%d") if self.last_verified_at else "",
            "audit": {
                "status": "\u2713 Open" if self.status == "open" else "\u26A0 Unverified",
                "confidence": self.confidence or "high",
                "reason": f"Verified {self.last_verified_at.strftime('%Y-%m-%d %H:%M')}" if self.last_verified_at else "Cached",
                "posting_age_days": self.posting_age_days,
                "ghost_risk": self.ghost_risk or "low",
                "degree_match": "ok",
                "visa": self.visa_sponsorship or "unspecified",
                "drop": False,
                "needs_manual_check": False,
            },
        }


class PendingDiscovery(db.Model):
    """Tracks region+direction combos that need more jobs."""
    __tablename__ = "pending_discovery"

    id = db.Column(db.Integer, primary_key=True)
    regions = db.Column(db.JSON, nullable=False)     # ["UK", "AU"]
    directions = db.Column(db.JSON, nullable=False)  # ["DS/ML", "Health Informatics"]
    requested_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(20), default="pending")  # pending | done


class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    stripe_sub_id = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="active")  # active | canceled | past_due
    current_period_end = db.Column(db.DateTime)

    user = db.relationship("User", back_populates="subscription")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "stripe_sub_id": self.stripe_sub_id,
            "status": self.status,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
        }
