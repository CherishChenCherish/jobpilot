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
