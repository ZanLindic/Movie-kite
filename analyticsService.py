from flask import Blueprint, jsonify, request

from extensions import db
from models import MovieEvent, User

analytics_bp = Blueprint("analytics_bp", __name__, url_prefix="/api/analytics")


def _parse_limit(value, default=100, maximum=500):
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return default

    return max(1, min(limit, maximum))


@analytics_bp.route("/events", methods=["GET"])
def list_events():
    limit = _parse_limit(request.args.get("limit"), default=100, maximum=500)
    username = (request.args.get("username") or "").strip()
    event_type = (request.args.get("event_type") or "").strip()

    query = db.session.query(MovieEvent, User.username).join(User, User.id == MovieEvent.user_id)

    if username:
        query = query.filter(User.username == username)

    if event_type:
        query = query.filter(MovieEvent.event_type == event_type)

    rows = query.order_by(MovieEvent.created_at.desc()).limit(limit).all()

    return jsonify([
        {
            "id": event.id,
            "user_id": event.user_id,
            "username": username_value,
            "movie_id": event.movie_id,
            "movie_title": event.movie_title,
            "event_type": event.event_type,
            "details": event.details,
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }
        for event, username_value in rows
    ])


@analytics_bp.route("/events/summary", methods=["GET"])
def events_summary():
    rows = (
        db.session.query(MovieEvent.event_type, db.func.count(MovieEvent.id))
        .group_by(MovieEvent.event_type)
        .order_by(db.func.count(MovieEvent.id).desc(), MovieEvent.event_type.asc())
        .all()
    )

    return jsonify([
        {
            "event_type": event_type,
            "count": count,
        }
        for event_type, count in rows
    ])


@analytics_bp.route("/movies/popularity", methods=["GET"])
def movies_popularity():
    rows = (
        db.session.query(MovieEvent.movie_title, db.func.count(MovieEvent.id))
        .group_by(MovieEvent.movie_title)
        .order_by(db.func.count(MovieEvent.id).desc(), MovieEvent.movie_title.asc())
        .all()
    )

    return jsonify([
        {
            "movie_title": movie_title,
            "event_count": count,
        }
        for movie_title, count in rows
    ])


@analytics_bp.route("/users/activity", methods=["GET"])
def users_activity():
    rows = (
        db.session.query(
            User.username,
            db.func.count(MovieEvent.id),
            db.func.max(MovieEvent.created_at),
        )
        .join(MovieEvent, MovieEvent.user_id == User.id)
        .group_by(User.id, User.username)
        .order_by(db.func.count(MovieEvent.id).desc(), User.username.asc())
        .all()
    )

    return jsonify([
        {
            "username": username,
            "event_count": count,
            "last_event_at": last_event_at.isoformat() if last_event_at else None,
        }
        for username, count, last_event_at in rows
    ])
