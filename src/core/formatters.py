"""Centralized currency and locale formatting utilities for Indian Real Estate (INR)."""

from typing import Union


def indian_comma_format(val: Union[int, float], decimal_places: int = 0) -> str:
    """Format a numeric value using the official Indian numbering system (e.g. 1,08,00,000).
    
    In the Indian numbering system:
    - The rightmost three digits form the first group (hundreds).
    - All preceding digits are grouped in pairs (thousands, lakhs, crores).
    """
    if val is None:
        return "0"
    
    sign = "-" if val < 0 else ""
    abs_val = abs(val)
    
    if decimal_places == 0:
        int_part = int(round(abs_val))
        dec_part = ""
    else:
        int_part = int(abs_val)
        dec_part = f"{abs_val - int_part:.{decimal_places}f}"[1:]  # strip leading '0'
    
    s = str(int_part)
    if len(s) <= 3:
        res = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        res = ",".join(groups) + "," + last3
    
    return f"{sign}{res}{dec_part}"


def format_inr(
    val: Union[int, float],
    use_words: bool = False,
    decimal_places: int = 0,
    prefix: str = "₹",
) -> str:
    """Format an amount into Indian Rupees (INR).
    
    Examples:
        format_inr(12500000) -> "₹1,25,00,000"
        format_inr(12500000, use_words=True) -> "₹1.25 Crore"
        format_inr(8500000, use_words=True) -> "₹85.00 Lakh"
        format_inr(45000) -> "₹45,000"
    """
    if val is None:
        return f"{prefix}0"
    
    abs_val = abs(val)
    sign = "-" if val < 0 else ""
    
    if use_words:
        if abs_val >= 10_000_000:  # 1 Crore = 10,000,000
            crores = abs_val / 10_000_000
            cr_str = f"{crores:.2f}".rstrip("0").rstrip(".") if crores != int(crores) else f"{int(crores)}"
            return f"{sign}{prefix}{cr_str} Crore"
        elif abs_val >= 100_000:  # 1 Lakh = 100,000
            lakhs = abs_val / 100_000
            lk_str = f"{lakhs:.2f}".rstrip("0").rstrip(".") if lakhs != int(lakhs) else f"{int(lakhs)}"
            return f"{sign}{prefix}{lk_str} Lakh"
        elif abs_val >= 1_000:
            thousands = abs_val / 1_000
            th_str = f"{thousands:.1f}".rstrip("0").rstrip(".") if thousands != int(thousands) else f"{int(thousands)}"
            return f"{sign}{prefix}{th_str} Thousand"
    
    return f"{prefix}{indian_comma_format(val, decimal_places=decimal_places)}"


def format_inr_short(val: Union[int, float], prefix: str = "₹") -> str:
    """Short Indian currency notation for chart labels and compact badges (e.g. ₹1.25 Cr, ₹85.0 L)."""
    if val is None:
        return f"{prefix}0"
    abs_val = abs(val)
    sign = "-" if val < 0 else ""
    if abs_val >= 10_000_000:
        return f"{sign}{prefix}{abs_val / 10_000_000:.2f} Cr"
    elif abs_val >= 100_000:
        return f"{sign}{prefix}{abs_val / 100_000:.2f} L"
    elif abs_val >= 1_000:
        return f"{sign}{prefix}{abs_val / 1_000:.1f} k"
    return f"{sign}{prefix}{abs_val:,.0f}"


def format_rent(val: Union[int, float], compact: bool = False) -> str:
    """Format monthly rental rate (e.g. ₹45,000/month or ₹45,000/mo)."""
    if val is None:
        return "₹0/mo"
    unit = "/mo" if compact else "/month"
    return f"{format_inr(val)}{unit}"


def format_psf(val: Union[int, float]) -> str:
    """Format price per square foot (e.g. ₹8,500/sq ft)."""
    if val is None:
        return "₹0/sq ft"
    return f"{format_inr(val, decimal_places=0)}/sq ft"


def format_bhk(bedrooms: int, property_type: str = "Apartment") -> str:
    """Format residential layout in Indian BHK notation (e.g. 3 BHK, 2 BHK, 1 BHK, Studio)."""
    if bedrooms <= 0:
        return "Studio"
    return f"{bedrooms} BHK"


# Centralized locale constants
COUNTRY = "India"
CURRENCY_CODE = "INR"
CURRENCY_SYMBOL = "₹"
AREA_UNIT = "sq ft"
AREA_UNIT_LABEL = "sq ft"
POSTAL_TERM = "PIN Code"
DISTRICT_TERM = "District / Municipal Corporation"
MUNICIPAL_RECORDS_TERM = "Municipal / Sub-Registrar Records"
