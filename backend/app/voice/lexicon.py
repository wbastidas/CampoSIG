"""Build the ASR lexicon from the profile and the open work order (RF-331, RF-332).

Recognition of ordinary Spanish is a solved problem; recognition of *this utility's*
vocabulary is not. A decoder that has never seen a feeder code will transcribe it as
whatever Spanish words sound closest, and a capture whose feeder is wrong is worse than
one with no feeder at all.

So the lexicon is generated, never written by hand, from three sources:

1. the **canonical spoken vocabulary** (``profiles/amd/voice-es-EC.yaml``), which says how
   an Ecuadorian technician pronounces a canonical value;
2. the **business unit's synced metadata**, which supplies the utility's own display
   labels — including the three catalogues that differ per unit (RF-304);
3. the **open work order**, whose asset code, feeder and address are the words most likely
   to be dictated in the next minute, and which therefore get the highest boost.

Nothing here contains a real class, field or domain name: source 2 arrives as data at
runtime and source 3 belongs to one work order (RF-305).
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.model_profile.amd import AttributeRole
from app.model_profile.metadata import GisMetadata
from app.model_profile.resolver import ModelResolver, ResolutionError
from app.voice.grammar import extractable_fields
from app.voice.normalizer import strip_accents
from app.voice.vocabulary import VocabularyTerms

#: Source tags on a hotword, so a boost can be explained and a lexicon diffed.
SOURCE_WORK_ORDER = "work_order_context"
SOURCE_VOLATILE_DOMAIN = "volatile_domain"
SOURCE_DOMAIN_VALUE = "domain_value"
SOURCE_ATTRIBUTE_CUE = "attribute_cue"
SOURCE_ASSET_LABEL = "asset_label"


class SpokenVocabulary(BaseModel):
    """The canonical spoken vocabulary file, typed."""

    version: int
    locale: str
    boosts: dict[str, float] = Field(default_factory=dict)
    boolean_words: dict[str, list[str]] = Field(default_factory=dict)
    enum_synonyms: dict[str, dict[str, list[str]]] = Field(default_factory=dict)
    attribute_cues: dict[str, list[str]] = Field(default_factory=dict)

    def boost(self, source: str) -> float:
        return self.boosts.get(source, 1.0)

    @property
    def affirmative(self) -> list[str]:
        return self.boolean_words.get("affirmative", [])

    @property
    def negative(self) -> list[str]:
        return self.boolean_words.get("negative", [])


@lru_cache
def load_spoken_vocabulary(path: str | None = None) -> SpokenVocabulary:
    default = Path(__file__).resolve().parents[3] / "profiles" / "amd" / "voice-es-EC.yaml"
    location = Path(path) if path else default
    data = yaml.safe_load(location.read_text(encoding="utf-8"))
    return SpokenVocabulary.model_validate(data)


class Hotword(BaseModel):
    """One phrase the decoder should be pushed towards."""

    text: str
    boost: float
    source: str


class OrderContext(BaseModel):
    """What the open work order already knows, as words (RF-331).

    Everything is optional: a work order created from a GIS review may have no address,
    and one from the call centre may have no feeder yet.
    """

    asset_code: str | None = None
    feeder_code: str | None = None
    substation: str | None = None
    address: str | None = None
    asset_type_key: str | None = None

    def phrases(self) -> list[str]:
        return [
            value
            for value in (self.asset_code, self.feeder_code, self.substation, self.address)
            if value
        ]


class VoiceLexicon(BaseModel):
    """Everything the device needs to turn dictation into canonical values.

    ``content_hash`` is what makes the download cheap: the phone sends the hash it holds
    and gets a body back only when the lexicon actually changed. Volatile catalogues move
    often, the rest almost never.
    """

    profile_id: str
    form_code: str
    form_version: str
    locale: str
    hotwords: list[Hotword] = Field(default_factory=list)
    #: Canonical field key → phrases that announce the field in dictation.
    field_cues: dict[str, list[str]] = Field(default_factory=dict)
    #: Canonical field key → canonical value → spoken forms of that value.
    value_aliases: dict[str, dict[str, list[str]]] = Field(default_factory=dict)
    #: Canonical field key → the literal codes valid for that field in this unit now.
    #: A feeder code is not a word: the decoder hears "cero cuatro be hache cero siete
    #: cero te once" and only the real catalogue can turn that back into one value.
    code_values: dict[str, list[str]] = Field(default_factory=dict)
    #: Fields whose catalogue changes per business unit; never cached as constants.
    volatile_fields: list[str] = Field(default_factory=list)
    affirmative: list[str] = Field(default_factory=list)
    negative: list[str] = Field(default_factory=list)
    content_hash: str = ""
    warnings: list[str] = Field(default_factory=list)

    def aliases_for(self, field_key: str) -> dict[str, list[str]]:
        return self.value_aliases.get(field_key, {})

    def codes_for(self, field_key: str) -> list[str]:
        return self.code_values.get(field_key, [])

    def compute_hash(self) -> str:
        """Hash of everything that affects recognition, excluding the hash itself."""
        payload = self.model_dump(mode="json", exclude={"content_hash", "warnings"})
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


#: Words a derived cue may not consist of on its own. They appear in half the labels of
#: any geodatabase ("Tipo de montaje", "Valor nominal") and as a cue they would match the
#: wrong field constantly. The full label is still kept as a phrase.
_GENERIC_CUE_WORDS = frozenset({"tipo", "valor", "dato", "datos", "nombre", "campo", "codigo"})


def _cue_phrases(title: str | None) -> list[str]:
    """Spoken cues taken from a field's own label.

    The label is what the utility calls the field, so it is the phrase a technician is
    most likely to use. Single short words are dropped: a cue of "de" matches everything.
    """
    if not title:
        return []
    folded = strip_accents(title.lower()).strip()
    phrases = [folded] if len(folded) > 3 else []
    words = [
        w for w in folded.replace("/", " ").split() if len(w) > 3 and w not in _GENERIC_CUE_WORDS
    ]
    return list(dict.fromkeys(phrases + words))


def _catalog_refs(node: Any) -> set[str]:
    """Every `x-catalog-ref` in a composed schema, however deeply nested.

    The whole schema and not only the extractable fields: a defect is dictated inside a repeatable
    table, so `extractable_fields` rightly leaves it out — the extractor fills a table one entry at
    a time — but the **decoder** still has to have heard «cruceta podrida». Treating those two needs
    as one thing is what left an entire block undictatable.
    """
    found: set[str] = set()
    if isinstance(node, dict):
        ref = node.get("x-catalog-ref")
        if isinstance(ref, str) and ref:
            found.add(ref)
        for value in node.values():
            found |= _catalog_refs(value)
    elif isinstance(node, list):
        for item in node:
            found |= _catalog_refs(item)
    return found


def build_lexicon(
    resolver: ModelResolver,
    metadata: GisMetadata | None,
    *,
    form_code: str,
    form_version: str,
    schema: dict[str, Any],
    asset_type_key: str | None = None,
    context: OrderContext | None = None,
    vocabulary: SpokenVocabulary | None = None,
    terms: VocabularyTerms | None = None,
) -> VoiceLexicon:
    """Build the lexicon for one composed form in one business unit.

    :param schema: the composed form's JSON Schema. Walking the schema rather than the
        profile is deliberate: the lexicon must cover exactly the fields this form can
        fill, no more — hotwords for fields that are not on screen only add confusions.
    :param terms: the administrable dictionary (RF-147), already resolved for the unit. Without it
        a field whose values live in a platform catalogue — a defect, an activity — gets **no
        hotwords at all**, which is the state this parameter was added to fix. It is passed in
        rather than queried so this stays a pure function of data.
    """
    spoken = vocabulary or load_spoken_vocabulary()
    dictionary = terms or VocabularyTerms()
    lexicon = VoiceLexicon(
        profile_id=resolver.profile.id,
        form_code=form_code,
        form_version=form_version,
        locale=spoken.locale,
        affirmative=list(spoken.affirmative),
        negative=list(spoken.negative),
    )
    hotwords: dict[tuple[str, str], Hotword] = {}
    #: Catalogue references already turned into hotwords by the field loop below, so the pass
    #: over the nested ones does not repeat them.
    covered: set[str] = set()

    def add_hotword(text: str, source: str) -> None:
        folded = strip_accents(text.lower()).strip()
        if len(folded) < 2:
            return
        key = (folded, source)
        boost = spoken.boost(source)
        current = hotwords.get(key)
        if current is None or current.boost < boost:
            hotwords[key] = Hotword(text=folded, boost=boost, source=source)

    # Exactly the fields a dictation can fill — the same set the grammar covers. Cues for
    # a repeatable table or an evidence URI would only add confusions to the decoder.
    properties = extractable_fields(schema)

    for field_key, prop in properties.items():
        # Three sources, canonical first: the spoken vocabulary of the model descriptor, the
        # field's own label, and whatever an area added to the `vocabulary` catalogue (RF-147).
        # The administrable ones go last so they extend rather than displace the baseline.
        cues = list(
            dict.fromkeys(
                spoken.attribute_cues.get(field_key, [])
                + _cue_phrases(prop.get("title"))
                + dictionary.field_cues.get(field_key, [])
            )
        )
        if cues:
            lexicon.field_cues[field_key] = cues
            for cue in cues:
                add_hotword(cue, SOURCE_ATTRIBUTE_CUE)

        # Volatility is asserted by two independent sources and either one is enough. The
        # form's flag is set only when the domain actually arrived in the last sync, so a
        # volatile catalogue that failed to export would look stable — which is exactly
        # when the warning matters most (RF-304). The profile's declaration does not
        # depend on the sync having worked.
        volatile = bool(prop.get("x-volatile-catalog")) or _profile_says_volatile(
            resolver, asset_type_key, field_key
        )
        if volatile:
            lexicon.volatile_fields.append(field_key)

        enum_ref = prop.get("x-catalog-ref")
        enum_values = prop.get("enum")

        # A field whose values live in a platform catalogue (RF-034): `defect`, `activity`,
        # `delay_reason`… Its `enum` is not in the schema — the list is data, not shape — so before
        # RF-147 this fell through to the code-bearing branch, found no GIS domain and produced
        # nothing. A technician dictating «cruceta podrida» had no hotword to be pushed towards.
        administrable = dictionary.aliases_for(str(enum_ref)) if enum_ref else {}
        if administrable:
            covered.add(str(enum_ref))
            lexicon.value_aliases[field_key] = {
                code: list(forms) for code, forms in administrable.items()
            }
            lexicon.code_values[field_key] = sorted(administrable)
            source = SOURCE_VOLATILE_DOMAIN if volatile else SOURCE_DOMAIN_VALUE
            for forms in administrable.values():
                for phrase in forms:
                    add_hotword(phrase, source)
            continue

        if not enum_ref or not isinstance(enum_values, list):
            # A code-bearing string field: its valid values are the domain's own codes,
            # which is the only thing that can turn dictated characters back into a code.
            codes = _domain_codes(metadata, prop.get("x-domain"))
            if codes:
                lexicon.code_values[field_key] = codes
                source = SOURCE_VOLATILE_DOMAIN if volatile else SOURCE_DOMAIN_VALUE
                for code in codes:
                    add_hotword(code, source)
            elif volatile:
                lexicon.warnings.append(
                    f"'{field_key}' usa un catálogo volátil que no llegó en la última "
                    "sincronización; su léxico queda incompleto hasta que el agente corra"
                )
            continue

        aliases, alias_warnings = _value_aliases(
            resolver,
            metadata,
            spoken,
            asset_type_key=asset_type_key,
            attribute_key=field_key,
            enum_ref=str(enum_ref),
            canonical_values=[str(v) for v in enum_values],
            volatile=volatile,
        )
        lexicon.warnings.extend(alias_warnings)
        if aliases:
            covered.add(str(enum_ref))
            lexicon.value_aliases[field_key] = {k: list(v) for k, v in aliases.items()}
            source = SOURCE_VOLATILE_DOMAIN if volatile else SOURCE_DOMAIN_VALUE
            for spoken_forms in aliases.values():
                for phrase in spoken_forms:
                    add_hotword(phrase, source)

    # Catalogue values that live inside a repeatable table (RF-147). Hotwords only, deliberately:
    # `value_aliases` is the extractor's contract and covers what one dictation can fill, while a
    # table is filled entry by entry. The decoder's need is different and simpler — it has to have
    # heard the words.
    for ref in sorted(_catalog_refs(schema) - covered):
        nested = dictionary.aliases_for(ref)
        if not nested:
            # Said out loud, because the symptom otherwise is a technician dictating a defect and
            # nothing being recognised, which reads as a broken decoder rather than an empty list.
            lexicon.warnings.append(
                f"el catálogo '{ref}' que este formulario referencia no trajo ningún valor: "
                "lo que se dicte en ese campo no tiene con qué reconocerse"
            )
            continue
        for spoken_forms in nested.values():
            for phrase in spoken_forms:
                add_hotword(phrase, SOURCE_DOMAIN_VALUE)

    # Terms an area added that name no field and no value: jargon a decoder should still be pushed
    # towards. Boosted like an attribute cue, because that is what they behave like.
    for term in dictionary.terms:
        add_hotword(term, SOURCE_ATTRIBUTE_CUE)

    if asset_type_key:
        add_hotword(asset_type_key.replace("_", " "), SOURCE_ASSET_LABEL)

    # The work order last, so its phrases win any boost comparison on a tie.
    if context is not None:
        for phrase in context.phrases():
            add_hotword(phrase, SOURCE_WORK_ORDER)
        _seed_context_codes(lexicon, resolver, asset_type_key, context, properties)

    lexicon.hotwords = sorted(hotwords.values(), key=lambda h: (-h.boost, h.text))
    lexicon.content_hash = lexicon.compute_hash()
    return lexicon


def _value_aliases(
    resolver: ModelResolver,
    metadata: GisMetadata | None,
    spoken: SpokenVocabulary,
    *,
    asset_type_key: str | None,
    attribute_key: str,
    enum_ref: str,
    canonical_values: list[str],
    volatile: bool,
) -> tuple[dict[str, list[str]], list[str]]:
    """Spoken forms per canonical value: the canonical file plus the unit's own labels."""
    warnings: list[str] = []
    aliases: dict[str, list[str]] = {}
    synonyms = spoken.enum_synonyms.get(enum_ref, {})
    if not synonyms:
        warnings.append(
            f"la enumeración canónica '{enum_ref}' no tiene formas habladas en es-EC; "
            "el dictado de ese campo dependerá solo de las etiquetas del dominio"
        )

    domain_labels = _domain_labels(resolver, metadata, asset_type_key, attribute_key)
    if volatile and not domain_labels:
        # A volatile catalogue that did not arrive must not be filled in from the
        # canonical file alone: the unit's real values are precisely what is missing.
        warnings.append(
            f"'{attribute_key}' usa un catálogo volátil que no llegó en la última "
            "sincronización; su léxico queda incompleto hasta que el agente corra"
        )

    for value in canonical_values:
        phrases = [strip_accents(p.lower()) for p in synonyms.get(value, [])]
        label = domain_labels.get(value)
        if label:
            phrases.append(strip_accents(label.lower()))
        deduped = list(dict.fromkeys(p for p in phrases if p))
        if deduped:
            aliases[value] = deduped
    return aliases, warnings


