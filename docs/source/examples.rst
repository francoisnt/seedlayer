********
Examples
********

This section contains complete, runnable examples demonstrating SeedLayer in real-world scenarios. All examples use the models from the ``example/`` directory.

Ecommerce Database Schema
=========================

The examples use this e-commerce schema with relationships:

.. code-block:: python

    # From example/models.py
    class Category(Base):
        __tablename__ = "categories"
        id = Column(Integer, primary_key=True, autoincrement=True)
        name = SeededColumn(String, seed=Seed("sentence", faker_kwargs={"nb_words": 2}), unique=True)
        description = SeededColumn(String, seed=Seed("sentence", faker_kwargs={"nb_words": 10}))

    class Customer(Base):
        __tablename__ = "customers"
        id = SeededColumn(Integer, primary_key=True, autoincrement=True)
        first_name = SeededColumn(String, seed=Seed("first_name"))
        last_name = SeededColumn(String, seed=Seed("last_name"))
        email = SeededColumn(String, seed=Seed("email"), unique=True)
        phone = SeededColumn(String, seed=Seed("phone_number"), nullable=True)

    class Product(Base):
        __tablename__ = "products"
        id = SeededColumn(Integer, primary_key=True, autoincrement=True)
        category_id = SeededColumn(Integer, ForeignKey("categories.id"), seed=None)
        name = SeededColumn(String, seed=Seed("product_name"), unique=True)
        price = SeededColumn(Float, seed=Seed("pyfloat", faker_kwargs={"min_value": 1.0, "max_value": 500.0}))

The models demonstrate:

- **Foreign key relationships** (Product.category_id → Category.id)
- **Unique constraints** on names and emails
- **Nullable columns** (Customer.phone)
- **Custom Seed configurations** for different column types
- **Precision handling** for prices (using ``pyfloat`` with ``right_digits``)

Basic Seeding Example
=====================

This is the exact code from ``example/dataseed.py``:

.. code-block:: python

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from seedlayer import SeedLayer
    from models import Base, Category, Customer, Order, OrderItem, Product

    # Setup database
    engine = create_engine("sqlite:///seeded_data.db", echo=False)
    Base.metadata.create_all(engine)

    # Define seed plan - just specify model:row count pairs
    seed_plan = {
        Category: 700,
        Product: 700,
        Customer: 700,
        Order: 700,
        OrderItem: 700,
    }

    Session = sessionmaker(bind=engine)
    with Session() as session:
        # Create seeder and generate data
        seed_layer = SeedLayer(session, seed_plan)
        seed_layer.seed()

**What happens:**

1. **Dependency Resolution**: SeedLayer analyzes foreign keys and generates tables in correct order: Category → Product → Customer → Order → OrderItem
2. **Data Generation**: Uses the custom ``Seed`` configurations from each model
3. **Constraint Handling**: Maintains uniqueness and referential integrity automatically

Custom Faker Provider
======================

The example includes a custom Faker provider for product names:

.. code-block:: python

    # From example/dataseed.py
    from faker.providers import BaseProvider

    class CustomCommerceProvider(BaseProvider):
        """Custom Faker provider for generating product names."""

        def product_name(self) -> str:
            adjectives = ["Awesome", "Practical", "Sleek", "Amazing", "Ergonomic"]
            sizes = ["Little", "Small", "Medium", "Large", "Big", "Extra Large"]
            colors = ["Red", "Blue", "Green", "Yellow", "White", "Silver"]
            materials = ["Steel", "Wooden", "Plastic", "Cotton", "Granite"]
            products = ["Bookshelf", "Cabinet", "Dresser", "Mattress", "Headset"]

            return f"""{self.random_element(adjectives)}
                     {self.random_element(sizes)}
                     {self.random_element(colors)}
                     {self.random_element(materials)}
                     {self.random_element(products)}
                     {self.random_int(min=1, max=9000)}"""

In the seeding code, this provider is added and configured:

