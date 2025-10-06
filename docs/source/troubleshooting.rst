***************
Troubleshooting
***************

This guide helps you debug and resolve issues with SeedLayer. Built-in logging and debugging tools help identify problems and verify data generation.

Logging Configuration
======================

SeedLayer uses Python's standard logging module. Enable debug logging to see detailed information:

.. code-block:: python

    import logging
    logging.basicConfig(level=logging.DEBUG)

With debug logging enabled, you'll see:

1. **Dependency resolution** - How SeedLayer analyzes your models and foreign keys
2. **Column generation** - What data is generated for each column
3. **Uniqueness tracking** - How unique constraints are maintained
4. **Error details** - Specific information about any failures

Example Debug Output
====================

.. code-block:: none

    [DEBUG] seedlayer.seedlayer: Resolving dependencies for model User
    [DEBUG] seedlayer.seedlayer: Generating data for User columns: ['id', 'name', 'email', 'age']
    [INFO] seedlayer.seedlayer: Seeding 1000 rows for User
    [DEBUG] seedlayer.seedlayer: Generated User(id=1, name='John Doe', email='john@example.com', age=25)

Common Issues and Solutions
===========================

Foreign Key Violations
----------------------

**Problem**: Getting foreign key constraint errors.

**Solutions**:

1. **Check seed plan order**: Make sure parent tables come before child tables:

   .. code-block:: python

       # ❌ Wrong order - child before parent
       seed_plan = {Order: 100, Customer: 50}

       # ✅ Correct order - parent before child
       seed_plan = {Customer: 50, Order: 100}

2. **Set referenced columns to seed=None**: Foreign key columns should not generate random data:

   .. code-block:: python

       # ❌ Wrong - generates random category_id values
       category_id = SeededColumn(Integer, ForeignKey("categories.id"))

       # ✅ Correct - lets SeedLayer fill with valid FK values
       category_id = SeededColumn(Integer, ForeignKey("categories.id"), seed=None)

Unique Constraint Violations
----------------------------

**Problem**: UNIQUE constraint failed errors.

**Solutions**:

1. **Enable uniqueness tracking**: Ensure unique columns are marked:

   .. code-block:: python

       email = SeededColumn(String, seed="email", unique=True)

2. **Insufficient Faker variety**: If your row count exceeds Faker's variety, reduce row count or make some rows non-unique.

Missing Providers
-----------------

**Problem**: AttributeError about missing Faker provider.

**Solution**: Check Faker provider names:

.. code-block:: python

    # ❌ Wrong - provider doesn't exist
    post_code = SeededColumn(String, seed="zipcode")

    # ✅ Correct - valid provider name
    post_code = SeededColumn(String, seed="zipcode")

Use ``dir()`` on a Faker instance to see available providers:

.. code-block:: python

    from faker import Faker
    fake = Faker()
    print([attr for attr in dir(fake) if not attr.startswith('_')])

Type Errors
-----------

**Problem**: "Cannot generate data for column type" errors.

**Solutions**:

1. **Use SeededColumn**: Replace SQLAlchemy's Column with SeededColumn:

   .. code-block:: python

       # ❌ Won't work with SeedLayer
       from sqlalchemy import Column
       name = Column(String)

       # ✅ SeedLayer-compatible
       from seedlayer import SeededColumn
       name = SeededColumn(String, seed="name")

2. **Add custom type mapping**: For unsupported types, add custom defaults:

   .. code-block:: python

       custom_types = {MyCustomType: "custom_provider"}
       seeder = SeedLayer(session, plan, type_defaults=custom_types)

Circular Dependencies
---------------------

**Problem**: "Circular dependency detected" errors.

**Solution**: Redesign your schema or break the cycle:

.. code-block:: python

    # Example: User references Department, Department references Manager (User)
    # Break by seeding Department first with dummy manager_id, then updating
    class Department(Base):
        manager_id = SeededColumn(Integer, nullable=True, seed=None)  # Allow null temporarily

    class User(Base):
        department_id = SeededColumn(Integer, ForeignKey("departments.id"), seed=None)

    # Seed Departments first (with null managers), then Users, then update managers
    seed_plan = {Department: 10, User: 100}

