import os
import sys

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from seedlayer import (
    Seed,
    SeededColumn,
)

Base = declarative_base()


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = SeededColumn(String, seed=Seed("sentence", faker_kwargs={"nb_words": 2}), unique=True)
    description = SeededColumn(String, seed=Seed("sentence", faker_kwargs={"nb_words": 10}))


class Product(Base):
    __tablename__ = "products"
    id = SeededColumn(Integer, primary_key=True, autoincrement=True)
    category_id = SeededColumn(Integer, ForeignKey("categories.id"), seed=None)
    name = SeededColumn(String, seed=Seed("product_name"), unique=True)
    price = SeededColumn(
        Float,
        seed=Seed(
            "pyfloat", faker_kwargs={"min_value": 1.0, "max_value": 500.0, "right_digits": 2}
        ),
    )


class Customer(Base):
    __tablename__ = "customers"
    id = SeededColumn(Integer, primary_key=True, autoincrement=True)
    first_name = SeededColumn(String, seed=Seed("first_name"))
    last_name = SeededColumn(String, seed=Seed("last_name"))
    email = SeededColumn(String, seed=Seed("email"), unique=True)
    phone = SeededColumn(String, seed=Seed("phone_number"), nullable=True)


class Order(Base):
    __tablename__ = "orders"
    id = SeededColumn(Integer, primary_key=True, autoincrement=True)
    customer_id = SeededColumn(Integer, ForeignKey("customers.id"), seed=None)
    order_date = SeededColumn(DateTime, seed=Seed("date_time_this_year"))
    total_amount = SeededColumn(
        Float,
        seed=Seed(
            "pyfloat", faker_kwargs={"min_value": 10.0, "max_value": 1000.0, "right_digits": 2}
        ),
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    order_id = SeededColumn(Integer, ForeignKey("orders.id"), primary_key=True, seed=None)
    product_id = SeededColumn(Integer, ForeignKey("products.id"), primary_key=True, seed=None)
    quantity = SeededColumn(Integer, seed=Seed("random_int", faker_kwargs={"min": 1, "max": 10}))
    unit_price = SeededColumn(
        Float,
        seed=Seed(
            "pyfloat", faker_kwargs={"min_value": 1.0, "max_value": 500.0, "right_digits": 2}
        ),
    )
