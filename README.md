# Movie-kite

Flask + Vue movie tracker with session-based login/signup.

## Run

```bash
source .venv/bin/activate
./.venv/bin/python main.py
```

Open the app at `http://127.0.0.1:5000/` so authentication cookies and session state work correctly.

## Data model

- `User`: `id`, `username`, `email`, `password_hash`
- `Movie`: `id`, `user_id`, `title`, `watch_list`, `library`, `mongo_pointer`, `year`, `poster_url`, `rating`
- MongoDB review docs are scoped per user and movie through `user_id` + `movie_id`

## Notes

- Passwords are stored as hashes, never plain text.
- Movie rows are scoped to the signed-in user.
- MongoDB stores notes/reviews for the user’s own movies.
