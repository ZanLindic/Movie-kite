# Movie-kite

Flask + Vue movie tracker with session-based login/signup.

## Run

```bash
source .venv/bin/activate
./.venv/bin/python main.py
```

Open the app at `http://127.0.0.1:5000/` so authentication cookies and session state work correctly.

## Production deployment with Nginx

Use Gunicorn to run the Flask app on loopback, then let Nginx expose the public site on `movie-kite.top`.

1. Install the production dependency:

```bash
source .venv/bin/activate
pip install gunicorn
```

2. Set production environment variables in `.env`:

```dotenv
SECRET_KEY=change-me
SESSION_COOKIE_SECURE=true
MONGO_URI=mongodb://localhost:27017/movieDB
DATABASE_URL=sqlite:///movies.db
```

3. Create the systemd unit from `deploy/systemd/movie-kite.service`, then enable it:

```bash
sudo cp deploy/systemd/movie-kite.service /etc/systemd/system/movie-kite.service
sudo systemctl daemon-reload
sudo systemctl enable --now movie-kite.service
sudo systemctl status movie-kite.service
```

4. Create the Nginx site from `deploy/nginx/movie-kite.conf` and reload Nginx:

```bash
sudo cp deploy/nginx/movie-kite.conf /etc/nginx/sites-available/movie-kite.conf
sudo ln -s /etc/nginx/sites-available/movie-kite.conf /etc/nginx/sites-enabled/movie-kite.conf
sudo nginx -t
sudo systemctl reload nginx
```

5. If you are using HTTPS, add a certificate with Certbot after the site is reachable on port 80.

The Gunicorn service binds to `127.0.0.1:5000`, so Nginx is the only public-facing process.

## Data model

- `User`: `id`, `username`, `email`, `password_hash`
- `Movie`: `id`, `user_id`, `title`, `watch_list`, `library`, `mongo_pointer`, `year`, `poster_url`, `rating`
- MongoDB review docs are scoped per user and movie through `user_id` + `movie_id`

## Notes

- Passwords are stored as hashes, never plain text.
- Movie rows are scoped to the signed-in user.
- MongoDB stores notes/reviews for the user’s own movies.
