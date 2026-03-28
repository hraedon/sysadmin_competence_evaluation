"""Server-side profile storage — mirrors frontend/src/lib/profile.js logic."""
import datetime
import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from ..database import Profile, EvaluationRecord

logger = logging.getLogger(__name__)


def get_profile(db: Session, user_id: str) -> dict:
    """Load the user's profile, or return an empty skeleton."""
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if profile and profile.data:
        return profile.data
    return {"updated": None, "domains": {}}


def save_result(db: Session, user_id: str, scenario_id: str, result: dict) -> dict:
    """Save a single evaluation result to the user's profile.

    Mirrors the frontend profile.js saveResult() logic: find-or-create domain
    entry, replace prior result for same scenario_id, update timestamp.
    """
    profile_row = db.query(Profile).filter(Profile.user_id == user_id).first()
    data = (profile_row.data if profile_row and profile_row.data else
            {"updated": None, "domains": {}})

    domain_key = str(result.get("domain", "unknown"))
    if domain_key not in data["domains"]:
        data["domains"][domain_key] = {
            "domain_name": result.get("domain_name", f"Domain {domain_key}"),
            "results": [],
        }

    domain = data["domains"][domain_key]
    # Replace existing result for the same scenario
    domain["results"] = [r for r in domain["results"] if r.get("scenario_id") != scenario_id]
    domain["results"].append({
        "scenario_id": scenario_id,
        "level": result.get("level"),
        "confidence": result.get("confidence"),
        "gap": result.get("gap"),
        "almost_caught": result.get("almost_caught", []),
        "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
    })

    data["updated"] = datetime.datetime.now(datetime.UTC).isoformat()

    if profile_row:
        profile_row.data = data
        flag_modified(profile_row, "data")
        profile_row.updated_at = datetime.datetime.now(datetime.UTC)
    else:
        profile_row = Profile(user_id=user_id, data=data)
        db.add(profile_row)

    db.commit()
    return data


def import_profile(db: Session, user_id: str, incoming: dict) -> dict:
    """Import a profile from localStorage, merging with any existing server data.

    Merge strategy: "most recent result per scenario wins" — compare created_at
    timestamps, keep the newer result.
    """
    existing = get_profile(db, user_id)
    incoming_domains = incoming.get("domains", {})

    for domain_key, domain_data in incoming_domains.items():
        if domain_key not in existing["domains"]:
            existing["domains"][domain_key] = domain_data
            continue

        existing_domain = existing["domains"][domain_key]
        existing_results = {r["scenario_id"]: r for r in existing_domain.get("results", [])}

        for result in domain_data.get("results", []):
            sid = result.get("scenario_id")
            if not sid:
                continue

            if sid in existing_results:
                # Keep the most recent result
                existing_ts = existing_results[sid].get("created_at", "")
                incoming_ts = result.get("created_at", "")
                if incoming_ts > existing_ts:
                    existing_results[sid] = result
            else:
                existing_results[sid] = result

        existing_domain["results"] = list(existing_results.values())

    existing["updated"] = datetime.datetime.now(datetime.UTC).isoformat()

    profile_row = db.query(Profile).filter(Profile.user_id == user_id).first()
    if profile_row:
        profile_row.data = existing
        flag_modified(profile_row, "data")
        profile_row.updated_at = datetime.datetime.now(datetime.UTC)
    else:
        profile_row = Profile(user_id=user_id, data=existing)
        db.add(profile_row)

    db.commit()
    return existing


def export_profile(db: Session, user_id: str) -> dict:
    """Export the user's profile as JSON."""
    return get_profile(db, user_id)
