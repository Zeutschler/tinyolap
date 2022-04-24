from locust import HttpUser, between, task


class TinyOlapRestUser(HttpUser):
    wait_time = between(2, 10)
    host = "http://127.0.0.1:8000/"

    @task(4)
    def random_read(self):
        response = self.client.get("read")
        # response = self.client.post("/", response = self.client.post("/login", {"username":"testuser", "password":"secret"}))
        # print("Response text:", response.text)

    @task(1)
    def random_write(self):
        response = self.client.get("write")
        # print("Response text:", response.text)