def _domain_labels(
    resolver: ModelResolver,
    metadata: GisMetadata | None,
    asset_type_key: str | None,
    attribute_key: str,
) -> dict[str, str]:
    """Canonical value → the display label the unit's geodatabase uses for it.

    The chain is canonical value → source code (profile ``value_map``) → domain label
    (synced metadata). Any break in it is a missing alias, never an exception: dictation
    must keep working on the canonical words alone.
    """
    if metadata is None or asset_type_key is None:
        return {}
    try:
        bound = resolver.binding(asset_type_key).attributes.get(attribute_key)
    except ResolutionError:
        return {}
    if bound is None or not bound.domain:
        return {}
    domain = metadata.domain(bound.domain)
    if domain is None:
        return {}
    # Coded values may arrive with integer codes rendered as JSON strings, so compare
    # as strings — the same reason the generator does (RF-304).
    by_code = {str(code): label for code, label in domain.coded_values.items()}

    labels: dict[str, str] = {}
    amd_enum = resolver.amd.enums
    for canonical in amd_enum.get(_enum_ref_of(resolver, asset_type_key, attribute_key) or "", []):
        try:
            source = resolver.to_source_value(asset_type_key, attribute_key, canonical)
        except ResolutionError:
            continue
        label = by_code.get(str(source))
        if label:
            labels[canonical] = label
    return labels


