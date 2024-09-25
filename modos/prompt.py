from datetime import date
from typing import Any, List, Mapping, Optional

import click
from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
import typer

from .codes import CodeMatcher, get_slot_matchers
from .helpers.schema import (
    get_enum_values,
    get_slots,
    get_slot_range,
    load_schema,
)
from .remote import EndpointManager


class SlotCodeCompleter(Completer):
    def __init__(self, matcher: CodeMatcher):
        self.matcher = matcher

    def get_completions(self, document, complete_event):
        self.matcher.find_codes(document.text)

        for rec in self.matcher.find_codes(document.text):
            yield Completion(
                rec.label, start_position=-document.cursor_position
            )


def fuzzy_complete(matcher: CodeMatcher):
    result = prompt(
        "> ", completer=SlotCodeCompleter(matcher), complete_while_typing=True
    )
    return result


class SlotPrompter:
    def __init__(self, endpoint: Optional[EndpointManager] = None):
        self.slot_matchers = get_slot_matchers(endpoint.fuzon)

    def prompt_for_slot(self, slot_name: str, optional: bool = False):
        slot_range = get_slot_range(slot_name)
        choices, default = None, None
        if slot_range == "datetime":
            default = date.today()
        elif load_schema().get_enum(slot_range):
            choices = click.Choice(get_enum_values(slot_range))
        elif optional:
            default = ""

        prefix = "(optional) " if optional else "(required) "

        if slot_name in self.slot_matchers:
            output = fuzzy_complete(self.slot_matchers[slot_name])
        else:
            output = typer.prompt(
                f"{prefix}Enter a value for {slot_name}",
                default=default,
                type=choices,
            )

        if output == "":
            output = None

        return output

    def prompt_for_slots(
        self, target_class: type, exclude: Optional[Mapping[str, List]] = None
    ) -> dict[str, Any]:
        """Prompt the user to provide values for the slots of input class.
        values of required fields can be excluded to repeat the prompt.

        Parameters
            ----------
            target_class
                Class to build
            exclude
                Mapping with the name of a slot as key  and list of invalid entries as values.
        """

        entries = {}
        required_slots = set(get_slots(target_class, required_only=True))
        optional_slots = (
            set(get_slots(target_class, required_only=False)) - required_slots
        )

        # Always require identifiers if possible
        if "id" in optional_slots:
            optional_slots.remove("id")
            required_slots.add("id")

        for slot_name in required_slots:
            entries[slot_name] = self.prompt_for_slot(slot_name)
            if entries[slot_name] is None:
                raise ValueError(f"Missing required slot: {slot_name}")
            if exclude and entries.get(slot_name) in exclude.get(
                slot_name, []
            ):
                print(
                    f"Invalid value: {slot_name} must differ from {exclude[slot_name]}."
                )
                entries[slot_name] = self.prompt_for_slot(slot_name)

        if optional_slots:
            for slot_name in optional_slots:
                entries[slot_name] = self.prompt_for_slot(
                    slot_name, optional=True
                )
        return entries
