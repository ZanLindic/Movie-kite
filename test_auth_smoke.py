import os
import tempfile
import unittest

from werkzeug.security import check_password_hash

os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/movieDB")
os.environ.setdefault("SECRET_KEY", "test-secret")

from main import create_app
from extensions import db
from models import User


class AuthSmokeTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "test_movies.db")
        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_path}"

        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.temp_dir.cleanup()
        os.environ.pop("DATABASE_URL", None)

    def test_register_login_session_and_hash(self):
        register_response = self.client.post(
            "/api/auth/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "password": "Secret123!",
            },
        )
        self.assertEqual(register_response.status_code, 201)

        with self.client as client:
            me_response = client.get("/api/auth/me")
            self.assertEqual(me_response.status_code, 200)
            self.assertEqual(me_response.get_json()["user"]["username"], "alice")

            logout_response = client.post("/api/auth/logout")
            self.assertEqual(logout_response.status_code, 200)

            login_response = client.post(
                "/api/auth/login",
                json={"identifier": "alice@example.com", "password": "Secret123!"},
            )
            self.assertEqual(login_response.status_code, 200)

            me_again_response = client.get("/api/auth/me")
            self.assertEqual(me_again_response.status_code, 200)
            self.assertEqual(me_again_response.get_json()["user"]["email"], "alice@example.com")

        with self.app.app_context():
            user = User.query.filter_by(username="alice").first()
            self.assertIsNotNone(user)
            self.assertNotEqual(user.password_hash, "Secret123!")
            self.assertTrue(check_password_hash(user.password_hash, "Secret123!"))


if __name__ == "__main__":
    unittest.main()
