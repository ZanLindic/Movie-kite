from flask import Blueprint, request, jsonify, session
from sqlalchemy.exc import IntegrityError
from extensions import db
from models import Movie
from movieEvents import record_movie_event
import requests
import os


# Blueprint for movie service - vsa ta koda se potem inicializira v main.py
movieService_bp = Blueprint("movieService", __name__)



### Proxy Route to GET Movie Data from OMDb API ###
@movieService_bp.route("/search", methods=["GET"])
def proxy_search():
    query = request.args.get('q')
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    # Talk to OMDb API
    api_key = os.getenv("API_KEY") 
    response = requests.get(f"https://www.omdbapi.com/?s={query}&apikey={api_key}")

    # Return in Json format to frontend
    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"error": "Failed to fetch data from OMDb API"}), response.status_code
    
  

### Route to Add a Movie from Search Results ###
@movieService_bp.route("/add", methods=["POST", "OPTIONS"])
def add_movie_from_search():
    if request.method == "OPTIONS":
        return "", 204

    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "You must be logged in to save movies."}), 401

    data = request.get_json()
    
    title_input = data.get("title", "").strip()
    year_input = data.get("year", "").strip()
    status_input = (data.get("status") or "").strip().lower()

    if not title_input:
        return {"error": "Title is required"}, 400

    if not status_input:
        return {"error": "Status is required"}, 400

    try:
        existing_movie = Movie.query.filter_by(user_id=user_id, title=title_input).first()

        if existing_movie:
            movie = existing_movie
            movie.year = year_input or movie.year
            movie.set_status(status_input)
            movie.mongo_pointer = movie.mongo_pointer or f"user:{user_id}:movie:{movie.id}"
            message = f"Updated movie {movie.title}"
            event_type = "movie_updated"
        else:
            movie = Movie(user_id=user_id, title=title_input, year=year_input)
            movie.set_status(status_input)
            db.session.add(movie)
            db.session.flush()
            movie.mongo_pointer = f"user:{user_id}:movie:{movie.id}"
            message = f"Added movie {movie.title}"
            event_type = "movie_added"

        record_movie_event(
            user_id=user_id,
            movie_id=movie.id,
            movie_title=movie.title,
            event_type=event_type,
            details=f"status={status_input}; year={movie.year or ''}"
        )

        db.session.commit()
        return jsonify({"message": f"{message} to {status_input}"}), 201
    except IntegrityError:
        db.session.rollback()
        return {"error": "Movie with this title is already in the database"}, 400
    except Exception as e:
        db.session.rollback()
        return {"error": str(e)}, 500



### Route to Get All Movies in the Database ###
@movieService_bp.route("/", methods=["GET"])
def get_all_movies():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "You must be logged in to view movies."}), 401

    movies = Movie.query.filter_by(user_id=user_id).all()
    movies_list = [m.to_dict() for m in movies]
    return jsonify(movies_list)



### Route to Update Movie Status ###
@movieService_bp.route("/<int:movie_id>/status", methods=["PUT"])
def update_status(movie_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "You must be logged in to update movies."}), 401

    data = request.get_json()
    movie = Movie.query.filter_by(id=movie_id, user_id=user_id).first_or_404()
    
    # We expect {'status': 'library'} or {'status': 'watchlist'}
    previous_status = movie.status
    movie.set_status(data.get('status', movie.status))
    record_movie_event(
        user_id=user_id,
        movie_id=movie.id,
        movie_title=movie.title,
        event_type="movie_status_changed",
        details=f"from={previous_status}; to={movie.status}"
    )
    db.session.commit()
    return jsonify({"message": "Status updated!"})



### Route to Delete a Movie from the library ###
@movieService_bp.route("/<int:movie_id>", methods=["DELETE"])
def delete_movie(movie_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "You must be logged in to delete movies."}), 401

    movie = Movie.query.filter_by(id=movie_id, user_id=user_id).first_or_404()
    record_movie_event(
        user_id=user_id,
        movie_id=movie.id,
        movie_title=movie.title,
        event_type="movie_deleted",
        details=f"status={movie.status}"
    )
    db.session.delete(movie)
    db.session.commit()
    return jsonify({"message": "Movie deleted!"})



### Route to Update Movie Rating ###
@movieService_bp.route("/<int:movie_id>/rating", methods=["PATCH"])
def update_rating(movie_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "You must be logged in to rate movies."}), 401

    data = request.get_json()
    movie = Movie.query.filter_by(id=movie_id, user_id=user_id).first_or_404()
    movie.rating = data.get('rating')
    record_movie_event(
        user_id=user_id,
        movie_id=movie.id,
        movie_title=movie.title,
        event_type="movie_rated",
        details=f"rating={movie.rating}"
    )
    db.session.commit()
    return jsonify({"message": "Rating updated"})