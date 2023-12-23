from pathlib import Path
from linkml_runtime.linkml_model.meta import SlotDefinition
from linkml_runtime.utils.schemaview import SchemaView


def load_schema() -> SchemaView:
    """Return a view over the schema structure."""
    import smoc_schema.schema as schema

    schema_file = Path(schema.__path__[0]) / "smoc_schema.yaml"
    return SchemaView(schema_file)


SCHEMA_VIEW = load_schema()


def get_slots(target_class: str, required_only=False) -> list[str]:
    """Return a list of required slots for a class."""
    required = []
    class_slots = SCHEMA_VIEW.get_class(target_class).slots
    if not class_slots:
        return required

    # NOTE: May need to check inheritance and slot_usage
    for slot_name in class_slots:
        if not required_only or SCHEMA_VIEW.get_slot(slot_name).required:
            required.append(slot_name)

    return required


def validate_instance(instance):
    """Validate an instance against the schema."""
    required_slots = get_required_slots(instance.__class__.__name__)
    for slot_name in required_slots:
        if not getattr(instance, slot_name):
            raise ValueError(f"Missing required slot: {slot_name}")
