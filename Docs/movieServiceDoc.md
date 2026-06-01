# Movie Service

`movieService.py` contains the movie-related blueprint. It is responsible for searching external movie data, storing movies in SQLite, and updating movie state in the database.

## Blueprint Role

The module registers `movieService_bp`, and `main.py` mounts it under `/movies`. That means every route in this file is exposed below the `/movies` prefix.

## Responsibilities

This service handles the structured movie data stored by SQLAlchemy through the `Movie` model:

- search movies from the OMDb API
- add a selected movie to the local database
- fetch all saved movies
- update a movie's status
- update a movie's rating
- delete a movie from the library
- proxy stored poster URLs back to the frontend
- upload poster images to object storage when a movie is saved

## Search Flow

`GET /movies/search?q=<query>` acts as a proxy to OMDb.

The route:

- reads the `q` query parameter from the request
- returns a `400` response if the query is missing
- sends the query to OMDb using the `API_KEY` environment variable
- returns the OMDb response JSON to the frontend

This keeps the frontend from talking to OMDb directly and centralizes the external API call in the backend.

## Add Movie Flow

`POST /movies/add` inserts a new `Movie` row.

The request body is expected to contain:

- `title`
- `year`
- `status`

The route trims and normalizes the data, creates a `Movie` object, and commits it through `db.session`.

Validation and error handling:

- missing `title` returns `400`
- duplicate titles are rejected by the database unique constraint and return `400`
- unexpected failures return `500`

The route also accepts `OPTIONS` so browser CORS preflight requests can complete successfully.

## Movie Management Routes

`GET /movies/` returns all saved movies as JSON.

`GET /movies/poster?url=<poster_url>` returns poster bytes for frontend rendering.

`PUT /movies/<movie_id>/status` updates the stored status for one movie.

`PATCH /movies/<movie_id>/rating` updates the stored rating for one movie.

`DELETE /movies/<movie_id>` removes a movie from SQLite.

All three mutating routes load the movie with `query.get_or_404`, so a missing movie returns a `404` response automatically.

## Database Model

The service uses the `Movie` SQLAlchemy model defined in `models.py`.

Important fields:

- `id`: primary key
- `title`: required and unique
- `status`: defaults to `watchlist`
- `year`: stored as a string
- `poster_url`: optional poster link
- `rating`: integer rating with a default of `0`

When a poster URL is provided during `POST /movies/add`, the backend tries to store the image in object storage and saves the resulting URL in `poster_url`.

## Service Notes

This module depends on two external inputs:

- the local SQLite database configured in `main.py`
- the OMDb `API_KEY` environment variable for search requests

It is the part of the backend that owns all movie lifecycle operations.
