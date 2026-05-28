from flask import Blueprint, request, jsonify, session
from datetime import datetime
from extensions import mongo
from extensions import db
from models import Movie
from movieEvents import record_movie_event

# Blueprint for written notes (reviews) - vsa ta koda se potem inicializira v main.py
review_bp = Blueprint('review_bp', __name__)


def _get_owned_movie(movie_id):
    user_id = session.get("user_id")
    if not user_id:
        return None, (jsonify({"error": "You must be logged in."}), 401)

    movie = Movie.query.filter_by(id=movie_id, user_id=user_id).first()
    if not movie:
        return None, (jsonify({"error": "Movie not found."}), 404)

    return movie, None

# Route to fetch the note for a specific movie ID
@review_bp.route('/<int:movie_id>', methods=['GET'])
def get_notes(movie_id):
    """Fetch the written note for a specific SQL movie ID."""
    movie, error_response = _get_owned_movie(movie_id)
    if error_response:
        return error_response

    note_data = mongo.db.movie_notes.find_one({"movie_id": movie_id, "user_id": movie.user_id})
    if note_data:
        return jsonify({
            "note": note_data['note'],
            "last_updated": note_data.get('last_updated')
        }), 200
    return jsonify({"note": ""}), 200


# Route to create or update a note for a specific movie ID
@review_bp.route('/<int:movie_id>', methods=['POST'])
def save_note(movie_id):
    """Create or update a note for a specific SQL movie ID."""
    movie, error_response = _get_owned_movie(movie_id)
    if error_response:
        return error_response

    data = request.get_json()
    note_text = data.get('note', '')

    mongo.db.movie_notes.update_one(
        {"movie_id": movie_id, "user_id": movie.user_id},
        {"$set": {
            "note": note_text,
            "user_id": movie.user_id,
            "last_updated": datetime.utcnow()
        }},
        upsert=True 
    )

    movie.mongo_pointer = f"user:{movie.user_id}:movie:{movie.id}"
    record_movie_event(
        user_id=movie.user_id,
        movie_id=movie.id,
        movie_title=movie.title,
        event_type="movie_note_saved",
        details=f"note_length={len(note_text)}"
    )
    db.session.commit()

    return jsonify({"message": "Note synced to MongoDB"}), 201


# Route to delete a note for a specific movie ID
@review_bp.route('/<int:movie_id>', methods=['DELETE'])
def delete_note(movie_id):
    """Wipe the note from Mongo without touching the SQL movie record."""
    movie, error_response = _get_owned_movie(movie_id)
    if error_response:
        return error_response

    mongo.db.movie_notes.delete_one({"movie_id": movie_id, "user_id": movie.user_id})
    record_movie_event(
        user_id=movie.user_id,
        movie_id=movie.id,
        movie_title=movie.title,
        event_type="movie_note_deleted",
        details="note deleted"
    )
    db.session.commit()
    return jsonify({"message": "Note deleted"}), 200