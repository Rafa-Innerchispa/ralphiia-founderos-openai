from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from quoteops.contracts import (
    CatalogDraftReviewRequest,
    ConversationMessageRequest,
    EvidenceReviewRequest,
    MissionApprovalRequest,
    MissionDeliveryRequest,
    MultimodalEvidenceCreateRequest,
    PackageSelectionRequest,
    QuoteUpdateRequest,
    SupplierOfferCreateRequest,
)


def _with_mission_id(schema: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(schema)
    properties = value.setdefault("properties", {})
    properties["mission_id"] = {
        "type": "string",
        "pattern": r"^mission_[a-f0-9]{18}$",
        "description": "Existing QuoteOps mission identifier.",
    }
    required = value.setdefault("required", [])
    if "mission_id" not in required:
        required.insert(0, "mission_id")
    return value


MCP_TOOLS = [
    {
        "name": "quoteops_start_or_continue_mission",
        "description": (
            "Create or continue an idempotent bilingual QuoteOps case from natural language. "
            "Use source_channel=chatgpt_mcp when called from ChatGPT."
        ),
        "inputSchema": ConversationMessageRequest.model_json_schema(),
    },
    {
        "name": "quoteops_get_mission",
        "description": "Read the current case file, task, packages, quote, and timeline without writing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mission_id": {"type": "string", "pattern": r"^mission_[a-f0-9]{18}$"},
                "language": {"type": "string", "enum": ["es", "en"], "default": "es"},
            },
            "required": ["mission_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "quoteops_add_supplier_offer",
        "description": (
            "Record exact supplier costs with source evidence. It creates only staging catalog drafts; "
            "it never creates canonical inventory or guesses selling prices."
        ),
        "inputSchema": _with_mission_id(SupplierOfferCreateRequest.model_json_schema()),
    },
    {
        "name": "quoteops_record_extracted_evidence",
        "description": (
            "Persist structured facts extracted by ChatGPT from an image, PDF, product label, site "
            "photo, or price list. Extracted data remains reviewable and does not change canonical "
            "catalog or quote prices automatically."
        ),
        "inputSchema": _with_mission_id(MultimodalEvidenceCreateRequest.model_json_schema()),
    },
    {
        "name": "quoteops_review_extracted_evidence",
        "description": "Confirm or reject one extracted evidence record after human review.",
        "inputSchema": {
            **_with_mission_id(EvidenceReviewRequest.model_json_schema()),
            "properties": {
                **_with_mission_id(EvidenceReviewRequest.model_json_schema())["properties"],
                "evidence_id": {"type": "string", "pattern": r"^evidence_[a-f0-9]{18}$"},
            },
            "required": ["mission_id", "evidence_id", "idempotency_key", "decision", "reviewed_by"],
        },
    },
    {
        "name": "quoteops_review_catalog_draft",
        "description": (
            "Approve or reject a new product or service draft after human review. Approval writes "
            "only to the isolated QuoteOps staging catalog, never to canonical inventory."
        ),
        "inputSchema": {
            **_with_mission_id(CatalogDraftReviewRequest.model_json_schema()),
            "properties": {
                **_with_mission_id(CatalogDraftReviewRequest.model_json_schema())["properties"],
                "catalog_draft_id": {"type": "string", "pattern": r"^catalogdraft_[a-f0-9]{18}$"},
            },
            "required": [
                "mission_id",
                "catalog_draft_id",
                "idempotency_key",
                "decision",
                "reviewed_by",
            ],
        },
    },
    {
        "name": "quoteops_select_package",
        "description": (
            "Select package A, B, or C and create an editable quote. Supplier costs are retained as "
            "internal evidence while all unconfirmed selling prices remain zero."
        ),
        "inputSchema": _with_mission_id(PackageSelectionRequest.model_json_schema()),
    },
    {
        "name": "quoteops_update_quote",
        "description": "Save human-confirmed selling prices for the selected editable quote.",
        "inputSchema": _with_mission_id(QuoteUpdateRequest.model_json_schema()),
    },
    {
        "name": "quoteops_approve_quote",
        "description": "Record human approval and generate the local PDF. Approval is always explicit.",
        "inputSchema": _with_mission_id(MissionApprovalRequest.model_json_schema()),
    },
    {
        "name": "quoteops_register_delivery",
        "description": (
            "Register delivery after approval. Staging does not perform private external delivery when "
            "production writes are disabled."
        ),
        "inputSchema": _with_mission_id(MissionDeliveryRequest.model_json_schema()),
    },
]


class QuoteOpsMcpContract:
    """Typed adapter used by the staging MCP endpoint and future central proxy."""

    def __init__(self, conversation, execution_service) -> None:
        self.conversation = conversation
        self.execution_service = execution_service

    @staticmethod
    def tools() -> list[dict[str, Any]]:
        return deepcopy(MCP_TOOLS)

    def call(self, name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
        args = dict(arguments or {})
        try:
            if name == "quoteops_start_or_continue_mission":
                args.setdefault("source_channel", "chatgpt_mcp")
                return self.conversation.message(ConversationMessageRequest.model_validate(args)).model_dump()
            if name == "quoteops_get_mission":
                return self.conversation.get(
                    str(args.get("mission_id") or ""),
                    str(args.get("language") or "es"),
                ).model_dump()
            mission_id = str(args.pop("mission_id", ""))
            if not mission_id:
                return {"ok": False, "error": "mission_id_required"}
            if name == "quoteops_add_supplier_offer":
                return self.conversation.add_supplier_offer(
                    mission_id,
                    SupplierOfferCreateRequest.model_validate(args),
                )
            if name == "quoteops_record_extracted_evidence":
                return self.conversation.record_extracted_evidence(
                    mission_id,
                    MultimodalEvidenceCreateRequest.model_validate(args),
                )
            if name == "quoteops_review_extracted_evidence":
                evidence_id = str(args.pop("evidence_id", ""))
                if not evidence_id:
                    return {"ok": False, "error": "evidence_id_required"}
                return self.conversation.review_extracted_evidence(
                    mission_id,
                    evidence_id,
                    EvidenceReviewRequest.model_validate(args),
                )
            if name == "quoteops_review_catalog_draft":
                catalog_draft_id = str(args.pop("catalog_draft_id", ""))
                if not catalog_draft_id:
                    return {"ok": False, "error": "catalog_draft_id_required"}
                return self.conversation.review_catalog_draft(
                    mission_id,
                    catalog_draft_id,
                    CatalogDraftReviewRequest.model_validate(args),
                )
            if name == "quoteops_select_package":
                return self.conversation.select_package(
                    mission_id,
                    PackageSelectionRequest.model_validate(args),
                ).model_dump()
            if name == "quoteops_update_quote":
                return self.conversation.update_quote(
                    mission_id,
                    QuoteUpdateRequest.model_validate(args),
                ).model_dump()
            if name == "quoteops_approve_quote":
                return self.conversation.approve(
                    mission_id,
                    MissionApprovalRequest.model_validate(args),
                    self.execution_service,
                )
            if name == "quoteops_register_delivery":
                return self.conversation.deliver(
                    mission_id,
                    MissionDeliveryRequest.model_validate(args),
                    self.execution_service,
                )
            return {"ok": False, "error": "unknown_tool", "tool": name}
        except ValidationError as exc:
            return {
                "ok": False,
                "error": "validation_error",
                "fields": [
                    {"field": ".".join(str(item) for item in error["loc"]), "code": error["type"]}
                    for error in exc.errors()
                ],
            }
        except KeyError:
            return {"ok": False, "error": "mission_not_found"}
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
