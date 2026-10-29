"""Read-only load scenario. Never target a production site."""
import os
from locust import HttpUser,task,between

class ProductReader(HttpUser):
    wait_time=between(.2,.5)
    def on_start(self):
        self.client.headers.update({'Authorization':'Bearer '+os.environ['PRACTICE_CUSTOMER_TOKEN']})
    @task
    def products(self):
        self.client.get('/commerce/catalog',name='商品查询')
