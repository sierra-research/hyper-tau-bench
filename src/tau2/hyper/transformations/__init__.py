"""
Pluggable section transformations for information-distribution variants.

Importing this package registers the built-in transformations. To add a new
representation, subclass :class:`SectionTransformation`, call
:func:`register_transformation`, and import the module here — the kit builder,
manifests, and validation pick it up with no further wiring.
"""

# Built-in representations register themselves on import.
from tau2.hyper.transformations import (
    api_contract_pack as _api_contract_pack,  # noqa: F401
)
from tau2.hyper.transformations import (
    case_ledger_export as _case_ledger_export,  # noqa: F401
)
from tau2.hyper.transformations import (
    client_knowledge as _client_knowledge,  # noqa: F401
)
from tau2.hyper.transformations import (
    contact_center_qa_export as _contact_center_qa_export,  # noqa: F401
)
from tau2.hyper.transformations import (
    customer_kickoff_document as _customer_kickoff_document,  # noqa: F401
)
from tau2.hyper.transformations import (
    device_ui_screenshot as _device_ui_screenshot,  # noqa: F401
)
from tau2.hyper.transformations import (
    email_threads as _email_threads,  # noqa: F401
)
from tau2.hyper.transformations import (
    helpdesk_automation_export as _helpdesk_automation_export,  # noqa: F401
)
from tau2.hyper.transformations import (
    interactive_screen_recording as _interactive_screen_recording,  # noqa: F401
)
from tau2.hyper.transformations import (
    jira_issue_export as _jira_issue_export,  # noqa: F401
)
from tau2.hyper.transformations import (
    knowledge_base_html_export as _knowledge_base_html_export,  # noqa: F401
)
from tau2.hyper.transformations import (
    process_flowchart as _process_flowchart,  # noqa: F401
)
from tau2.hyper.transformations import (
    process_presentation as _process_presentation,  # noqa: F401
)
from tau2.hyper.transformations import prose as _prose  # noqa: F401
from tau2.hyper.transformations import (
    recorded_working_session as _recorded_working_session,  # noqa: F401
)
from tau2.hyper.transformations import (
    reference_documents as _reference_documents,  # noqa: F401
)
from tau2.hyper.transformations import slack_mcp as _slack_mcp  # noqa: F401
from tau2.hyper.transformations import transcripts as _transcripts  # noqa: F401
from tau2.hyper.transformations import (
    website_screenshot as _website_screenshot,  # noqa: F401
)
from tau2.hyper.transformations.base import (
    KitFile,
    SectionTransformation,
    TransformationArtifact,
    get_transformation,
    has_transformation,
    known_representations,
    register_transformation,
    resolve_section_transformations,
    select_section_transformation,
)
from tau2.hyper.transformations.bundles import (
    normalize_section_bundle_selection,
    resolve_transformation_bundle,
    resolve_transformation_bundles,
    resolve_transformation_spec_by_id,
)

# Variant compilation: coverage audit, fallback, reports. Imported after the
# built-ins so every representation is registered before compilation runs.
from tau2.hyper.transformations.compile import (
    FALLBACK_HEADING,
    FactCoverage,
    TransformationActivation,
    TransformationBundleActivation,
    VariantCompilation,
    compile_hyper_task,
    compile_variant_transformations,
    render_fallback_markdown,
)
from tau2.hyper.transformations.modality import (
    DEFAULT_KIT_MODALITY_PROFILE,
    ModalityProfile,
    modality_for_path,
    parse_modality_profile,
)

__all__ = [
    "KitFile",
    "TransformationArtifact",
    "SectionTransformation",
    "get_transformation",
    "has_transformation",
    "known_representations",
    "register_transformation",
    "resolve_section_transformations",
    "select_section_transformation",
    "normalize_section_bundle_selection",
    "resolve_transformation_bundle",
    "resolve_transformation_bundles",
    "resolve_transformation_spec_by_id",
    "DEFAULT_KIT_MODALITY_PROFILE",
    "ModalityProfile",
    "modality_for_path",
    "parse_modality_profile",
    "FALLBACK_HEADING",
    "FactCoverage",
    "TransformationActivation",
    "TransformationBundleActivation",
    "VariantCompilation",
    "compile_hyper_task",
    "compile_variant_transformations",
    "render_fallback_markdown",
]
