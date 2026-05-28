from extensions import db
from models import MovieEvent


def record_movie_event(*, user_id, movie_id, movie_title, event_type, details=None):
    event = MovieEvent(
        user_id=user_id,
        movie_id=movie_id,
        movie_title=movie_title,
        event_type=event_type,
        details=details,
    )
    db.session.add(event)
    return event
