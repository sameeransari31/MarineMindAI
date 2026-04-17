"""
Validation layer for noon report data.
Validates field types, ranges, and required fields before saving.
"""
from datetime import date, time
from decimal import Decimal, InvalidOperation


# ─────────────────────────────────────────────────────────────────────────────
# FIELD DEFINITIONS: name → (required, type, min, max, unit)
# ─────────────────────────────────────────────────────────────────────────────

FIELD_RULES = {
    'report_date': {'required': True, 'type': 'date'},
    'report_time': {'required': False, 'type': 'time'},
    'voyage_number': {'required': False, 'type': 'string', 'max_length': 50},
    'latitude': {'required': False, 'type': 'decimal', 'min': -90, 'max': 90},
    'longitude': {'required': False, 'type': 'decimal', 'min': -180, 'max': 180},
    'port_of_departure': {'required': False, 'type': 'string', 'max_length': 100},
    'port_of_arrival': {'required': False, 'type': 'string', 'max_length': 100},
    'speed_avg': {'required': False, 'type': 'decimal', 'min': 0, 'max': 35},
    'speed_ordered': {'required': False, 'type': 'decimal', 'min': 0, 'max': 35},
    'distance_sailed': {'required': False, 'type': 'decimal', 'min': 0, 'max': 999},
    'distance_to_go': {'required': False, 'type': 'decimal', 'min': 0, 'max': 99999},
    'rpm_avg': {'required': False, 'type': 'decimal', 'min': 0, 'max': 250},
    'slip_percent': {'required': False, 'type': 'decimal', 'min': -30, 'max': 50},
    'me_load_percent': {'required': False, 'type': 'decimal', 'min': 0, 'max': 110},
    'me_power_kw': {'required': False, 'type': 'decimal', 'min': 0, 'max': 100000},
    'me_exhaust_temp': {'required': False, 'type': 'decimal', 'min': 0, 'max': 600},
    'sfoc': {'required': False, 'type': 'decimal', 'min': 100, 'max': 300},
    'fo_consumption': {'required': False, 'type': 'decimal', 'min': 0, 'max': 300},
    'bf_consumption': {'required': False, 'type': 'decimal', 'min': 0, 'max': 100},
    'fo_rob': {'required': False, 'type': 'decimal', 'min': 0, 'max': 99999},
    'bf_rob': {'required': False, 'type': 'decimal', 'min': 0, 'max': 99999},
    'ae_fo_consumption': {'required': False, 'type': 'decimal', 'min': 0, 'max': 50},
    'boiler_fo_consumption': {'required': False, 'type': 'decimal', 'min': 0, 'max': 50},
    'me_cylinder_oil_consumption': {'required': False, 'type': 'decimal', 'min': 0, 'max': 500},
    'me_system_oil_consumption': {'required': False, 'type': 'decimal', 'min': 0, 'max': 500},
    'ae_lub_oil_consumption': {'required': False, 'type': 'decimal', 'min': 0, 'max': 500},
    'draft_fore': {'required': False, 'type': 'decimal', 'min': 0, 'max': 30},
    'draft_aft': {'required': False, 'type': 'decimal', 'min': 0, 'max': 30},
    'draft_mean': {'required': False, 'type': 'decimal', 'min': 0, 'max': 30},
    'cargo_condition': {'required': False, 'type': 'choice', 'choices': ['laden', 'ballast', 'part_laden']},
    'cargo_quantity': {'required': False, 'type': 'decimal', 'min': 0, 'max': 500000},
    'cargo_type': {'required': False, 'type': 'string', 'max_length': 100},
    'ae_running_hours': {'required': False, 'type': 'decimal', 'min': 0, 'max': 24},
    'fw_consumption': {'required': False, 'type': 'decimal', 'min': 0, 'max': 200},
    'fw_produced': {'required': False, 'type': 'decimal', 'min': 0, 'max': 200},
    'wind_force': {'required': False, 'type': 'integer', 'min': 0, 'max': 12},
    'wind_direction': {'required': False, 'type': 'string', 'max_length': 10},
    'sea_state': {'required': False, 'type': 'integer', 'min': 0, 'max': 9},
    'swell_height': {'required': False, 'type': 'decimal', 'min': 0, 'max': 20},
    'current_knots': {'required': False, 'type': 'decimal', 'min': 0, 'max': 10},
    'current_direction': {'required': False, 'type': 'string', 'max_length': 10},
    'visibility': {'required': False, 'type': 'decimal', 'min': 0, 'max': 50},
    'air_temp': {'required': False, 'type': 'decimal', 'min': -40, 'max': 60},
    'sea_water_temp': {'required': False, 'type': 'decimal', 'min': -5, 'max': 40},
    'barometric_pressure': {'required': False, 'type': 'decimal', 'min': 900, 'max': 1100},
    'hours_steaming': {'required': False, 'type': 'decimal', 'min': 0, 'max': 24},
    'hours_stopped': {'required': False, 'type': 'decimal', 'min': 0, 'max': 24},
    'remarks': {'required': False, 'type': 'string'},
}


