***********
Quick Start
***********

This guide shows you how to get SeedLayer up and running with minimal setup.

Installation
============

Install SeedLayer with pip:

.. code-block:: bash

    pip install seedlayer

SeedLayer requires:

- Python 3.8+
- SQLAlchemy 2.0+
- Faker 20.0+

Getting Started
===============

Here's the simplest way to use SeedLayer. Just create a dictionary mapping your models to how many rows you want, and SeedLayer handles the rest.

.. code-block:: python

    # Import SeedLayer and your models
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from seedlayer import SeedLayer
    from your_models import Base, Category, Customer, Order

    # Define how many rows you want for each model
    seed_plan = {
        Category: 50,
        Customer: 100,
        Order: 200,
    }

    # Create your database engine and tables
    engine = create_engine("sqlite:///seeded_data.db", echo=False)
    Base.metadata.create_all(engine)

    # Seed your data
    with Session(engine) as session:
        seeder = SeedLayer(session, seed_plan)
        seeder.seed()

**Output:**

.. code-block:: text

    2025-08-27 15:08:33,652 [INFO] seedlayer.seedlayer: Model seeding order: ['Category', 'Customer', 'Order']
    2025-08-27 15:08:33,652 [INFO] seedlayer.seedlayer: Seeding 50 rows for Category
    2025-08-27 15:08:34,005 [INFO] seedlayer.seedlayer: Seeding 100 rows for Customer
    2025-08-27 15:08:34,393 [INFO] seedlayer.seedlayer: Seeding 200 rows for Order

What Just Happened?
===================

SeedLayer automatically:

1. **Resolved dependencies** - It analyzed your models and figured out the correct order to seed them based on foreign key relationships.

2. **Generated realistic data** - Used Faker's default providers for each column type (strings, numbers, dates, etc.).

3. **Handled constraints** - Primary keys are managed by the database, and it respects unique constraints and foreign key relationships.

Next Steps
==========

- :doc:`basic-customization` - Learn how to customize data generation
- :doc:`examples` - See more complex real-world examples
