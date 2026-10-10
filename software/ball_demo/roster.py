"""Strict server-owned roster and tag assignments for portable missions."""
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, ValidationError, model_validator

from .map_io import Contract, Identifier, Matrix, Number, Positive, rigid


class Person(Contract):
    person_id: Annotated[str, Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_.-]+$')]
    display_name: Annotated[str, Field(min_length=1, max_length=100)]
    tag_family: Literal['tag36h11']
    tag_id: int = Field(ge=0, lt=587)
    tag_size_m: Positive
    enabled: bool = True

    @model_validator(mode='after')
    def identity(self):
        if not self.display_name.strip() or self.display_name != self.display_name.strip():
            raise ValueError('Display name must be nonblank and trimmed')
        if type(self.enabled) is not bool:
            raise ValueError('enabled must be a boolean')
        return self


class LandingSite(Contract):
    site_id: Annotated[str, Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_.-]+$')]
    display_name: Annotated[str, Field(min_length=1, max_length=100)]
    tag_family: Literal['tag36h11']
    tag_id: int = Field(ge=0, lt=587)
    tag_size_m: Positive
    width_m: Positive
    length_m: Positive
    approach_tolerance_rad: Number = Field(default=.35, gt=0, le=3.141592653589793)
    # Transform from the tag frame to the pad center frame. Identity means the
    # measured tag is centered and aligned with the landing footprint.
    pad_from_tag: Matrix = Field(default_factory=lambda: [
        [1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]])
    enabled: bool = True

    @model_validator(mode='after')
    def valid_site(self):
        if not self.display_name.strip() or self.display_name != self.display_name.strip():
            raise ValueError('Landing-site name must be nonblank and trimmed')
        if type(self.enabled) is not bool:
            raise ValueError('enabled must be a boolean')
        rigid(self.pad_from_tag)
        return self


class Roster(Contract):
    schema_version: Literal[1] = 1
    people: Annotated[list[Person], Field(max_length=100)] = Field(default_factory=list)
    landing_sites: Annotated[list[LandingSite], Field(max_length=100)] = Field(default_factory=list)

    @model_validator(mode='after')
    def unique_assignments(self):
        ids = [person.person_id for person in self.people]
        tags = [person.tag_id for person in self.people if person.enabled]
        site_ids = [site.site_id for site in self.landing_sites]
        tags.extend(site.tag_id for site in self.landing_sites if site.enabled)
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate person_id in prepared roster')
        if len(site_ids) != len(set(site_ids)):
            raise ValueError('Duplicate site_id in prepared roster')
        if len(tags) != len(set(tags)):
            raise ValueError('Enabled people and landing sites must have distinct AprilTag IDs')
        return self

    def by_person_id(self, person_id):
        return next((person for person in self.people if person.person_id == person_id), None)

    def by_tag_id(self, tag_id):
        return next((person for person in self.people if person.enabled and person.tag_id == tag_id), None)

    def site_by_id(self, site_id):
        return next((site for site in self.landing_sites if site.enabled and site.site_id == site_id), None)

    def site_by_tag_id(self, tag_id):
        return next((site for site in self.landing_sites if site.enabled and site.tag_id == tag_id), None)


def load_roster(path):
    """Load an operator-prepared roster from a private runtime JSON file."""
    path = Path(path)
    try:
        if path.stat().st_size > 128_000:
            raise ValueError('Prepared roster exceeds 128 KB')
        return Roster.model_validate_json(path.read_text())
    except ValueError as error:
        if str(error) == 'Prepared roster exceeds 128 KB':
            raise
        raise ValueError(f'Invalid prepared roster: {error}') from error
    except (ValidationError, OSError) as error:
        raise ValueError(f'Invalid prepared roster: {error}') from error
