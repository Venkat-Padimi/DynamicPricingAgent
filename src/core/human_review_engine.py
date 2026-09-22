"""Human Review Engine for enforced Human-in-the-Loop oversight."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from src.core.enums import ReviewStatus
from src.core.models import (
    HumanReviewDecision,
    RentalPricingResult,
    ValuationResult,
)


class HumanReviewEngine:
    """Enforces strict Human-in-the-Loop (HITL) approval gates before final decision release."""

    @classmethod
    def approve_recommendation(
        cls,
        reviewer_name: str,
        reviewer_role: str,
        valuation: ValuationResult,
        rental_pricing: RentalPricingResult,
        notes: str = "Approved as decision-support baseline.",
        review_id: Optional[str] = None,
    ) -> HumanReviewDecision:
        """Process APPROVE action accepting AI valuation and rental recommendation."""
        if not reviewer_name or not reviewer_name.strip():
            raise ValueError("Human review approval failed: 'reviewer_name' is mandatory.")

        rev_id = review_id or f"REV-{uuid.uuid4().hex[:8].upper()}"
        return HumanReviewDecision(
            review_id=rev_id,
            reviewer_name=reviewer_name.strip(),
            reviewer_role=reviewer_role.strip() if reviewer_role else "Real Estate Asset Manager",
            status=ReviewStatus.APPROVED,
            original_valuation=valuation.estimated_value,
            original_recommended_rent=rental_pricing.recommended_midpoint,
            modified_valuation=None,
            modified_recommended_rent=None,
            reviewer_notes=notes.strip(),
            evidence_request_details=None,
            decision_timestamp=datetime.now(timezone.utc),
        )

    @classmethod
    def modify_recommendation(
        cls,
        reviewer_name: str,
        reviewer_role: str,
        valuation: ValuationResult,
        rental_pricing: RentalPricingResult,
        modified_valuation: Optional[float] = None,
        modified_recommended_rent: Optional[float] = None,
        notes: str = "",
        review_id: Optional[str] = None,
    ) -> HumanReviewDecision:
        """Process MODIFY action applying human overrides to valuation or rental pricing."""
        if not reviewer_name or not reviewer_name.strip():
            raise ValueError("Human review modification failed: 'reviewer_name' is mandatory.")

        if modified_valuation is None and modified_recommended_rent is None:
            raise ValueError("Human review modification failed: at least one override (valuation or rent) must be provided.")

        if modified_valuation is not None and modified_valuation <= 0:
            raise ValueError("Human review modification failed: 'modified_valuation' must be positive.")

        if modified_recommended_rent is not None and modified_recommended_rent <= 0:
            raise ValueError("Human review modification failed: 'modified_recommended_rent' must be positive.")

        if not notes or not notes.strip():
            raise ValueError("Human review modification failed: justification 'notes' are required when overriding AI values.")

        rev_id = review_id or f"REV-{uuid.uuid4().hex[:8].upper()}"
        return HumanReviewDecision(
            review_id=rev_id,
            reviewer_name=reviewer_name.strip(),
            reviewer_role=reviewer_role.strip() if reviewer_role else "Real Estate Asset Manager",
            status=ReviewStatus.MODIFIED,
            original_valuation=valuation.estimated_value,
            original_recommended_rent=rental_pricing.recommended_midpoint,
            modified_valuation=modified_valuation,
            modified_recommended_rent=modified_recommended_rent,
            reviewer_notes=notes.strip(),
            evidence_request_details=None,
            decision_timestamp=datetime.now(timezone.utc),
        )

    @classmethod
    def reject_recommendation(
        cls,
        reviewer_name: str,
        reviewer_role: str,
        valuation: ValuationResult,
        rental_pricing: RentalPricingResult,
        rejection_reason: str,
        review_id: Optional[str] = None,
    ) -> HumanReviewDecision:
        """Process REJECT action stopping finalization and recording audit rationale."""
        if not reviewer_name or not reviewer_name.strip():
            raise ValueError("Human review rejection failed: 'reviewer_name' is mandatory.")

        if not rejection_reason or not rejection_reason.strip():
            raise ValueError("Human review rejection failed: 'rejection_reason' notes are required.")

        rev_id = review_id or f"REV-{uuid.uuid4().hex[:8].upper()}"
        return HumanReviewDecision(
            review_id=rev_id,
            reviewer_name=reviewer_name.strip(),
            reviewer_role=reviewer_role.strip() if reviewer_role else "Real Estate Asset Manager",
            status=ReviewStatus.REJECTED,
            original_valuation=valuation.estimated_value,
            original_recommended_rent=rental_pricing.recommended_midpoint,
            modified_valuation=None,
            modified_recommended_rent=None,
            reviewer_notes=f"REJECTED: {rejection_reason.strip()}",
            evidence_request_details=None,
            decision_timestamp=datetime.now(timezone.utc),
        )

    @classmethod
    def request_more_evidence(
        cls,
        reviewer_name: str,
        reviewer_role: str,
        valuation: ValuationResult,
        rental_pricing: RentalPricingResult,
        evidence_request_details: str,
        review_id: Optional[str] = None,
    ) -> HumanReviewDecision:
        """Process REQUEST_MORE_EVIDENCE action signaling system to gather additional market records."""
        if not reviewer_name or not reviewer_name.strip():
            raise ValueError("Evidence request failed: 'reviewer_name' is mandatory.")

        if not evidence_request_details or not evidence_request_details.strip():
            raise ValueError("Evidence request failed: 'evidence_request_details' must specify what evidence is required.")

        rev_id = review_id or f"REV-{uuid.uuid4().hex[:8].upper()}"
        return HumanReviewDecision(
            review_id=rev_id,
            reviewer_name=reviewer_name.strip(),
            reviewer_role=reviewer_role.strip() if reviewer_role else "Real Estate Asset Manager",
            status=ReviewStatus.EVIDENCE_REQUESTED,
            original_valuation=valuation.estimated_value,
            original_recommended_rent=rental_pricing.recommended_midpoint,
            modified_valuation=None,
            modified_recommended_rent=None,
            reviewer_notes=f"Evidence Requested: {evidence_request_details.strip()}",
            evidence_request_details=evidence_request_details.strip(),
            decision_timestamp=datetime.now(timezone.utc),
        )
