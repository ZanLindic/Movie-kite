from datetime import datetime

from extensions import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True, index=True)
    email = db.Column(db.String(120), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    movies = db.relationship("Movie", backref="user", lazy=True, cascade="all, delete-orphan")


class Movie(db.Model):
    __table_args__ = (
        db.UniqueConstraint("user_id", "title", name="uq_user_movie_title"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(100), nullable=False)
    watch_list = db.Column(db.Boolean, default=False, nullable=False)
    library = db.Column(db.Boolean, default=False, nullable=False)
    mongo_pointer = db.Column(db.String(128))
    year = db.Column(db.String(4))
    poster_url = db.Column(db.String(255))
    rating = db.Column(db.Integer, default=0, nullable=False)

    def set_status(self, status):
        status = (status or "").strip().lower()
        self.watch_list = status == "watchlist"
        self.library = status == "library"

    @property
    def status(self):
        if self.library:
            return "library"
        if self.watch_list:
            return "watchlist"
        return ""

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "watch_list": self.watch_list,
            "library": self.library,
            "mongo_pointer": self.mongo_pointer,
            "year": self.year,
            "poster_url": self.poster_url,
            "rating": self.rating,
        }


class MovieEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    movie_id = db.Column(db.Integer, index=True)
    movie_title = db.Column(db.String(100), nullable=False)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)