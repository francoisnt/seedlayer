***************************
Further Customization
***************************

This guide covers global customization options including custom Faker providers, type defaults, and Faker configuration.

Overriding Type Defaults
=========================

Change default Faker providers for SQLAlchemy column types across your entire application. Instead of customizing each column individually, set global defaults.

Basic Usage
-----------

Pass a ``type_defaults`` dictionary when creating the ``SeedLayer``:

.. code-block:: python

    from sqlalchemy import Integer, String
    from seedlayer import SeedLayer, Seed
    from your_models import Product, User

    # Customize defaults for specific column types
    custom_type_defaults = {
        Integer: Seed(faker_provider="random_int", faker_kwargs={"min": 1000, "max": 9999}),
        String: Seed(faker_provider="sentence", faker_kwargs={"nb_words": 3}),
    }

    with Session(engine) as session:
        seeder = SeedLayer(
            session,
            {Product: 100, User: 50},
            type_defaults=custom_type_defaults
        )
        seeder.seed()

Now all ``Integer`` columns will generate values between 1000-9999, and all ``String`` columns will be 3-word sentences.

Common Type Overrides
---------------------

Override common types for domain-specific data:

.. code-block:: python

    from sqlalchemy import Float, DateTime, Date

    custom_defaults = {
        Float: Seed("random_float", faker_kwargs={"min": 0.0, "max": 100.0}),  # 0-100 range
        DateTime: Seed("date_time_this_year"),  # Only this year's dates
        Date: "date_this_year",  # String shorthand also works for simple cases
    }

    seeder = SeedLayer(session, seed_plan, type_defaults=custom_defaults)

Custom Faker Providers
======================

Extend Faker's capabilities with your own providers for domain-specific data.

Creating Custom Providers
-------------------------

Define a custom provider inheriting from Faker's ``BaseProvider``:

.. code-block:: python

    from faker.providers import BaseProvider

    class CustomProvider(BaseProvider):
        def product_code(self):
            """Generate custom product codes"""
            return f"PROD-{self.random_int(min=1000, max=9999)}"

        def support_tier(self):
            """Generate support tiers"""
            return self.random_element(["basic", "premium", "enterprise"])

Adding to SeedLayer
-------------------

Register your custom provider with SeedLayer:

.. code-block:: python

    from my_providers import CustomProvider

    with Session(engine) as session:
        seeder = SeedLayer(session, seed_plan)
        seeder.add_faker_provider(CustomProvider)

        # Now you can use your custom providers
        class Product(Base):
            __tablename__ = "products"
            id = SeededColumn(Integer, primary_key=True, autoincrement=True)
            code = SeededColumn(String(20), seed="product_code")
            tier = SeededColumn(String(20), seed="support_tier")

        seeder.seed()

Multiple Providers
------------------

Add multiple custom providers:

.. code-block:: python

    class EcommerceProvider(BaseProvider):
        def category_name(self):
            return self.random_element([
                "Electronics", "Clothing", "Books", "Home & Garden", "Sports"
            ])

    class UserProvider(BaseProvider):
        def account_status(self):
            return self.random_element(["active", "inactive", "suspended"])

    # Add both providers
    seeder.add_faker_provider(EcommerceProvider)
    seeder.add_faker_provider(UserProvider)

Faker Configuration
===================

Control Faker's global behavior with localization and reproducible seeding.

Setting Locale
---------------

Generate data in specific languages or regions:

.. code-block:: python

    with Session(engine) as session:
        seeder = SeedLayer(session, seed_plan)

        # Generate French data
        seeder.configure_faker(locale="fr_FR")
        seeder.seed()

    # Or use multiple locales dynamically
    locales = ["en_US", "es_ES", "de_DE", "fr_FR"]

    for locale in locales:
        seeder.configure_faker(locale=locale)
        # Generate data for this locale

Reproducible Results
--------------------

Use seeds for consistent data generation across runs:

.. code-block:: python

    with Session(engine) as session:
        seeder = SeedLayer(session, seed_plan)

        # Same seed = same fake data every time
        seeder.configure_faker(seed=42, locale="en_US")
        seeder.seed()
        # Will generate identical data on every run

Combined Configuration
----------------------

Use both seed and locale together:

.. code-block:: python

    # Reproducible results in French
    seeder.configure_faker(seed=123, locale="fr_FR")

    # Switch to reproducible results in Spanish
    seeder.configure_faker(seed=123, locale="es_ES")

Advanced Provider Combinations
-------------------------------

Create complex scenarios by combining custom providers with configuration:

.. code-block:: python

    class LocalizedProductProvider(BaseProvider):
        def product_name_de(self):
            return self.random_element([
                "Laptop", "Telefon", "Buch", "Auto", "Haus"
            ])

        def product_name_fr(self):
            return self.random_element([
                "Ordinateur", "Téléphone", "Livre", "Voiture", "Maison"
            ])

    seeder.add_faker_provider(LocalizedProductProvider)

    # Use German product names
    seeder.configure_faker(locale="de_DE")
    # Products will get German names

    # Switch to French
    seeder.configure_faker(locale="fr_FR")
    # Products get French names

Provider Preservation
=====================

When changing locales or configurations, SeedLayer preserves your custom providers automatically. You don't need to re-add them.

Best Practices
==============

1. **Provider naming** - Use descriptive provider method names
2. **Configuration consistency** - Choose locales that match your use case
3. **Seed management** - Use fixed seeds for testing, random for development
4. **Provider efficiency** - Keep custom providers lightweight

Performance Notes
=================

- Custom providers add overhead - use them where Faker defaults aren't sufficient
- Provider registration is done once per SeedLayer instance
- Locale switching re-initializes Faker internally and re-adds custom providers

Example Complete Setup
======================

Here's a comprehensive example putting it all together:

.. code-block:: python

    from faker.providers import BaseProvider
    from seedlayer import SeedLayer, Seed
    from sqlalchemy import Integer, String
    from my_app.models import User, Product, Order

    # Custom provider
    class AppProvider(BaseProvider):
        def account_type(self):
            return self.random_element(["free", "premium", "enterprise"])

    # Custom type defaults
    custom_defaults = {
        Integer: Seed("random_int", faker_kwargs={"min": 1, "max": 1000}),
        String: "word",  # Simple string fallback
    }

    # Setup seeder
    seed_plan = {User: 100, Product: 50, Order: 200}

    with Session(engine) as session:
        seeder = SeedLayer(session, seed_plan, type_defaults=custom_defaults)

        # Add custom provider
        seeder.add_faker_provider(AppProvider)

        # Configure for reproducible, localized data
        seeder.configure_faker(seed=42, locale="en_US")

        seeder.seed()

Next Steps
==========

See real-world usage examples:

- :doc:`examples` - Complete examples using the features above
