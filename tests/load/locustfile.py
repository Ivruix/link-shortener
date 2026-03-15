from locust import HttpUser, task, between
import random


class LinkShortenerUser(HttpUser):
    wait_time = between(1, 3)
    short_codes = []

    def on_start(self):
        response = self.client.post("/auth/register", json={
            "username": f"user_{random.randint(1000, 9999)}",
            "password": "testpass123"
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def create_link(self):
        urls = [
            "https://example.com",
            "https://google.com",
            "https://github.com",
            "https://stackoverflow.com"
        ]
        self.client.post("/links/shorten", json={
            "original_url": random.choice(urls)
        }, headers=getattr(self, "headers", {}))

    @task(10)
    def redirect_link(self):
        if self.short_codes:
            code = random.choice(self.short_codes)
            self.client.get(f"/links/{code}", follow_redirects=False)

    @task(1)
    def get_stats(self):
        if self.short_codes:
            code = random.choice(self.short_codes)
            self.client.get(f"/links/{code}/stats")

    @task(1)
    def update_link(self):
        if self.short_codes and hasattr(self, "headers"):
            code = random.choice(self.short_codes)
            self.client.put(f"/links/{code}", json={
                "original_url": "https://updated.com"
            }, headers=self.headers)
