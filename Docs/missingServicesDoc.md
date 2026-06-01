## Services implemented
1. User registration/login
2. Movie poster storage & viewing

## Notes
- Posters are uploaded through `posterStorageService.py` and proxied back through `/movies/poster` for frontend rendering.
- Auth uses session-based login/logout in `authService.py`.