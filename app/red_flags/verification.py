from __future__ import annotations

import json
from typing import Any

from app.citations.validator import CitationValidator
from app.model_gateway.gateway import ModelGateway
from app.red_flags.prompts import RED_FLAG_VERIFICATION_PROMPT_VERSION
from app.red_flags.schemas import (
    RedFlagDraft,
    RedFlagOutput,
    RedFlagSeverity,
    RedFlagStatus,
    RedFlagVerificationOutput,
)


class HighSeverityFlagVerifier:
    """Publication gate for HIGH/CRITICAL flags."""

    def __init__(self, gateway: ModelGateway, citation_validator: CitationValidator) -> None:
        self.gateway = gateway
        self.citation_validator = citation_validator

    def verify(
        self,
        flags: list[RedFlagDraft],
        *,
        document_id: str,
        model_alias: str,
        timeout_seconds: int,
        workflow_id: str,
        step_id: str,
        context: Any | None = None,
    ) -> RedFlagOutput:
        passthrough: list[RedFlagDraft] = []
        eligible: list[RedFlagDraft] = []
        for flag in flags:
            if flag.severity not in {RedFlagSeverity.HIGH, RedFlagSeverity.CRITICAL}:
                passthrough.append(flag)
                continue
            valid_evidence = bool(flag.citations) and all(
                result.valid
                for result in self.citation_validator.validate_all(
                    flag.citations,
                    expected_document_id=document_id,
                )
            )
            if valid_evidence:
                eligible.append(flag)
            else:
                passthrough.append(
                    flag.model_copy(
                        update={
                            "status": RedFlagStatus.SUPPRESSED,
                            "verification_model": model_alias,
                            "verification_reason": "Insufficient or invalid citation evidence",
                        }
                    )
                )
        if eligible:
            flags_json = json.dumps(
                [flag.model_dump(mode="json", by_alias=True) for flag in eligible],
                ensure_ascii=False,
            )
            prompt = (
                f"Prompt version: {RED_FLAG_VERIFICATION_PROMPT_VERSION}. Verify only "
                "HIGH/CRITICAL flags against citation evidence. verified=true only when "
                "evidence is sufficient.\n"
                f"flags={flags_json}\n"
                f"context={json.dumps(context, ensure_ascii=False, default=str)}"
            )
            decisions = self.gateway.generate_structured(
                model_alias=model_alias,
                prompt=prompt,
                output_schema=RedFlagVerificationOutput,
                timeout_seconds=timeout_seconds,
                metadata={"workflowId": workflow_id, "stepId": step_id},
            )
            by_id = {decision.flag_id: decision for decision in decisions.decisions}
            for flag in eligible:
                decision = by_id.get(flag.flag_id)
                verified = bool(decision and decision.verified and decision.evidence_sufficient)
                passthrough.append(
                    flag.model_copy(
                        update={
                            "status": (
                                RedFlagStatus.VERIFIED if verified else RedFlagStatus.SUPPRESSED
                            ),
                            "verification_model": model_alias,
                            "verification_reason": (
                                decision.reason if decision else "Verifier omitted this flag"
                            ),
                        }
                    )
                )
        order = {flag.flag_id: index for index, flag in enumerate(flags)}
        passthrough.sort(key=lambda flag: order[flag.flag_id])
        return RedFlagOutput(flags=passthrough)