.. code-block:: python

    # From example/dataseed.py
    with Session() as session:
        seed_layer = SeedLayer(session, seed_plan)

        # Reproducible results
        seed_layer.configure_faker(seed=42)

        # Add custom provider
        seed_layer.add_faker_provider(CustomCommerceProvider)

        # Generate data
        seed_layer.seed()

Example Output
==============

Running the example produces realistic e-commerce data with:

- **700 categories** with unique 2-word names and 10-word descriptions
- **700 products** with unique names, prices $1-500, linked to categories
- **700 customers** with realistic names, emails, and optional phone numbers
- **700 orders** with timestamps this year and totals $10-1000
- **700 order items** linking orders to products with quantities 1-10

The data maintains all foreign key relationships and constraints automatically.

Running the Example
===================

To run this example yourself:

1. Navigate to the ``example/`` directory
2. Run the seeder:

   .. code-block:: bash

       cd example
       python dataseed.py

3. Query the generated SQLite database:

   .. code-block:: python

       import sqlite3
       conn = sqlite3.connect('seeded_data.db')

       # See what got created
       cursor = conn.cursor()
       cursor.execute("SELECT count(*) FROM customers")
       print(f"Generated {cursor.fetchone()[0]} customers")

       # Sample some data
       cursor.execute("SELECT first_name, last_name, email FROM customers LIMIT 5")
       for row in cursor.fetchall():
           print(row)

Model Customization Examples
============================

Primary Key Handling
--------------------

SeedLayer automatically handles primary keys - you define them as autoincrement but SeedLayer lets the database manage them:

.. code-block:: python

    # ✅ Correct - database manages primary keys
    id = SeededColumn(Integer, primary_key=True, autoincrement=True)
    id = SeededColumn(Integer, primary_key=True, autoincrement=True)

Complex Seeds
-------------

Products use precise float generation:

.. code-block:: python

    # Prices with 2 decimal places, $1.00 to $500.00
    price = SeededColumn(
        Float,
        seed=Seed(
            "pyfloat",
            faker_kwargs={
                "min_value": 1.0,
                "max_value": 500.0,
                "right_digits": 2
            }
        ),
    )

Order totals use different ranges:

.. code-block:: python

    # Order totals $10.00 to $1000.00
    total_amount = SeededColumn(
        Float,
        seed=Seed(
            "pyfloat",
            faker_kwargs={
                "min_value": 10.0,
                "max_value": 1000.0,
                "right_digits": 2
            }
        ),
    )

Composite Primary Keys
----------------------

OrderItem uses a composite primary key (order_id, product_id):

.. code-block:: python

    class OrderItem(Base):
        __tablename__ = "order_items"
        order_id = SeededColumn(Integer, ForeignKey("orders.id"), primary_key=True, seed=None)
        product_id = SeededColumn(Integer, ForeignKey("products.id"), primary_key=True, seed=None)
        quantity = SeededColumn(Integer, seed=Seed("random_int", faker_kwargs={"min": 1, "max": 10}))
        unit_price = SeededColumn(Float, seed=Seed("pyfloat", faker_kwargs={"min_value": 1.0, "max_value": 500.0}))

Notes:

- Composite key columns have ``seed=None`` - SeedLayer fills them with valid FK values
- Quantity ranges from 1-10 items
- Unit price is independent of product price (could differ for discounts)

Link Table Pattern
-------------------

OrderItem is a "link table" - tables that only have foreign keys as primary keys automatically get cross-product seeding where SeedLayer generates all valid combinations within constraints.

Best Practices from Examples
===========================

1. **Use meaningful column names** that help identify their purpose
2. **Set appropriate constraints** (unique, nullable) that match real business rules
3. **Choose seed ranges** that reflect real-world data distributions
4. **Handle precision** carefully for monetary values (use ``right_digits``)
5. **Test your constraints** - run the seeder and check the generated data
6. **Use explicit Seeds** for complex requirements rather than relying on defaults

Next Steps
==========

- :doc:`troubleshooting` - Learn about logging and debugging
- `View source code <https://github.com/francoisnt/seedlayer/tree/main/example>`_ - Explore the complete example
