from locust import HttpUser, between, task


class TinyOlapRestUser(HttpUser):
    wait_time = between(1, 2)
    host = "http://127.0.0.1:8000/"

    @task(4)
    def random_read(self):
        response = self.client.get("cells/")

    @task(1)
    def random_write(self):
        response = self.client.put("cells/")

    @task(10)
    def random_view(self):
        response = self.client.get("views/")


