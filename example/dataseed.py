# import sys
import os

from faker.providers import BaseProvider
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from seedlayer import SeedLayer

from .models import Base, Category, Customer, Order, OrderItem, Product

# Setup database and seeding
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "seeded_data.db"))
engine = create_engine(f"sqlite:///{db_path}", echo=False)
Base.metadata.create_all(engine)


class CustomCommerceProvider(BaseProvider):
    def product_name(self):
        adjectives = ["Awesome", "Practical", "Sleek", "Amazing", "Ergonomic", "Gorgeous", "Gold"]
        sizes = ["Little", "Small", "Medium", "Regular", "Large", "Big", "Extra Large", "Jumbo"]
        colors = ["Red", "Blue", "Green", "Yellow", "White", "Silver"]
        materials = ["Steel", "Wooden", "Plastic", "Cotton", "Granite", "Leather"]
        products = ["Bookshelf", "Cabinet", "Dresser", "Mattress", "Headset", "Camera"]
        return f"\
            {self.random_element(adjectives)} \
            {self.random_element(sizes)} \
            {self.random_element(colors)} \
            {self.random_element(materials)} \
            {self.random_element(products)} \
            {self.random_int(min=1, max=9000)} "


# Define seed plan:
seed_plan = {
    Category: 700,
    Product: 700,
    Customer: 700,
    Order: 700,
    OrderItem: 700,
}

Session = sessionmaker(bind=engine)
with Session() as session:
    # Initiate SeedLayer with session and plan
    seed_layer = SeedLayer(session, seed_plan)

    # Set seed for reproducible results
    seed_layer.configure_faker(seed=42)

    # Add custom Faker provider
    seed_layer.add_faker_provider(CustomCommerceProvider)

    # Generate Data
    seed_layer.seed()
