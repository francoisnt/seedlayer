import os

from faker.providers import BaseProvider
from sqlalchemy import create_engine

from seedlayer import SeedLayer
from seedlayer.types import SeedingPlan

from .models import Base, Category, Customer, Order, OrderItem, Product

# Setup database and seeding
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "seeded_data.db"))
engine = create_engine(f"sqlite:///{db_path}", echo=False)

# Delete existing DB if it exists
if os.path.exists(db_path):
    os.remove(db_path)

# Create the structure of the DB
Base.metadata.create_all(engine)


class CustomCommerceProvider(BaseProvider):
    """Custom Faker provider for generating product names."""

    def product_name(self) -> str:
        """Generate a random product name."""
        adjectives = ["Awesome", "Practical", "Sleek", "Amazing", "Ergonomic", "Gorgeous", "Gold"]
        sizes = ["Little", "Small", "Medium", "Regular", "Large", "Big", "Extra Large", "Jumbo"]
        colors = ["Red", "Blue", "Green", "Yellow", "White", "Silver"]
        materials = ["Steel", "Wooden", "Plastic", "Cotton", "Granite", "Leather"]
        products = ["Bookshelf", "Cabinet", "Dresser", "Mattress", "Headset", "Camera"]
        return " ".join(
            [
                self.random_element(adjectives),
                self.random_element(sizes),
                self.random_element(colors),
                self.random_element(materials),
                self.random_element(products),
                str(self.random_int(min=1, max=9000)),
            ]
        )


# Define seed plan:
seed_plan: SeedingPlan = {
    Category: 7000,
    Product: 7000,
    Customer: 7000,
    Order: 7000,
    OrderItem: 7000,
}

# Initiate SeedLayer with engine and plan
seed_layer = SeedLayer(engine, seed_plan)

# Set seed for reproducible results
seed_layer.configure_faker(seed=42)

# Add custom Faker provider
seed_layer.add_faker_provider(CustomCommerceProvider)

# Generate Data
seed_layer.seed()  # Always uses single transaction now
