

# Grafana SQL Queries for Movie-kite

These queries are written for the current SQL schema in `models.py`:

- `user(id, username, email, password_hash)`
- `movie(id, user_id, title, watch_list, library, mongo_pointer, year, poster_url, rating)`
- `movie_event(id, user_id, movie_id, movie_title, event_type, details, created_at)`

They are designed for Grafana panels that show how many users have a movie in `watchlist` or `library`, plus totals per user.

## 1. Movies in Library by Title

Count how many users have each movie in their library.

```sql
SELECT
    title,
    COUNT(*) AS users_in_library
FROM movie
WHERE library = 1
GROUP BY title
ORDER BY users_in_library DESC, title ASC;
```

## 2. Movies in Watchlist by Title

Count how many users have each movie in their watchlist.

```sql
SELECT
    title,
    COUNT(*) AS users_in_watchlist
FROM movie
WHERE watch_list = 1
GROUP BY title
ORDER BY users_in_watchlist DESC, title ASC;
```

## 3. Total Movies Per Status

Show how many rows are in each list type overall.

```sql
SELECT
    'library' AS list_type,
    COUNT(*) AS total_rows
FROM movie
WHERE library = 1
UNION ALL
SELECT
    'watchlist' AS list_type,
    COUNT(*) AS total_rows
FROM movie
WHERE watch_list = 1;
```

## 4. User Movie Counts

Show how many movies each user has in each list.

```sql
SELECT
    u.username,
    COUNT(CASE WHEN m.library = 1 THEN 1 END) AS library_count,
    COUNT(CASE WHEN m.watch_list = 1 THEN 1 END) AS watchlist_count,
    COUNT(*) AS total_movies
FROM user u
LEFT JOIN movie m ON m.user_id = u.id
GROUP BY u.id, u.username
ORDER BY total_movies DESC, u.username ASC;
```

## 5. Top Users By Library Size

Useful for a leaderboard or bar chart.

```sql
SELECT
    u.username,
    COUNT(*) AS library_count
FROM user u
JOIN movie m ON m.user_id = u.id
WHERE m.library = 1
GROUP BY u.id, u.username
ORDER BY library_count DESC
LIMIT 10;
```

## 6. Average Rating Per Movie

If you want a rating panel for library movies.

```sql
SELECT
    title,
    AVG(rating) AS avg_rating,
    COUNT(*) AS rating_count
FROM movie
WHERE library = 1 AND rating > 0
GROUP BY title
ORDER BY avg_rating DESC, rating_count DESC;
```

## 7. Per-User Library and Watchlist Breakdown

Good for a table panel filtered by a selected user.

```sql
SELECT
    u.username,
    m.title,
    m.watch_list,
    m.library,
    m.rating,
    m.year
FROM movie m
JOIN user u ON u.id = m.user_id
ORDER BY u.username ASC, m.title ASC;
```

## Grafana Notes

- Use a table panel for lists and a bar chart or stat panel for counts.
- If you want to filter by a specific user, add a Grafana variable for `username`.
- If you want time-based interaction history, add a separate `movie_events` table or send events to Loki. The current schema only stores the latest state, not the full history.

## Example User Filter Query

```sql
SELECT
    m.title,
    m.watch_list,
    m.library,
    m.rating
FROM movie m
JOIN user u ON u.id = m.user_id
WHERE u.username = '$username'
ORDER BY m.title ASC;
```

## Recommendation

Your current tables are enough for aggregation dashboards. For click-by-click analytics such as "added to watchlist", "moved to library", and "removed", add an event table like:

- `movie_event(id, user_id, movie_id, movie_title, event_type, details, created_at)`

That makes Grafana time-series dashboards much better than trying to infer history from the latest movie row state.

## Event-Based Grafana Queries

### Movie Actions Over Time

```sql
SELECT
    date(created_at) AS day,
    event_type,
    COUNT(*) AS event_count
FROM movie_event
GROUP BY date(created_at), event_type
ORDER BY day ASC, event_type ASC;
```

### Recent User Interactions

```sql
SELECT
    created_at,
    username,
    movie_title,
    event_type,
    details
FROM movie_event e
JOIN user u ON u.id = e.user_id
ORDER BY created_at DESC
LIMIT 100;
```

### Most Active Movies

```sql
SELECT
    movie_title,
    COUNT(*) AS total_events
FROM movie_event
GROUP BY movie_title
ORDER BY total_events DESC, movie_title ASC;
```

## Optional Analytics API

If you prefer a JSON feed instead of querying the database directly, the app now exposes:

- `GET /api/analytics/events?limit=100&username=alice&event_type=movie_added`
- `GET /api/analytics/events/summary`
- `GET /api/analytics/movies/popularity`
- `GET /api/analytics/users/activity`

These endpoints are useful if you want to plug the app into a small custom dashboard or an intermediate service before Grafana.