Performance Issues
==================

Large Datasets
--------------

For >10k rows per table, consider:

1. **Batch seeding**: Seed in smaller chunks:

   .. code-block:: python

       # Instead of 100k rows once:
       for _ in range(10):
           small_plan = {Model: 10000}
           seeder = SeedLayer(session, small_plan)
           seeder.seed()

2. **Disable echo**: Set ``echo=False`` in your engine
3. **Use faster database**: Consider switching from SQLite to PostgreSQL/MySQL for large datasets

Memory Usage
------------

Large datasets can consume memory due to:

- **Uniqueness tracking**: Reduces as rows are generated
- **Reference tracking**: SeedLayer tracks generated IDs for FK relationships

Solutions:

1. **Clear sessions periodically**: Don't hold references to seeded objects
2. **Use smaller batches**: As mentioned above
3. **Monitor memory**: Use tools like memory_profiler

Verification Tools
==================

Debug Mode Output
------------------

Inspect the final state of seeded models:

.. code-block:: python

    seeder = SeedLayer(session, seed_plan)
    seeder.seed()

    # See summary of what was generated
    print(seeder)

This shows:

- Successfully seeded row counts
- Generated ID ranges
- Unique value tracking status

Manual Data Inspection
----------------------

Query your database to verify data quality:

.. code-block:: python

    # Check row counts
    result = session.execute(text("SELECT COUNT(*) FROM users")).scalar()
    print(f"Seeded {result} users")

    # Verify foreign key constraints
    result = session.execute(text("""
        SELECT COUNT(*) FROM orders
        WHERE customer_id NOT IN (SELECT id FROM customers)
    """)).scalar()

    if result > 0:
        print(f"Found {result} orphaned orders!")

    # Check uniqueness
    result = session.execute(text("""
        SELECT email, COUNT(*)
        FROM customers
        GROUP BY email
        HAVING COUNT(*) > 1
    """)).fetchall()

    if result:
        print(f"Found {len(result)} duplicate emails")

Data Quality Checks
-------------------

Test that your seed configurations produce realistic data:

.. code-block:: python

    # Check value ranges
    ages = session.execute(text("SELECT age FROM users WHERE age < 0 OR age > 150")).fetchall()
    if ages:
        print(f"Problematic ages found: {ages}")

    # Verify nullable columns behave correctly
    null_phones = session.execute(text("SELECT COUNT(*) FROM customers WHERE phone IS NULL")).scalar()
    total_customers = session.execute(text("SELECT COUNT(*) FROM customers")).scalar()
    null_percentage = (null_phones / total_customers) * 100
    print(f"Null phone percentage: {null_percentage:.1f}% (expected ~20%)")

Common FAQs
===========

**Q: Why doesn't my primary key column get seeded?**

**A:** SeedLayer lets the database manage autoincrement primary keys. Set ``seed=None`` if you want SeedLayer to fill them manually (not recommended for production).

**Q: Can I use existing SQLAlchemy Column classes with SeedLayer?**

**A:** No, you must use ``SeededColumn`` instead of ``Column``. The ``seed`` parameter is required for SeedLayer to know how to generate data.

**Q: My custom Faker provider isn't working.**

**A:** Make sure you call ``seeder.add_faker_provider(YourProvider)`` before ``seeder.seed()``, and that your provider inherits from ``BaseProvider``.

**Q: Getting "Cannot resolve model dependencies" errors.**

**A:** Check that all foreign key references point to valid models in your seed plan. Ensure parent tables are seeded before child tables.

**Q: Performance is slow with many unique columns.**

**A:** Uniqueness tracking uses sets to ensure no duplicates. On very large datasets (>100k rows), consider reducing uniqueness requirements or seeding in batches.

Getting Help
============

If you're still having issues:

1. **Enable full debug logging** and check the output
2. **Test with minimal example** - Start with a single simple model
3. **Verify your SQLAlchemy models** - Ensure FK constraints are properly defined
4. **Check SeedLayer version** compatibility with your SQLAlchemy/Faker versions

For bugs or feature requests, visit the `GitHub repository <https://github.com/francoisnt/seedlayer>`_.
