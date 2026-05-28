# Review Service

`reviewService.py` contains the note and review blueprint. It stores free-form text in MongoDB and links each note to a movie through the SQL movie ID.

## Blueprint Role

The module registers `review_bp`, and `main.py` mounts it under `/api/reviews`. Every route in this file is therefore available below that prefix.

## Responsibilities

This service handles note data that does not fit the structured SQL movie model well:

- fetch the current note for a movie
- create or update a note
- delete a note without touching the SQL movie record

The notes live in the `movie_notes` MongoDB collection.

## Fetch Flow

`GET /api/reviews/<movie_id>` looks up a document with the matching `movie_id` value.

Behavior:

- if a note exists, the service returns the note text and `last_updated`
- if no note exists, the service returns an empty note object

This makes the frontend simpler because it can always expect a JSON response.

## Save Flow

`POST /api/reviews/<movie_id>` creates or updates a note.

The route:

- reads the JSON body
- pulls the `note` field, defaulting to an empty string
- writes the note into `movie_notes` with `update_one`
- sets `last_updated` to the current UTC time
- uses `upsert=True` so a missing document is created automatically

This route returns `201` when the note is synced to MongoDB.

## Delete Flow

`DELETE /api/reviews/<movie_id>` removes the matching note document from MongoDB.

Important detail:

- only the MongoDB note is deleted
- the SQL movie record is left untouched

That allows the user to clear notes without removing the movie from the library.

## Data Model

The MongoDB document shape is simple:

- `movie_id`: the SQL movie ID used as the join key
- `note`: the free-form review text
- `last_updated`: UTC timestamp of the latest save

## Service Notes

This module depends on the shared MongoDB connection configured in `main.py`.
It is intentionally separate from the SQL movie service so movie records and review notes can evolve independently.
