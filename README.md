# Declarative Fake Data Seeder for SQLAlchemy ORM

## Overview

SeedLayer is a **declarative** Python library designed to simplify the process of seeding [SQLAlchemy](https://www.sqlalchemy.org/) database models with realistic fake data. By leveraging the [Faker](https://faker.readthedocs.io/en/stable/index.html) library, it generates data for SQLAlchemy models in a declarative manner, allowing users to define seeding behavior directly within model definitions. It respects primary key (PK), foreign key (FK), and unique constraints, while automatically handling model and inter-column dependencies to ensure valid data generation. This makes it ideal for testing, development, and demo environments.

### Benefits

- **Declarative Configuration**: Create a simple seed plan, and SeedLayer manages the rest.
- **Automated Data Generation**: Generates realistic fake data using `Faker` providers.
- **Dependency Management**: Automatically resolves foreign key dependencies.
- **Inter-Column Dependency Support**: Handles dependencies between columns within the same model.
- **Unique Constraint Support**: Ensures unique columns remain unique by tracking used values and generating new ones as needed.
- **Link Table Support**: Handles link tables (tables that represent many-to-many relationships) by generating valid combinations of foreign key values.
- **Type Defaults**: Uses sensible default Faker providers for common SQLAlchemy column types (e.g., `Integer`, `String`, `DateTime`, `Float`, `UUID`).
- **Extensible**: Supports custom `Faker` providers and locale configuration for tailored data generation of each model.

### Requirements

1. **Declarative Base Models**: Models must inherit from `sqlalchemy.orm.DeclarativeBase`.
2. **Primary Keys**: Each model, other than link tables, must have a single primary key that is autoincremented. SeedLayer doesn't create a value for the primary key; it relies on the database managing them.
3. **Foreign Key Constraints**: Foreign keys must reference a valid primary key column in other tables within the provided `SeedPlan`. The library assumes single foreign key constraints per column (multiple FKs per column are not supported).
4. **Link Tables**: If a model's primary keys are all also foreign keys, it is treated as a link table, and the library generates valid combinations of foreign key values. The seed plan must not specify more rows than possible combinations of the combined primary key values.
5. **Session Management**: A valid SQLAlchemy `Session` object must be provided for database operations.

## Compatibility

SeedLayer requires:
    - Python 3.8 or higher
    - SQLAlchemy 2.0 or higher
    - Faker 20.0 or higher

## Usage

### Getting Started Without Any Change to Your Models

1. **Install**:

   ```bash
   pip install seedlayer
   ```

2. **Create Seed File** (e.g., `dataseed.py`):

   ```python
   # Import seedlayer and your models
   from sqlalchemy import create_engine
   from sqlalchemy.orm import Session
   from seedlayer import SeedLayer
   from .models import Base, Category, Customer, Order, OrderItem, Product

   # Create your declarative seed plan, a python dict with your models as key and the number of rows you want to seed as value for each of them.
   # No need to mind the order, SeedLayer will automatically sort your models correctly and notify you in case of circular dependency.
   seed_plan = {
       Category: 700,
       Product: 700,
       Customer: 700,
       Order: 700,
       OrderItem: 700,
   }

   # Create an engine for your database
   engine = create_engine("sqlite:///seeded_data.db", echo=False)

   # If needed, create database tables based on your models
   Base.metadata.create_all(engine)

   with Session(engine) as session:
       # Provide SeedLayer with a valid database session and your seed plan
       seeder = SeedLayer(session, seed_plan)

       # Generate your data
       seeder.seed()
   ```

3. **Run Your File as a Module**:

   ```bash
   python -m example.dataseed
   ```

4. **SeedLayer Output**:
   SeedLayer will determine the correct order to seed tables based on their dependencies and then generate data for each using the default Faker provider for every column type.

   ```txt
   2025-08-27 15:08:33,652 [INFO] seedlayer.seedlayer: Model seeding order: ['Category', 'Customer', 'Product', 'Order', 'OrderItem']
   2025-08-27 15:08:33,652 [INFO] seedlayer.seedlayer: Seeding 700 rows for Category
   2025-08-27 15:08:34,005 [INFO] seedlayer.seedlayer: Seeding 700 rows for Customer
   2025-08-27 15:08:34,393 [INFO] seedlayer.seedlayer: Seeding 700 rows for Product
   2025-08-27 15:08:34,651 [INFO] seedlayer.seedlayer: Seeding 700 rows for Order
   2025-08-27 15:08:34,933 [INFO] seedlayer.seedlayer: Seeding 700 rows for OrderItem
   ```

5. **Verify Data**:
   Open your database in your favorite client to see the newly added data.

### Customizing Data Generation

SeedLayer provides powerful tools to tailor fake data generation for your SQLAlchemy models, allowing fine-grained control over how data is created. Three key classes enable this customization, making it easy to generate realistic and contextually relevant data while respecting model constraints.

1. **SeededColumn Class**
    The `SeededColumn` class extends SQLAlchemy's `Column` class, adding two key parameters to customize data generation: `seed` and `nullable_chance`. These parameters allow fine-grained control over how fake data is generated for specific columns while respecting model constraints like uniqueness and nullability. Use `SeededColumn` in your model definitions to override default data generation behavior.

    - **Seed Parameter**: The `seed` parameter defines how fake data is generated for the column. It accepts either:
        - A string specifying a valid `Faker` provider (e.g., `"name"`, `"email"`, `"random_int"`), which uses the provider's default behavior.
        - A `Seed` object for advanced configuration, allowing you to specify provider arguments, keyword arguments, or dependencies on other columns via `ColumnReference`.  
        This parameter enables you to tailor data to your application's needs, such as generating realistic names, constrained numbers, or custom formats.

    - **Nullable Chance Parameter**: The `nullable_chance` parameter (default: 20) is an integer between 0 and 100 that specifies the percentage chance that a nullable column (i.e., a column with `nullable=True`) will generate a `None` value instead of fake data. This is useful for simulating real-world scenarios where optional fields may be unset. For example, a `nullable_chance=10` means a 10% chance of generating `None`. If the column is not nullable, this parameter is ignored.

    **Example**:

    ```python
    from seedlayer import SeededColumn, Seed
    from sqlalchemy import Integer, String
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        pass

    class User(Base):
        __tablename__ = "users"
        id = SeededColumn(Integer, primary_key=True, autoincrement=True)
        name = SeededColumn(String, seed="name")  # Uses Faker's name provider
        age = SeededColumn(
            Integer,
            nullable=True,
            seed=Seed(faker_provider="random_int", faker_kwargs={"min": 18, "max": 80}),
            nullable_chance=10
        )  # 10% chance of generating None
    ```

    In this example:
    - The `name` column uses the `seed="name"` parameter to generate realistic names using Faker's `name` provider.
    - The `age` column uses a `Seed` object to generate random integers between 18 and 80, with a 10% chance of being `None` due to `nullable_chance=10`.

    For users who have their own custom SQLAlchemy `Column` subclasses (e.g., for additional functionality like custom validation or metadata), the `SeededColumnMixin` can be combined with your custom `Column` class to add seeding capabilities without replacing your existing customizations.

    **Example with SeededColumnMixin**:

    ```python
    from sqlalchemy import Column, Integer, String
    from seedlayer import SeededColumnMixin

    # Custom Column class with additional functionality
    class CustomColumn(Column):
        def __init__(self, *args, custom_metadata=None, **kwargs):
            self.custom_metadata = custom_metadata or {}
            super().__init__(*args, **kwargs)

    # Combine with SeededColumnMixin
    class SeededCustomColumn(SeededColumnMixin, CustomColumn):
        inherit_cache = True  # Enable SQLAlchemy compilation caching for performance
    ```

    In this example:

    - `CustomColumn` adds a `custom_metadata` parameter for additional functionality.
    - `SeededCustomColumn` combines `SeededColumnMixin` with `CustomColumn`, enabling both seeding and custom metadata.
    - The `inherit_cache = True` attribute is added to `SeededCustomColumn` to enable SQLAlchemy's query compilation caching, improving performance for repeated queries.

2. **Seed Class**  
    The `Seed` class allows advanced configuration of `Faker` providers by specifying provider arguments and keyword arguments. This is useful for generating data with specific constraints, such as ranges for numbers or custom formats. The `Seed` class is passed to the `seed` parameter of `SeededColumn` for precise control.

    **Example**:

    ```python
    from seedlayer import SeededColumn, Seed
    from sqlalchemy import Integer

    class Product(Base):
        __tablename__ = "products"
        id = SeededColumn(Integer, primary_key=True, autoincrement=True)
        price = SeededColumn(
            Integer,
            seed=Seed(faker_provider="random_int", faker_kwargs={"min": 10, "max": 500})
        )
    ```

    In this example, the `price` column generates random integers between 10 and 500.
    This is equivalent to calling the `Faker` provider directly with the same arguments, as shown below:

    ```python
    from faker import Faker

    faker = Faker()
    price = faker.random_int(min=10, max=500)
    ```

    The `Seed` class essentially wraps the `Faker` provider call, allowing you to define the provider (`random_int`) and its parameters (`min=10, max=500`) declaratively within the model. This ensures that SeedLayer consistently applies the specified configuration during data generation, while also supporting additional features like unique value tracking and column dependencies when used with `SeededColumn`.

3. **ColumnReference Class**  
    The `ColumnReference` class enables inter-column dependencies by allowing one column's value to be used as a parameter for another's data generation. This is particularly useful for creating logically consistent data, such as a description based on a name. The `ColumnReference` can also include a `transform` function to modify the referenced value before use.

    **Example**:

    ```python
    from seedlayer import SeededColumn, Seed, ColumnReference
    from sqlalchemy import String, Text

    class Product(Base):
        __tablename__ = "products"
        id = SeededColumn(Integer, primary_key=True, autoincrement=True)
        name = SeededColumn(String, seed="word")
        description = SeededColumn(
            Text,
            seed=Seed(
                faker_provider="sentence",
                faker_kwargs={"nb_words": ColumnReference("name", transform=lambda x: len(x.split()) + 5)}
            )
        )
    ```

    Here, the `description` column generates a sentence with a number of words based on the length of the `name` column plus 5.

    These classes work together to provide flexible, declarative control over data generation, ensuring that your fake data aligns with your application's requirements and constraints.

### Changing Default Providers for Column Types

You can override the default Faker providers for SQLAlchemy column types by passing a custom `type_defaults` dictionary to the `SeedLayer` constructor. The default providers are defined for common types like `Integer`, `String`, `Boolean`, `DateTime`, `Text`, `Float`, and `UUID`. To customize, create a dictionary mapping SQLAlchemy types to either a `Seed` object or a string representing a Faker provider.

**Example**:

```python
from sqlalchemy import Integer, String
from seedlayer import Seed, SeedLayer

custom_type_defaults = {
    Integer: Seed(faker_provider="random_int", faker_kwargs={"min": 1000, "max": 9999}),
    String: Seed(faker_provider="sentence", faker_kwargs={"nb_words": 3}),
}

with Session(engine) as session:
    seeder = SeedLayer(session, seed_plan, type_defaults=custom_type_defaults)
    seeder.seed()
```

In this example:

- `Integer` columns will use `Faker.random_int` with values between 1000 and 9999.
- `String` columns will use `Faker.sentence` to generate three-word sentences.

### Use Custom Faker Providers

You can extend the `Faker` instance used by SeedLayer by adding custom providers. This is useful for generating domain-specific data not covered by standard Faker providers.

**Example**:

```python
from faker.providers import BaseProvider
from seedlayer import SeedLayer

# Define a custom Faker provider
class CustomProvider(BaseProvider):
    def product_code(self):
        return f"PROD-{self.random_int(min=1000, max=9999)}"

# Add the custom provider to SeedLayer
with Session(engine) as session:
    seeder = SeedLayer(session, seed_plan)
    seeder.add_faker_provider(CustomProvider)
    seeder.seed()

# Use the custom provider in a model
class Product(Base):
    __tablename__ = "products"
    id = SeededColumn(Integer, primary_key=True, autoincrement=True)
    code = SeededColumn(String, seed=Seed(faker_provider="product_code"))
```

In this example:

- A custom `product_code` provider generates codes like `PROD-1234`.
- The `add_faker_provider` method registers the custom provider with SeedLayer's `Faker` instance.
- The `code` column in the `Product` model uses the custom provider for data generation.

### Configuring Faker for Reproducible and Localized Data

The `SeedLayer` class provides a `configure_faker` method to customize the `Faker` instance used for data generation. This method allows you to set a random seed for reproducible results and specify a locale to generate data in a specific language or region, ensuring that fake data aligns with your application's requirements.

#### Using configure_faker

The `configure_faker` method accepts two optional parameters:

- **seed**: An integer to set the random seed for the `Faker` instance, ensuring consistent data generation across runs. This is useful for testing or debugging scenarios where reproducible data is needed.
- **locale**: A string specifying the locale (e.g., `"en_US"`, `"fr_FR"`, `"de_DE"`) to generate region-specific data, such as names, addresses, or phone numbers in the desired language or format.

**Example**:

```python
[...]

with Session(engine) as session:
    seeder = SeedLayer(session, seed_plan)
    # Configure Faker with a seed and French locale
    seeder.configure_faker(seed=42, locale="fr_FR")
    seeder.seed()
```

In this example:

- The `seed=42` ensures that the same fake data is generated every time the script runs, making results reproducible.
- The `locale="fr_FR"` configures Faker to generate French names and addresses (e.g., "Jean Dupont" and "12 Rue de la Paix, Paris").

#### Notes

- **Reproducible Results**: Setting a seed is particularly useful for testing, as it ensures consistent data across multiple runs. Without a seed, Faker generates random data each time.
- **Locale Support**: The `locale` parameter supports any locale available in the `Faker` library. Refer to the [Faker documentation](https://faker.readthedocs.io/en/master/locales.html) for a list of supported locales.
- **Provider Preservation**: When changing the locale, existing custom providers are preserved and re-added to the new `Faker` instance automatically.

This configuration allows you to generate culturally relevant and consistent fake data tailored to your application's needs.

### Debugging and Logging

SeedLayer includes built-in logging to help trace the seeding process. By default, it logs at the `INFO` level, showing the model seeding order and progress. For more detailed output, enable `DEBUG` logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will provide detailed logs about:

- Dependency resolution and topological sorting.
- Data generation for each column and row.
- Any errors or warnings, such as missing dependencies or invalid Faker provider arguments.

**Example Output with DEBUG Logging**:

```txt
2025-08-27 15:08:33,652 [DEBUG] seedlayer.seedlayer: Resolving dependencies for model User
2025-08-27 15:08:33,653 [DEBUG] seedlayer.seedlayer: Generating 700 rows for User with columns: ['id', 'name', 'email', 'age']
2025-08-27 15:08:33,654 [INFO] seedlayer.seedlayer: Seeding 700 rows for User
...
```

You can also inspect the state of seeded models using the `SeedLayer` object's string representation:

```python
print(seeder)
```

This outputs a formatted summary of existing and new IDs, as well as unique values for each model.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue on the project repository.

1. Clone this repository.
2. Create a Python virtual environment
3. Install dependencies: `pip install -e .[dev]`.
4. Make changes and submit a pull request.

## License

This project is licensed under the MIT License.
