"""Dynamic OData V4 discovery for Dynamics 365 Business Central.

This module fetches the ``$metadata`` document for the configured Business
Central environment, parses the EDMX into a list of entity-set descriptors,
and generates :class:`DynamicsBCODataStream` subclasses for each discovered
entity set.

The dynamic streams are appended to the tap's static stream list at discover
time. Set ``enable_odata_discovery`` on the tap config to turn discovery on,
and use the ``odata_discovery_include_prefixes`` /
``odata_discovery_exclude_prefixes`` keys to scope which entity sets are
surfaced.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Type
from xml.etree import ElementTree as ET

import requests

from tap_dynamics_bc.client import DynamicsBCODataStream
from tap_dynamics_bc.streams import CompaniesStream

if TYPE_CHECKING:
    from tap_dynamics_bc.tap import TapdynamicsBc

EDM_NS = "{http://docs.oasis-open.org/odata/ns/edm}"

ODATA_BASE_TEMPLATE = (
    "https://api.businesscentral.dynamics.com/v2.0/{tenant}/{environment}/ODataV4"
)

# Property names that, when present on an entity AND typed as a timestamp,
# are used as the replication key. Order is significant: the first match wins.
REPLICATION_KEY_CANDIDATES = (
    "SystemModifiedAt",
    "lastModifiedDateTime",
)

# EDM types accepted as a replication key.
_TIMESTAMP_EDM_TYPES = frozenset({"Edm.DateTime", "Edm.DateTimeOffset"})

# EDM scalar -> JSON Schema property mapping. Anything not listed defaults to
# a nullable string, which is the safe choice for unknown / complex EDM types.
_EDM_TO_JSON: Dict[str, Dict[str, Any]] = {
    "Edm.String": {"type": ["null", "string"]},
    "Edm.Guid": {"type": ["null", "string"]},
    "Edm.Binary": {"type": ["null", "string"]},
    "Edm.Boolean": {"type": ["null", "boolean"]},
    "Edm.Byte": {"type": ["null", "integer"]},
    "Edm.SByte": {"type": ["null", "integer"]},
    "Edm.Int16": {"type": ["null", "integer"]},
    "Edm.Int32": {"type": ["null", "integer"]},
    "Edm.Int64": {"type": ["null", "integer"]},
    "Edm.Single": {"type": ["null", "number"]},
    "Edm.Double": {"type": ["null", "number"]},
    "Edm.Decimal": {"type": ["null", "number"]},
    "Edm.Date": {"type": ["null", "string"], "format": "date"},
    "Edm.DateTime": {"type": ["null", "string"], "format": "date-time"},
    "Edm.DateTimeOffset": {"type": ["null", "string"], "format": "date-time"},
    "Edm.Time": {"type": ["null", "string"], "format": "time"},
    "Edm.TimeOfDay": {"type": ["null", "string"], "format": "time"},
    "Edm.Duration": {"type": ["null", "string"]},
}


class EntitySetDef(Dict[str, Any]):
    """Typed-dict-like container describing one OData entity set.

    Keys:
        name: entity set name as exposed in the service (e.g. ``AGBICustomers``).
        entity_type: short EDM entity type name (without namespace).
        key_props: list of primary key property names.
        properties: mapping of property name -> EDM type string.
    """


def parse_metadata_xml(xml_text: str) -> List[EntitySetDef]:
    """Parse an OData V4 ``$metadata`` document into entity-set definitions.

    Returns one :class:`EntitySetDef` per ``<EntitySet>`` declared inside any
    ``<EntityContainer>``. Properties and primary keys are pulled from the
    matching ``<EntityType>`` (matched by short name, namespace stripped).
    """
    root = ET.fromstring(xml_text)

    entity_types: Dict[str, Dict[str, Any]] = {}
    for et in root.iter(f"{EDM_NS}EntityType"):
        type_name = et.attrib.get("Name")
        if not type_name:
            continue
        key_props: List[str] = []
        key_node = et.find(f"{EDM_NS}Key")
        if key_node is not None:
            key_props = [
                k.attrib["Name"] for k in key_node.findall(f"{EDM_NS}PropertyRef")
            ]
        properties: Dict[str, str] = {}
        for prop in et.findall(f"{EDM_NS}Property"):
            properties[prop.attrib["Name"]] = prop.attrib.get("Type", "Edm.String")
        entity_types[type_name] = {"key_props": key_props, "properties": properties}

    sets: List[EntitySetDef] = []
    for container in root.iter(f"{EDM_NS}EntityContainer"):
        for es in container.findall(f"{EDM_NS}EntitySet"):
            name = es.attrib["Name"]
            type_ref = es.attrib.get("EntityType", "")
            short_type = type_ref.rsplit(".", 1)[-1]
            et_def = entity_types.get(short_type)
            if et_def is None:
                continue
            sets.append(
                EntitySetDef(
                    name=name,
                    entity_type=short_type,
                    key_props=list(et_def["key_props"]),
                    properties=dict(et_def["properties"]),
                )
            )
    return sets


def _edm_to_json_schema(edm_type: str) -> Dict[str, Any]:
    """Map an EDM scalar type string to a nullable JSON Schema property."""
    if edm_type.startswith("Collection("):
        inner = edm_type[len("Collection(") : -1]
        return {"type": ["null", "array"], "items": _edm_to_json_schema(inner)}
    return dict(_EDM_TO_JSON.get(edm_type, {"type": ["null", "string"]}))


def build_schema(entity_set: EntitySetDef) -> Dict[str, Any]:
    """Build a Singer-compatible JSON Schema dict for an entity set.

    Adds ``company_id`` and ``company_name`` so dynamically discovered streams
    behave like the hand-written ones (which carry parent-company context).
    """
    properties: Dict[str, Any] = {
        name: _edm_to_json_schema(edm_type)
        for name, edm_type in entity_set["properties"].items()
    }
    properties.setdefault("company_id", {"type": ["null", "string"]})
    properties.setdefault("company_name", {"type": ["null", "string"]})
    return {
        "type": ["null", "object"],
        "additionalProperties": True,
        "properties": properties,
    }


def pick_replication_key(entity_set: EntitySetDef) -> Optional[str]:
    """Return the first timestamp-typed modified-date property on the entity.

    Properties whose EDM type is not a timestamp (e.g. ``Edm.Date``) are
    skipped because the Singer SDK rejects them as replication keys.
    """
    props = entity_set["properties"]
    for candidate in REPLICATION_KEY_CANDIDATES:
        if props.get(candidate) in _TIMESTAMP_EDM_TYPES:
            return candidate
    return None


def _stream_class_name(name: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in name)
    return f"DynamicODataStream_{safe}"


def _filter_entity_sets(
    entity_sets: Iterable[EntitySetDef],
    *,
    include_prefixes: Optional[Iterable[str]] = None,
    exclude_prefixes: Optional[Iterable[str]] = None,
    skip_names: Optional[Iterable[str]] = None,
) -> List[EntitySetDef]:
    include_list = list(include_prefixes) if include_prefixes else []
    exclude_list = list(exclude_prefixes) if exclude_prefixes else []
    skip_set = set(skip_names) if skip_names else set()

    filtered: List[EntitySetDef] = []
    for es in entity_sets:
        name = es["name"]
        if name in skip_set:
            continue
        if include_list and not any(name.startswith(p) for p in include_list):
            continue
        if any(name.startswith(p) for p in exclude_list):
            continue
        if not es["key_props"]:
            continue
        filtered.append(es)
    return filtered


def build_dynamic_stream_classes(
    entity_sets: Iterable[EntitySetDef],
    parent_stream_type: Type[Any],
    *,
    include_prefixes: Optional[Iterable[str]] = None,
    exclude_prefixes: Optional[Iterable[str]] = None,
    skip_names: Optional[Iterable[str]] = None,
) -> List[Type[DynamicsBCODataStream]]:
    """Generate one :class:`DynamicsBCODataStream` subclass per entity set.

    ``include_prefixes`` / ``exclude_prefixes`` filter which entity-set names
    are surfaced. ``skip_names`` removes exact matches (used to avoid
    shadowing the hand-written REST streams already declared in the tap).
    Entity sets without a primary key are dropped because Singer requires one.
    """
    selected = _filter_entity_sets(
        entity_sets,
        include_prefixes=include_prefixes,
        exclude_prefixes=exclude_prefixes,
        skip_names=skip_names,
    )

    classes: List[Type[DynamicsBCODataStream]] = []
    for es in selected:
        replication_key = pick_replication_key(es)
        attrs: Dict[str, Any] = {
            "name": es["name"],
            "path": f"/Company('{{company_name}}')/{es['name']}",
            "primary_keys": list(es["key_props"]) + ["company_id"],
            "replication_key": replication_key,
            "schema": build_schema(es),
            "parent_stream_type": parent_stream_type,
            "__doc__": (
                f"Dynamically discovered OData entity set ``{es['name']}``."
            ),
        }
        cls = type(_stream_class_name(es["name"]), (DynamicsBCODataStream,), attrs)
        classes.append(cls)
    return classes


def fetch_metadata_xml(tap: "TapdynamicsBc") -> str:
    """Download the OData ``$metadata`` document for the tap's environment.

    Reuses the tap's existing OAuth flow via a transient ``CompaniesStream``
    instance, so token refresh and environment validation behave exactly as
    they do during normal sync.
    """
    helper_stream = CompaniesStream(tap=tap)
    environments = helper_stream.get_environments_list().get("value", [])
    target_name = tap.config.get("environment_name", "Production")
    chosen = next(
        (e for e in environments if e.get("name", "").lower() == target_name.lower()),
        None,
    )
    if chosen is None:
        raise RuntimeError(
            f"Could not find Business Central environment {target_name!r}; "
            f"available: {[e.get('name') for e in environments]}"
        )

    odata_base = ODATA_BASE_TEMPLATE.format(
        tenant=chosen["aadTenantId"], environment=chosen["name"]
    )
    url = f"{odata_base}/$metadata"
    headers = dict(helper_stream.authenticator.auth_headers or {})
    headers.setdefault("Accept", "application/xml")

    tap.logger.info("Fetching OData $metadata for discovery: %s", url)
    response = requests.get(url, headers=headers, timeout=120)
    response.raise_for_status()
    return response.text


def discover_dynamic_streams(
    tap: "TapdynamicsBc",
    parent_stream_type: Type[Any],
    *,
    include_prefixes: Optional[Iterable[str]] = None,
    exclude_prefixes: Optional[Iterable[str]] = None,
    skip_names: Optional[Iterable[str]] = None,
) -> List[DynamicsBCODataStream]:
    """High-level entry point: fetch metadata and instantiate dynamic streams.

    Returns a list of stream instances ready to be appended to the tap's
    discovered streams. Errors during metadata fetch / parse are *not*
    swallowed: ``enable_odata_discovery`` is an explicit opt-in, so a failure
    here is treated as a configuration / connectivity problem that should
    surface immediately instead of silently shrinking the catalog.
    """
    xml_text = fetch_metadata_xml(tap)
    entity_sets = parse_metadata_xml(xml_text)
    tap.logger.info("OData $metadata declared %d entity sets", len(entity_sets))

    classes = build_dynamic_stream_classes(
        entity_sets,
        parent_stream_type=parent_stream_type,
        include_prefixes=include_prefixes,
        exclude_prefixes=exclude_prefixes,
        skip_names=skip_names,
    )
    tap.logger.info(
        "OData dynamic discovery emitting %d stream(s) (filters: include=%s, exclude=%s, skip=%d)",
        len(classes),
        list(include_prefixes) if include_prefixes else None,
        list(exclude_prefixes) if exclude_prefixes else None,
        len(set(skip_names)) if skip_names else 0,
    )
    return [cls(tap=tap) for cls in classes]
