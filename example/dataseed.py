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


# Create a session
Session = sessionmaker(bind=engine)
session = Session()

# Define seed plan: 5 users, 10 orders
seed_plan = {
    Category: 700,
    Product: 700,
    Customer: 700,
    Order: 700,
    OrderItem: 700,
}

# Initiate SeedLayer with session and plan
seed_layer = SeedLayer(session, seed_plan)

seed_layer.add_faker_provider(CustomCommerceProvider)

# Seed the database
seed_layer.seed()

# # Create and run seeder
# with Session(engine) as session:
#     seeder = SeedLayer(session, seed_plan, faker=Faker())
#     seeder.configure_faker(seed=42)  # Set seed for reproducible results
#     seeder.seed()

#     # Query results to verify
#     print("Seeded Users:")
#     for user in session.query(User).all():
#         print(f"  {user.id}: {user.username} ({user.email})")

#     print("\nSeeded Orders:")
#     for order in session.query(Order).all():
#         print(f"  {order.id}: User {order.user_id}, Date {order.order_date}, \
#               Amount {order.amount}")
