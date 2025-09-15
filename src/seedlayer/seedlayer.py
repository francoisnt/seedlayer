import logging
from pprint import pformat
from typing import (
    Dict,
    Optional,
)

from faker import Faker
from sqlalchemy.orm import Session

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
    def __init__(
        self,
        session: Session,
        seed_plan: SeedPlan,
        type_defaults: TypeDefaults = TYPE_DEFAULTS,
    ):
        if seed_plan is None:
            raise ValueError("seed_plan is missing")
        self.type_defaults: TypeDefaults = TYPE_DEFAULTS | type_defaults
        self.faker: Faker = Faker()
        self._session: Session = session
        self._model_dependency_graph: DependencyGraph = DependencyGraph()
        self._seed_plan: SeedPlan = seed_plan
        self.models: Dict[str, SeededModel] = {}

        for model_class, nb_of_rows_to_seed in seed_plan.items():
            model = SeededModel(model_class, nb_of_rows_to_seed, session, seed_plan)

            self._model_dependency_graph.add(
                model.name,
                model.foreign_key_dependencies,
            )

            if model.name in self.models.keys():
                raise ValueError("Multiple models with same name {model.name}")

            # TODO : map talbe names to model names
            self.models[model.name] = model

        self.model_seed_order = self._model_dependency_graph.topological_sort()

    def add_faker_provider(self, provider: type) -> None:
        self.faker.add_provider(provider)

    def configure_faker(self, seed: Optional[int] = None, locale: Optional[str] = None) -> None:
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

    def seed(self):
        """Seed all models in seed_plan dict into the DB, respecting FK dependencies."""

        logger.info(f"Model seeding order: {[m for m in self.model_seed_order]}")

        # TODO: transaction (per model?)

        for model_name in self.model_seed_order:
            model = self.models[model_name]
            count = model.nb_of_rows_to_seed
            logger.info(f"Seeding {count} rows for {model.name}")

            fake_rows = model.fake_rows(
                count, models=self.models, faker=self.faker, type_defaults=self.type_defaults
            )
            objects = []
            for row_data in fake_rows:
                obj = model.base_model(**row_data)
                self._session.add(obj)
                objects.append(obj)

            self._session.flush()

            model._process_query_result(objects, new_data=True)

            self._session.commit()

            for obj in objects:
                self._session.refresh(obj, attribute_names=model.primary_keys)

    def __repr__(self):
        # Simple printout for debugging
        return pformat(
            {
                model_class.__name__: {
                    "existing_ids": len(data.existing_ids),
                    "new_ids": len(data.new_ids),
                    "unique_values": {k: len(v) for k, v in data["unique_values"].items()},
                }
                for model_class, data in self.models.items()
            }
        )
