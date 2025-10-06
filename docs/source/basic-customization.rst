*************************
Basic Data Customization
*************************

This guide covers the fundamentals of customizing how SeedLayer generates fake data.

SeededColumn Class
===================

To customize data generation, use the ``SeededColumn`` class instead of SQLAlchemy's ``Column`` in your model definitions.

The ``SeededColumn`` extends ``Column`` with two key parameters:

- ``seed`` - Defines how data is generated
- ``nullable_chance`` - Controls null value probability

Simple Usage
------------

Define a custom column with a specific Faker provider:

.. code-block:: python

    from seedlayer import SeededColumn
    from sqlalchemy import String, Integer
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        pass

    class User(Base):
        __tablename__ = "users"
        id = SeededColumn(Integer, primary_key=True, autoincrement=True)
        name = SeededColumn(String, seed="name")  # Generates realistic names
        email = SeededColumn(String, seed="email") # Generates email addresses

Controlling Null Values
-----------------------

By default, nullable columns have a 20% chance of generating ``None``. Adjust this with ``nullable_chance``:

.. code-block:: python

    class Product(Base):
        __tablename__ = "products"
        id = SeededColumn(Integer, primary_key=True, autoincrement=True)
        name = SeededColumn(String(100), seed="word")
        description = SeededColumn(
            Text,
            nullable=True,
            seed="sentence",
            nullable_chance=10  # Only 10% chance of null
        )

In this example:
- ``description`` is nullable
- There's a 10% chance it will be ``None`` instead of a generated sentence
- 90% of the time it will contain a realistic sentence

Available Seed Types
===================

String Seeds
-------------

Use Faker provider names as strings:

.. code-block:: python

    name = SeededColumn(String(100), seed="name")
    company = SeededColumn(String(100), seed="company")
    address = SeededColumn(String(200), seed="address")

Numeric Seeds
-------------

.. code-block:: python

    age = SeededColumn(Integer, seed="random_int")
    price = SeededColumn(Float, seed="random_float")

Date/Time Seeds
---------------

.. code-block:: python

    created_at = SeededColumn(DateTime, seed="date_time")
    birth_date = SeededColumn(Date, seed="date")

UUID Seeds
-----------

.. code-block:: python

    unique_id = SeededColumn(String(36), seed="uuid4")

The ``seed`` parameter accepts any valid Faker provider name. For precise control, use the ``Seed`` class covered in :doc:`advanced-features`.

Best Practices
==============

1. **Use descriptive column names** - Makes customizing easier later
2. **Set appropriate column lengths** - Match your domain requirements
3. **Consider nullability** - Adjust ``nullable_chance`` based on your data needs
4. **Test your seeds** - Verify the generated data matches your expectations

Next Steps
==========

For advanced customization options like inter-column dependencies:

- :doc:`advanced-features` - Learn about the ``Seed`` class and column references
- :doc:`examples` - See real-world customization examples
