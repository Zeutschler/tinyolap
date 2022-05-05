from locust import HttpUser, between, task


class TinyOlapGraphqlUser(HttpUser):
    wait_time = between(5, 15)
    host = "http://127.0.0.1:8000/"

    @task(20)
    def random_read(self):
        response = self.client.get("/random_read/")
        # response = self.client.post("/", response = self.client.post("/login", {"username":"testuser", "password":"secret"}))
        print("Response text:", response.text)

    @task(1)
    def random_write(self):
        response = self.client.get("/random_write/")
        print("Response text:", response.text)