def _parse_date(value):
    """Try multiple date formats."""
    if isinstance(value, date):
        return value
    from datetime import datetime
    formats = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y', '%Y/%m/%d']
    for fmt in formats:
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def _parse_time(value):
    """Try multiple time formats."""
    if isinstance(value, time):
        return value
    from datetime import datetime
    formats = ['%H:%M:%S', '%H:%M', '%H%M']
    for fmt in formats:
        try:
            return datetime.strptime(str(value).strip(), fmt).time()
        except (ValueError, TypeError):
            continue
    return None


def _parse_decimal(value):
    """Parse a value to Decimal, handling common formats."""
    if value is None or str(value).strip() == '':
        return None
    try:
        cleaned = str(value).strip().replace(',', '')
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _parse_integer(value):
    """Parse a value to integer."""
    if value is None or str(value).strip() == '':
        return None
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return None


def validate_noon_report_row(row_data: dict) -> tuple[dict, list[str]]:
    """
    Validate a single row of noon report data.

    Args:
        row_data: Dict of field_name → raw value from the parsed file.

    Returns:
        (cleaned_data, errors) — cleaned_data has parsed/typed values;
        errors is a list of human-readable messages.
    """
    cleaned = {}
    errors = []

    for field_name, rules in FIELD_RULES.items():
        raw_value = row_data.get(field_name)
        is_empty = raw_value is None or str(raw_value).strip() in ('', 'nan', 'NaN', 'None', 'N/A', '-')

        # Required check
        if rules.get('required') and is_empty:
            errors.append(f"'{field_name}' is required but missing or empty.")
            continue

        if is_empty:
            cleaned[field_name] = None
            continue

        field_type = rules['type']

        # ── Date ──
        if field_type == 'date':
            parsed = _parse_date(raw_value)
            if parsed is None:
                errors.append(f"'{field_name}': invalid date format '{raw_value}'.")
            elif parsed > date.today():
                errors.append(f"'{field_name}': date {parsed} is in the future.")
            else:
                cleaned[field_name] = parsed

        # ── Time ──
        elif field_type == 'time':
            parsed = _parse_time(raw_value)
            if parsed is None:
                errors.append(f"'{field_name}': invalid time format '{raw_value}'.")
            else:
                cleaned[field_name] = parsed

        # ── Decimal ──
        elif field_type == 'decimal':
            parsed = _parse_decimal(raw_value)
            if parsed is None:
                errors.append(f"'{field_name}': cannot parse '{raw_value}' as a number.")
            else:
                min_val = rules.get('min')
                max_val = rules.get('max')
                if min_val is not None and parsed < Decimal(str(min_val)):
                    errors.append(f"'{field_name}': value {parsed} is below minimum {min_val}.")
                elif max_val is not None and parsed > Decimal(str(max_val)):
                    errors.append(f"'{field_name}': value {parsed} exceeds maximum {max_val}.")
                else:
                    cleaned[field_name] = parsed

        # ── Integer ──
        elif field_type == 'integer':
            parsed = _parse_integer(raw_value)
            if parsed is None:
                errors.append(f"'{field_name}': cannot parse '{raw_value}' as an integer.")
            else:
                min_val = rules.get('min')
                max_val = rules.get('max')
                if min_val is not None and parsed < min_val:
                    errors.append(f"'{field_name}': value {parsed} is below minimum {min_val}.")
                elif max_val is not None and parsed > max_val:
                    errors.append(f"'{field_name}': value {parsed} exceeds maximum {max_val}.")
                else:
                    cleaned[field_name] = parsed

        # ── Choice ──
        elif field_type == 'choice':
            val = str(raw_value).strip().lower().replace(' ', '_')
            allowed = rules.get('choices', [])
            if val not in allowed:
                errors.append(f"'{field_name}': '{raw_value}' is not a valid choice. Expected: {allowed}.")
            else:
                cleaned[field_name] = val

        # ── String ──
        elif field_type == 'string':
            val = str(raw_value).strip()
            max_length = rules.get('max_length')
            if max_length and len(val) > max_length:
                errors.append(f"'{field_name}': value exceeds max length of {max_length}.")
            else:
                cleaned[field_name] = val

    return cleaned, errors
