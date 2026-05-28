# MovieKite Backend Overview

This project is a single Flask application split into two blueprints:

- `movieService.py` handles movie search and movie records stored in SQLite through SQLAlchemy.
- `reviewService.py` handles written reviews stored in MongoDB.

The files are separate service modules, but they run inside the same Flask app created in `main.py`.

## Request Flow

1. The browser loads the frontend from `index.html` and the JavaScript in `app.js` sends requests to the Flask backend.
2. `main.py` creates the Flask app, loads environment variables, configures SQLAlchemy and MongoDB, enables CORS, and registers the blueprints.
3. Requests to `/movies` are routed to `movieService.py`.
4. Requests to `/api/reviews` are routed to `reviewService.py`.
5. The movie service reads and writes movie records in the SQLite database through the `Movie` SQLAlchemy model.
6. The review service reads and writes note documents in MongoDB using `movie_id` as the shared link back to the SQL movie record.

## Main App Responsibilities

`main.py` is the entry point for the backend. It does three important jobs:

- It configures the SQL database with `sqlite:///movies.db`.
- It configures MongoDB with the local `movieDB` database.
- It attaches the two blueprints so the route modules can stay focused on their own data stores.

The homepage route at `/` is only a simple status page that confirms the app is running and offers a link into the movies area.

## Data Split

The app uses two storage systems for two different kinds of data:

- SQLite stores the core movie list, including title, year, status, poster URL, and rating.
- MongoDB stores free-form review notes for each movie.

That split keeps structured movie data in SQL while letting notes stay flexible in MongoDB.

## End-to-End Example

When a user searches for a movie, the frontend calls the movie service search route. That route queries OMDb, returns the search results, and the frontend can then add a selected result to the SQL movie list.

When the user opens a movie detail view and writes a note, the frontend calls the review service. The note is saved in MongoDB using the same movie ID that came from the SQL movie table, so both stores stay linked.
