"""The living technical dictionary, and how it reaches the decoder (RF-147).

The requirement is «un diccionario vivo de vocabulario técnico (términos, sinónimos, regionalismos,
códigos) administrable, que alimenta el ASR, el extractor y los catálogos», and its acceptance
criterion is «un término añadido llega al móvil en el siguiente sync de catálogos».

The gap was a disconnection, not an absence. The catalogue entries of RF-034 already carry
`synonyms` — «cruceta podrida» for `cruceta_podrida` — and the lexicon builder never read them: it
built from the canonical spoken vocabulary (`profiles/amd/voice-es-EC.yaml`) and the unit's synced
GIS metadata, and nothing else. So a defect field had **no hotwords at all**, and a regionalism an
administrator typed reached nobody.

Two sources, and the split is deliberate:

* **`profiles/amd/voice-es-EC.yaml` is the canonical baseline.** It says how an Ecuadorian line
  technician says a *canonical* value, and it belongs with the model descriptor because that is what
  «canonical» means. It is not administrable at runtime and should not be: changing it changes the
  meaning of every profile.
* **The catalogues are the living half.** A value's synonyms live with the value, so adding a
  regionalism is the same act as adding the value, it versions with it, and it rides the same delta
  to the phone. That is what makes the acceptance criterion true rather than aspirational.

And one extra catalogue, `vocabulary`, for the words that name no value: field cues («dígame la
altura»), and plain terms a decoder should be pushed towards even though they fill nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.catalogs import service as catalogs
from app.org.models import BusinessUnit

#: The catalogue that holds vocabulary which is not a value of anything else.
VOCABULARY_CATALOG = "vocabulary"

#: `attributes.field` on a `vocabulary` entry names the form field it cues. Without it the entry is
#: a plain term: boosted, but not a cue for any particular field.
FIELD_ATTRIBUTE = "field"


@dataclass(frozen=True)
class VocabularyTerms:
    """Administrable vocabulary, already resolved for one business unit.

    A plain structure and not a query: `build_lexicon` stays a pure function of data, which is what
    lets the offline-package builder and the mobile contract tests use it without a database.
    """

    #: Catalogue code → entry code → spoken forms, preferred first.
    catalog_aliases: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    #: Form field key → extra spoken cues an area added.
    field_cues: dict[str, list[str]] = field(default_factory=dict)
    #: Terms that name no field and no value, boosted anyway.
    terms: list[str] = field(default_factory=list)

    def aliases_for(self, catalog_code: str) -> dict[str, list[str]]:
        return self.catalog_aliases.get(catalog_code, {})

    @property
    def is_empty(self) -> bool:
        return not (self.catalog_aliases or self.field_cues or self.terms)

    def as_dict(self) -> dict[str, Any]:
        return {
            "catalog_aliases": self.catalog_aliases,
            "field_cues": self.field_cues,
            "terms": self.terms,
        }


def _spoken_forms(label: str, synonyms: list[str]) -> list[str]:
    """The label first, then the synonyms, without repeats.

    The label leads because it is what the utility calls the thing; the synonyms are how people
    actually say it, and a decoder pushed towards both is what turns «cruceta podrida» into
    `cruceta_podrida`.
    """
    forms = [label, *synonyms]
    seen: dict[str, None] = {}
    for form in forms:
        cleaned = form.strip()
        if cleaned:
            seen.setdefault(cleaned.lower(), None)
    return list(seen)


def collect(session: Session, unit: BusinessUnit | None = None) -> VocabularyTerms:
    """Every administrable term a device of this unit should know.

    Includes the unit's own catalogue additions, because a word only that unit uses is exactly the
    one a national list would never carry.
    """
    aliases: dict[str, dict[str, list[str]]] = {}
    cues: dict[str, list[str]] = {}
    terms: list[str] = []

    for catalog in catalogs.list_catalogs(session):
        resolved = catalogs.resolve(session, catalog.code, unit)
        if catalog.code == VOCABULARY_CATALOG:
            for entry in resolved.entries:
                spoken = _spoken_forms(entry.label, entry.synonyms)
                target = entry.attributes.get(FIELD_ATTRIBUTE)
                if isinstance(target, str) and target:
                    cues.setdefault(target, [])
                    cues[target].extend(form for form in spoken if form not in cues[target])
                else:
                    terms.extend(form for form in spoken if form not in terms)
            continue
        entry_aliases = {
            entry.code: _spoken_forms(entry.label, entry.synonyms) for entry in resolved.entries
        }
        if entry_aliases:
            aliases[catalog.code] = entry_aliases

    return VocabularyTerms(catalog_aliases=aliases, field_cues=cues, terms=terms)