def _enum_ref_of(resolver: ModelResolver, asset_type_key: str, attribute_key: str) -> str | None:
    attribute = resolver.asset_type(asset_type_key).attribute(attribute_key)
    return attribute.enum_ref if attribute else None


def _domain_codes(metadata: GisMetadata | None, domain_name: Any) -> list[str]:
    """The literal codes of a domain, for fields whose value *is* a code."""
    if metadata is None or not isinstance(domain_name, str):
        return []
    domain = metadata.domain(domain_name)
    if domain is None:
        return []
    return sorted(str(code) for code in domain.coded_values)


def _seed_context_codes(
    lexicon: VoiceLexicon,
    resolver: ModelResolver,
    asset_type_key: str | None,
    context: OrderContext,
    properties: dict[str, Any],
) -> None:
    """Add the open work order's own codes to the fields they belong to.

    Reached by semantic role, never by field name (ADR-004): the business key takes the
    order's asset code, the network grouping takes its feeder. Adding them does not let
    the extractor invent anything — a proposal still requires the technician to have
    dictated those exact characters — but it is what makes the one code most likely to be
    said recognisable at all.
    """
    if asset_type_key is None:
        return
    try:
        asset_type = resolver.asset_type(asset_type_key)
    except (KeyError, ResolutionError):
        return
    by_role = (
        (AttributeRole.BUSINESS_KEY, context.asset_code),
        (AttributeRole.NETWORK_GROUPING, context.feeder_code),
    )
    for role, value in by_role:
        if not value:
            continue
        attribute = asset_type.attribute_with_role(role)
        if attribute is None or attribute.key not in properties:
            continue
        existing = lexicon.code_values.setdefault(attribute.key, [])
        if value not in existing:
            existing.append(value)
            existing.sort()


def _profile_says_volatile(
    resolver: ModelResolver, asset_type_key: str | None, attribute_key: str
) -> bool:
    """Whether the profile declares this attribute's catalogue as varying per unit."""
    if asset_type_key is None:
        return False
    try:
        bound = resolver.binding(asset_type_key).attributes.get(attribute_key)
    except ResolutionError:
        return False
    return bool(bound and bound.volatile_by_business_unit)
