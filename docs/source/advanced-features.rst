*********************
Advanced Features
*********************

This section covers powerful features for complex data generation scenarios including custom Faker providers and inter-column dependencies.

The Seed Class
==============

The ``Seed`` class provides precise control over Faker provider behavior. Use it when you need to specify provider arguments or options.

Basic Usage
-----------

Instead of a string, pass a ``Seed`` object to get exact control:

.. code-block:: python

    from seedlayer import SeededColumn, Seed
    from sqlalchemy import Integer, Float

    class Product(Base):
        __tablename__ = "products"
        id = SeededColumn(Integer, primary_key=True, autoincrement=True)
        price = SeededColumn(
            Float,
            seed=Seed(
                faker_provider="random_float",
                faker_kwargs={"min": 10.0, "max": 500.0}
            )
        )

This generates prices between $10.00 and $500.00.

Controlling Constraints
-----------------------

Perfect for generating values within specific ranges:

.. code-block:: python

    class Person(Base):
        __tablename__ = "people"
        id = SeededColumn(Integer, primary_key=True, autoincrement=True)
        age = SeededColumn(
            Integer,
            seed=Seed(
                faker_provider="random_int",
                faker_kwargs={"min": 18, "max": 80}
            )
        )
        height_cm = SeededColumn(
            Integer,
            seed=Seed(
                faker_provider="random_int",
                faker_kwargs={"min": 150, "max": 210}
            )
        )

Advanced Text Generation
-------------------------

Control sentence/paragraph structure:

.. code-block:: python

    class Article(Base):
        __tablename__ = "articles"
        id = SeededColumn(Integer, primary_key=True, autoincrement=True)
        title = SeededColumn(String(200), seed="sentence")
        content = SeededColumn(
            Text,
            seed=Seed(
                faker_provider="paragraph",
                faker_kwargs={"nb_sentences": 5}
            )
        )

ColumnReference - Inter-Column Dependencies
===========================================

Create logical relationships between columns using ``ColumnReference``. This allows one column's generated value to affect another's generation.

Basic Relationship
------------------

Make column values depend on other columns in the same row:

.. code-block:: python

    from seedlayer import ColumnReference

    class Product(Base):
        __tablename__ = "products"
        id = SeededColumn(Integer, primary_key=True, autoincrement=True)
        name = SeededColumn(String(100), seed="word")
        description = SeededColumn(
            Text,
            seed=Seed(
                faker_provider="sentence",
                faker_kwargs={
                    "nb_words": ColumnReference("name", transform=lambda x: len(x.split()) + 5)
                }
            )
        )

Here, the description length is based on the name - longer names generate longer descriptions.

Transform Functions
-------------------

Use transform functions to modify referenced values:

.. code-block:: python

    class User(Base):
        __tablename__ = "users"
        id = SeededColumn(Integer, primary_key=True, autoincrement=True)
        first_name = SeededColumn(String(50), seed="first_name")
        last_name = SeededColumn(String(50), seed="last_name")
        email = SeededColumn(
            String(255),
            seed=Seed(
                faker_provider="email",
                faker_kwargs={
                    "domain": ColumnReference(
                        ["first_name", "last_name"],
                        transform=lambda f, l: f"{f.lower()}.{l.lower()}@example.com"
                    )
                }
            )
        )

The email combines first and last names into a custom format.

Multiple References
-------------------

Reference multiple columns at once:

.. code-block:: python

    class Order(Base):
        __tablename__ = "orders"
        id = SeededColumn(Integer, primary_key=True, autoincrement=True)
        customer_id = SeededColumn(Integer, nullable=False)
        product_name = SeededColumn(String(100), seed="word")
        notes = SeededColumn(
            Text,
            nullable=True,
            seed=Seed(
                faker_provider="sentence",
                faker_kwargs={
                    "nb_words": ColumnReference(
                        "product_name",
                        transform=lambda name: min(len(name) // 2 + 3, 20)
                    )
                }
            ),
            nullable_chance=70
        )

Complex Scenarios
=================

Country-Based Data
-------------------

Use references to create geographically consistent data:

.. code-block:: python

    class Address(Base):
        __tablename__ = "addresses"
        id = SeededColumn(Integer, primary_key=True, autoincrement=True)
        country = SeededColumn(String(50), seed="country")
        city = SeededColumn(
            String(100),
            seed=Seed(
                faker_provider="city",
                locale=ColumnReference("country", transform=lambda c: c.lower()[:2])
            )
        )

This attempts to use the country's locale for city generation.

Mathematical Relationships
--------------------------

Create columns that relate mathematically:

.. code-block:: python

    class Project(Base):
        __tablename__ = "projects"
        id = SeededColumn(Integer, primary_key=True, autoincrement=True)
        estimated_hours = SeededColumn(
            Integer,
            seed=Seed("random_int", faker_kwargs={"min": 10, "max": 100})
        )
        actual_hours = SeededColumn(
            Integer,
            seed=Seed(
                faker_provider="random_int",
                faker_kwargs={
                    "min": ColumnReference("estimated_hours", transform=lambda e: int(e * 0.8)),
                    "max": ColumnReference("estimated_hours", transform=lambda e: int(e * 1.5))
                }
            )
        )

Actual hours vary around the estimate (±50%).

Best Practices
==============

1. **Test references carefully** - Ensure referenced columns exist and have valid data
2. **Use transforms efficiently** - Keep transform functions simple
3. **Handle edge cases** - Account for potential null/invalid values in transforms
4. **Design for readability** - Complex relationships can become hard to maintain

Performance Considerations
==========================

- ``ColumnReference`` transforms run during seeding, so keep them lightweight
- Complex interdependencies may affect seeding performance on large datasets
- Consider using fixed values for frequently-referenced data

Next Steps
==========

Learn about global configuration and type overrides:

- :doc:`further-customization` - Custom providers and global settings
- :doc:`examples` - See complex real-world scenarios
