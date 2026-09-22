"""Lease & Rent-Roll Analysis Engine."""

from typing import List, Optional, Tuple

from src.core.enums import DataOrigin, LeaseStatus
from src.core.models import ProvenanceMetadata, RentRollSummary, RentRollUnit


class LeaseAnalysisEngine:
    """Deterministic operational analysis engine for rent rolls, occupancy, and lease cliff risk."""

    @classmethod
    def verify_tenant_privacy(cls, units: List[RentRollUnit]) -> bool:
        """Verify strict tenant privacy safeguards (no names, emails, phone numbers, or PII)."""
        forbidden_indicators = ["@", "mr.", "mrs.", "ms.", "dr.", "inc", "llc"]
        for u in units:
            pseudo = u.tenant_pseudonym.lower()
            if not u.tenant_pseudonym.startswith("TENANT-"):
                return False
            if any(ind in pseudo for ind in forbidden_indicators):
                return False
            if " " in u.tenant_pseudonym:
                return False
        return True

    @classmethod
    def analyze_rent_roll(
        cls,
        property_id: str,
        units: List[RentRollUnit],
        provenance: Optional[ProvenanceMetadata] = None,
    ) -> Optional[RentRollSummary]:
        """Perform comprehensive deterministic calculation of operational metrics."""
        if not units:
            return None

        # Verify zero PII
        cls.verify_tenant_privacy(units)

        total_units = len(units)
        occupied_units = sum(1 for u in units if u.lease_status == LeaseStatus.OCCUPIED)
        vacant_units = total_units - occupied_units

        # Physical metrics
        physical_occupancy = round(occupied_units / total_units, 4) if total_units > 0 else 0.0
        physical_vacancy = round(vacant_units / total_units, 4) if total_units > 0 else 0.0

        # Current in-place income
        in_place_monthly = sum(u.current_rent for u in units if u.lease_status != LeaseStatus.VACANT)
        annual_in_place = round(in_place_monthly * 12.0, 2)

        # Average occupied PSF for potential rent baseline
        occupied_sqft = sum(u.sqft for u in units if u.lease_status != LeaseStatus.VACANT)
        avg_occ_psf = (in_place_monthly / occupied_sqft) if occupied_sqft > 0 else 25.0

        # Gross potential rent
        gross_potential = 0.0
        for u in units:
            if u.lease_status != LeaseStatus.VACANT and u.current_rent > 0:
                gross_potential += u.current_rent
            else:
                gross_potential += u.sqft * avg_occ_psf
        gross_potential = round(gross_potential, 2)

        # Economic occupancy and vacancy
        economic_occupancy = round(in_place_monthly / gross_potential, 4) if gross_potential > 0 else 0.0
        economic_vacancy = round(1.0 - economic_occupancy, 4)

        total_sqft = sum(u.sqft for u in units)
        avg_rent_unit = round(in_place_monthly / occupied_units, 2) if occupied_units > 0 else 0.0
        avg_rent_psf = round(in_place_monthly / total_sqft, 2) if total_sqft > 0 else 0.0

        # Lease expiration cliff analysis
        exp_30 = sum(1 for u in units if 0 < u.days_until_expiration <= 30 and u.lease_status != LeaseStatus.VACANT)
        exp_60 = sum(1 for u in units if 30 < u.days_until_expiration <= 60 and u.lease_status != LeaseStatus.VACANT)
        exp_90 = sum(1 for u in units if 60 < u.days_until_expiration <= 90 and u.lease_status != LeaseStatus.VACANT)
        exp_beyond_90 = sum(1 for u in units if u.days_until_expiration > 90 and u.lease_status != LeaseStatus.VACANT)

        expiring_90_units = [
            u for u in units if 0 < u.days_until_expiration <= 90 and u.lease_status != LeaseStatus.VACANT
        ]
        exp_rent_90 = round(sum(u.current_rent for u in expiring_90_units), 2)
        exp_sqft_90 = round(sum(u.sqft for u in expiring_90_units), 2)

        turnover_exposure_pct = (
            round((len(expiring_90_units) / total_units) * 100, 2) if total_units > 0 else 0.0
        )

        if turnover_exposure_pct >= 40.0:
            cliff_risk = "HIGH"
        elif turnover_exposure_pct >= 20.0:
            cliff_risk = "MEDIUM"
        else:
            cliff_risk = "LOW"

        potential_gap = round(gross_potential - in_place_monthly, 2)

        return RentRollSummary(
            property_id=property_id,
            total_units=total_units,
            occupied_units=occupied_units,
            physical_occupancy_rate=physical_occupancy,
            economic_occupancy_rate=economic_occupancy,
            physical_vacancy_rate=physical_vacancy,
            economic_vacancy_rate=economic_vacancy,
            gross_potential_monthly_rent=gross_potential,
            current_in_place_monthly_rent=round(in_place_monthly, 2),
            gross_annual_in_place_rent=annual_in_place,
            avg_rent_per_unit=avg_rent_unit,
            avg_rent_psf=avg_rent_psf,
            expiring_within_30_days=exp_30,
            expiring_within_60_days=exp_60,
            expiring_within_90_days=exp_90,
            expiring_beyond_90_days=exp_beyond_90,
            expiring_rent_within_90_days=exp_rent_90,
            expiring_sqft_within_90_days=exp_sqft_90,
            lease_turnover_exposure_pct=turnover_exposure_pct,
            cliff_risk_level=cliff_risk,
            potential_rent_gap=potential_gap,
            data_origin=provenance.origin if provenance else DataOrigin.SYNTHETIC_DEMONSTRATION_DATA,
            provenance=provenance,
        )

    @classmethod
    def generate_narratives(cls, summary: RentRollSummary) -> Tuple[str, str]:
        """Generate separate factual summary and agent operational interpretation."""
        facts = (
            f"Property operates at {summary.physical_occupancy_rate * 100:.1f}% physical occupancy "
            f"({summary.occupied_units}/{summary.total_units} units) with ₹{summary.current_in_place_monthly_rent:,.2f} "
            f"in-place monthly rent. Economic occupancy is {summary.economic_occupancy_rate * 100:.1f}%. "
            f"{summary.expiring_within_30_days + summary.expiring_within_60_days + summary.expiring_within_90_days} "
            f"unit(s) face lease expiration within 90 days, representing ₹{summary.expiring_rent_within_90_days:,.2f} "
            f"in monthly rent exposure ({summary.lease_turnover_exposure_pct:.1f}% of units)."
        )

        if summary.cliff_risk_level == "HIGH":
            interp = (
                "Elevated lease cliff risk: over 40% of units roll over within 90 days. "
                "Aggressive renewal negotiations or pre-leasing incentives are strongly advised."
            )
        elif summary.cliff_risk_level == "MEDIUM":
            interp = (
                "Moderate lease rollover exposure over the coming quarter. "
                "Current in-place rent sits below gross potential, offering an opportunity to capture rent growth on turnover."
            )
        else:
            interp = (
                "Stable lease maturity profile with low near-term vacancy risk. "
                "Focus should remain on operational expense management and tenant retention."
            )

        return facts, interp
