SeedLayer Documentation
=======================

.. image:: https://img.shields.io/pypi/v/seedlayer.svg?style=flat-square
   :target: https://pypi.org/project/seedlayer/
   :alt: PyPI Version

.. image:: https://img.shields.io/badge/python-3.8+-blue.svg?style=flat-square
   :target: https://www.python.org/downloads/
   :alt: Python Version

SeedLayer is a **declarative** Python library designed to simplify the process of seeding SQLAlchemy database models with realistic fake data. By leveraging the Faker library, it generates data for SQLAlchemy models in a declarative manner, allowing users to define seeding behavior directly within model definitions.

**Works automatically:**

- Generates realistic fake data without model changes
- Respects primary key, foreign key, and unique constraints
- Handles model dependencies and column inter-dependencies
- Supports custom Faker providers and locale configuration

Getting Started
===============

**Installation:**

.. code-block:: bash

    pip install seedlayer

**Basic Usage:**

.. code-block:: python

    from seedlayer import SeedLayer, SeededColumn
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        seeder = SeedLayer(session, {YourModel: 100})
        seeder.seed()

**With Model Customization:**

.. code-block:: python

    class User(Base):
        id = SeededColumn(Integer, primary_key=True, autoincrement=True)
        name = SeededColumn(String, seed="name")
        email = SeededColumn(String, seed="email", unique=True)

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   quickstart

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   basic-customization
   advanced-features
   further-customization
   examples

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/modules
   troubleshooting

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
