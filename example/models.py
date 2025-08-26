from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import declarative_base, Session
from faker.providers import BaseProvider
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from seedlayer import (
    SeededColumn,
    ColumnReference,
    Seed,
)

Base = declarative_base()

class CustomCommerceProvider(BaseProvider):
    def product_name(self):
        adjectives = ['Awesome', 'Practical', 'Sleek', 'Ergonomic', 'Gorgeous']
        size = ["Little", "Medium", "Regular", "Large", "Extra Large"]
        color = []
        materials = ['Steel', 'Wooden', 'Plastic', 'Cotton', 'Granite']
        products = ['Chair', 'Table', 'Shoes', 'Keyboard', 'Lamp']
        return f"{self.random_element(adjectives)} {self.random_element(materials)} {self.random_element(products)}"


class Category(Base):
    __tablename__ = "categories"
    id = SeededColumn(Integer, primary_key=True, autoincrement=True)
    name = SeededColumn(String, seed=Seed("sentence", faker_kwargs={"nb_words": 2}), unique=True)
    description = SeededColumn(String, seed=Seed("sentence", faker_kwargs={"nb_words": 10}))

class Product(Base):
    __tablename__ = "products"
    id = SeededColumn(Integer, primary_key=True, autoincrement=True)
    category_id = SeededColumn(Integer, ForeignKey("categories.id"), seed=None)
    name = SeededColumn(
        String,        seed=Seed(            "product_name"        ),        unique=True
    )
    price = SeededColumn(Float, seed=Seed("pyfloat", faker_kwargs={"min_value": 1.0, "max_value": 500.0, "right_digits": 2}))

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
    total_amount = SeededColumn(Float, seed=Seed("pyfloat", faker_kwargs={"min_value": 10.0, "max_value": 1000.0, "right_digits": 2}))

class OrderItem(Base):
    __tablename__ = "order_items"
    order_id = SeededColumn(Integer, ForeignKey("orders.id"), primary_key=True, seed=None)
    product_id = SeededColumn(Integer, ForeignKey("products.id"), primary_key=True, seed=None)
    quantity = SeededColumn(Integer, seed=Seed("random_int", faker_kwargs={"min": 1, "max": 10}))
    unit_price = SeededColumn(Float, seed=Seed("pyfloat", faker_kwargs={"min_value": 1.0, "max_value": 500.0, "right_digits": 2}))