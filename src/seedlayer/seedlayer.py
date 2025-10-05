import logging
from pprint import pformat

from faker import Faker
from sqlalchemy import select
from sqlalchemy.orm import Session, class_mapper

from .constants import TYPE_DEFAULTS, TypeDefaults
from .dependency_graph import DependencyGraph
from .seeded_model import SeededModel
from .types import SeedPlan

logging.basicConfig(  # root logger configuration
    level=logging.INFO,  # Enable DEBUG for detailed tracing
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class SeedLayer:
    """SeedLayer facilitates seeding database models with fake data.

    This class manages the process of populating SQLAlchemy models with generated
    fake data based on a provided seed plan. It handles model dependencies for proper
    insertion order, supports batching for performance, and integrates with the Faker
    library for realistic data generation.
    """

    def __init__(
        self,
        session: Session,
        seed_plan: SeedPlan,
        type_defaults: TypeDefaults = TYPE_DEFAULTS,
        batch_size: int = 1000,  # Configurable batch size
    ):
        """Initialize the SeedLayer instance.

        Args:
            session: SQLAlchemy session for database operations.
            seed_plan: Dictionary mapping model classes to number of rows to seed.
            type_defaults: Custom type defaults to override TYPE_DEFAULTS.
            batch_size: Number of rows to process in each batch. Defaults to 1000.
        """
        if seed_plan is None:
            raise ValueError("seed_plan is missing")
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        self.type_defaults: TypeDefaults = TYPE_DEFAULTS | type_defaults
        self.faker: Faker = Faker()
        self._session: Session = session
        self._model_dependency_graph: DependencyGraph = DependencyGraph()
        self._seed_plan: SeedPlan = seed_plan
        self._batch_size: int = batch_size
        self.models: dict[str, SeededModel] = {}
        for model_class, nb_of_rows_to_seed in seed_plan.items():
            model = SeededModel(model_class, nb_of_rows_to_seed, session, seed_plan)
            self._model_dependency_graph.add(
                model.name,
                model.foreign_key_dependencies,
            )
            if model.name in self.models.keys():
                raise ValueError(f"Multiple models with same name {model.name}")
            self.models[model.name] = model
        self.model_seed_order = self._model_dependency_graph.topological_sort()

    def add_faker_provider(self, provider: type) -> None:
        """Add a Faker provider to the shared Faker instance.

        Args:
            provider: The Faker provider class to add.
        """
        self.faker.add_provider(provider)

    def configure_faker(self, seed: int | None = None, locale: str | None = None) -> None:
        """Configure the shared Faker instance.

        Args:
            seed: Seed for reproducible results (optional).
            locale: Locale for the Faker instance, e.g., 'en_US' (optional).
        """
        providers = self.faker.providers.copy()  # Save providers
        if locale is not None:
            self.faker = Faker(locale)
            for provider in providers:
                self.faker.add_provider(provider)  # Re-add providers
        if seed is not None:
            self.faker.seed_instance(seed)

    def seed(self, single_transaction: bool = False) -> None:
        """Seed the models in the seed plan.

        This method executes the seeding process for all configured models,
        generating and inserting fake data according to the seed plan.

        Args:
            single_transaction: Whether to wrap all seeding operations in a
                single database transaction. Defaults to False.
        """
        logger.info(f"Model seeding order: {[m for m in self.model_seed_order]}")
        if single_transaction:
            with self._session.begin():
                self._seed_models(single_transaction=True)
        else:
            self._seed_models(single_transaction=False)

    def _seed_models(self, single_transaction: bool) -> None:
        """Internal method to seed models in batches using bulk_insert_mappings."""
        for model_name in self.model_seed_order:
            model = self.models[model_name]
            count = model.nb_of_rows_to_seed
            logger.info(f"Seeding {count} rows for {model.name}")

            # Process rows in batches
            remaining_rows = count
            while remaining_rows > 0:
                batch_count = min(self._batch_size, remaining_rows)
                logger.debug(f"Processing batch of {batch_count} rows for {model.name}")

                # Generate fake rows for the batch
                fake_rows = model.fake_rows(
                    batch_count,
                    models=self.models,
                    faker=self.faker,
                    type_defaults=self.type_defaults,
                )

                # Use bulk_insert_mappings with the Mapper object
                self._session.bulk_insert_mappings(class_mapper(model.base_model), fake_rows)
                self._session.flush()

                # Query all rows for this model to update primary keys and unique values
                query = (
                    select(
                        *[
                            getattr(model.base_model, col)
                            for col in model.primary_keys + model.unique_columns
                        ]
                    )
                    .order_by(getattr(model.base_model, model.primary_keys[0]).desc())
                    .limit(batch_count)
                )
                result = self._session.execute(query).all()
                model._process_query_result(result, new_data=True)

                if not single_transaction:
                    self._session.commit()
                remaining_rows -= batch_count
                logger.debug(f"Committed batch, {remaining_rows} rows remaining for {model.name}")

            if single_transaction:
                self._session.commit()

    def __repr__(self) -> str:
        """Return a string representation of the SeedLayer instance."""
        return pformat(
            {
                name: {
                    "existing_ids": len(model.existing_ids),
                    "new_ids": len(model.new_ids),
                    "unique_values": {k: len(v) for k, v in model.unique_values.items()},
                }
                for name, model in self.models.items()
            }
        )


__all__ = ["SeedLayer", "SeededModel"]
