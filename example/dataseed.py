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
        adjectives = [
            "Awesome",
            "Practical",
            "Sleek",
            "Ergonomic",
            "Gorgeous",
            "Innovative",
            "Stylish",
        ]
        sizes = [
            "Little",
            "Medium",
            "Regular",
            "Large",
            "Extra Large",
            "Small",
            "Big",
            "Mini",
            "Jumbo",
            "Standard",
        ]
        colors = [
            "Red",
            "Blue",
            "Green",
            "Black",
            "White",
            "Silver",
            "Gold",
            "Purple",
            "Yellow",
            "Gray",
        ]
        materials = [
            "Steel",
            "Wooden",
            "Plastic",
            "Cotton",
            "Granite",
            "Leather",
            "Glass",
            "Ceramic",
            "Metal",
            "Fabric",
        ]
        products = [
            "Bookshelf",
            "Cabinet",
            "Dresser",
            "Mattress",
            "Headset",
            "Camera",
            "Printer",
            "Tablet",
            "Phone",
            "Charger",
            "Fan",
            "Heater",
            "Blender",
            "Toaster",
            "Kettle",
            "Microwave",
            "Vase",
            "Candle",
            "Frame",
        ]
        return f"\
            {self.random_element(adjectives)} \
            {self.random_element(sizes)} \
            {self.random_element(colors)} \
            {self.random_element(materials)} \
            {self.random_element(products)} \
            "


# Define seed plan:
seed_plan = {
    Category: 20000,
    Product: 20000,
    Customer: 20000,
    Order: 20000,
    OrderItem: 20000,
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
