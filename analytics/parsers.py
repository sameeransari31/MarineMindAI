"""
Parsers for CSV and Excel noon report files.
Normalizes column names and yields row dicts for validation.
"""
import csv
import io
import re


# ─────────────────────────────────────────────────────────────────────────────
# COLUMN NAME MAPPING — maps common header variations to model field names
# ─────────────────────────────────────────────────────────────────────────────

COLUMN_ALIASES = {
    # Report info
    'report_date': 'report_date',
    'date': 'report_date',
    'report date': 'report_date',
    'report_time': 'report_time',
    'time': 'report_time',
    'report time': 'report_time',
    'voyage_number': 'voyage_number',
    'voyage number': 'voyage_number',
    'voyage no': 'voyage_number',
    'voyage': 'voyage_number',
    'voy no': 'voyage_number',

    # Position
    'latitude': 'latitude',
    'lat': 'latitude',
    'longitude': 'longitude',
    'lon': 'longitude',
    'lng': 'longitude',
    'long': 'longitude',

    # Ports
    'port_of_departure': 'port_of_departure',
    'port of departure': 'port_of_departure',
    'departure port': 'port_of_departure',
    'from port': 'port_of_departure',
    'port_of_arrival': 'port_of_arrival',
    'port of arrival': 'port_of_arrival',
    'arrival port': 'port_of_arrival',
    'to port': 'port_of_arrival',
    'destination': 'port_of_arrival',
    'eta': 'eta',

    # Speed & distance
    'speed_avg': 'speed_avg',
    'average speed': 'speed_avg',
    'avg speed': 'speed_avg',
    'speed (kts)': 'speed_avg',
    'speed avg': 'speed_avg',
    'speed': 'speed_avg',
    'speed_ordered': 'speed_ordered',
    'speed ordered': 'speed_ordered',
    'ordered speed': 'speed_ordered',
    'distance_sailed': 'distance_sailed',
    'distance sailed': 'distance_sailed',
    'distance': 'distance_sailed',
    'dist sailed': 'distance_sailed',
    'distance_to_go': 'distance_to_go',
    'distance to go': 'distance_to_go',
    'dtg': 'distance_to_go',

    # Engine performance
    'rpm_avg': 'rpm_avg',
    'rpm': 'rpm_avg',
    'avg rpm': 'rpm_avg',
    'rpm avg': 'rpm_avg',
    'slip_percent': 'slip_percent',
    'slip': 'slip_percent',
    'slip %': 'slip_percent',
    'slip percent': 'slip_percent',
    'me_load_percent': 'me_load_percent',
    'me load': 'me_load_percent',
    'me load %': 'me_load_percent',
    'engine load': 'me_load_percent',
    'me_power_kw': 'me_power_kw',
    'me power': 'me_power_kw',
    'me power kw': 'me_power_kw',
    'engine power': 'me_power_kw',
    'me_exhaust_temp': 'me_exhaust_temp',
    'me exhaust temp': 'me_exhaust_temp',
    'exhaust temp': 'me_exhaust_temp',
    'sfoc': 'sfoc',

    # Fuel
    'fo_consumption': 'fo_consumption',
    'fo consumption': 'fo_consumption',
    'fo cons': 'fo_consumption',
    'hfo consumption': 'fo_consumption',
    'fuel oil consumption': 'fo_consumption',
    'bf_consumption': 'bf_consumption',
    'bf consumption': 'bf_consumption',
    'bf cons': 'bf_consumption',
    'bio fuel consumption': 'bf_consumption',
    'fo_rob': 'fo_rob',
    'fo rob': 'fo_rob',
    'hfo rob': 'fo_rob',
    'bf_rob': 'bf_rob',
    'bf rob': 'bf_rob',
    'ae_fo_consumption': 'ae_fo_consumption',
    'ae fo consumption': 'ae_fo_consumption',
    'ae fo cons': 'ae_fo_consumption',
    'boiler_fo_consumption': 'boiler_fo_consumption',
    'boiler fo consumption': 'boiler_fo_consumption',
    'boiler fo cons': 'boiler_fo_consumption',

    # Lube oil
    'me_cylinder_oil_consumption': 'me_cylinder_oil_consumption',
    'me cyl oil': 'me_cylinder_oil_consumption',
    'cylinder oil': 'me_cylinder_oil_consumption',
    'me cyl oil consumption': 'me_cylinder_oil_consumption',
    'me_system_oil_consumption': 'me_system_oil_consumption',
    'me sys oil': 'me_system_oil_consumption',
    'system oil': 'me_system_oil_consumption',
    'me system oil consumption': 'me_system_oil_consumption',
    'ae_lub_oil_consumption': 'ae_lub_oil_consumption',
    'ae lub oil': 'ae_lub_oil_consumption',
    'ae lube oil': 'ae_lub_oil_consumption',

    # Draft
    'draft_fore': 'draft_fore',
    'draft fore': 'draft_fore',
    'draft fwd': 'draft_fore',
    'forward draft': 'draft_fore',
    'fwd draft': 'draft_fore',
    'draft_aft': 'draft_aft',
    'draft aft': 'draft_aft',
    'aft draft': 'draft_aft',
    'draft_mean': 'draft_mean',
    'draft mean': 'draft_mean',
    'mean draft': 'draft_mean',

    # Cargo
    'cargo_condition': 'cargo_condition',
    'cargo condition': 'cargo_condition',
    'condition': 'cargo_condition',
    'laden/ballast': 'cargo_condition',
    'cargo_quantity': 'cargo_quantity',
    'cargo quantity': 'cargo_quantity',
    'cargo qty': 'cargo_quantity',
    'cargo weight': 'cargo_quantity',
    'cargo_type': 'cargo_type',
    'cargo type': 'cargo_type',
    'cargo': 'cargo_type',

    # Auxiliary / fresh water
    'ae_running_hours': 'ae_running_hours',
    'ae running hours': 'ae_running_hours',
    'ae hours': 'ae_running_hours',
    'fw_consumption': 'fw_consumption',
    'fw consumption': 'fw_consumption',
    'fresh water consumption': 'fw_consumption',
    'fw_produced': 'fw_produced',
    'fw produced': 'fw_produced',
    'fresh water produced': 'fw_produced',

    # Weather
    'wind_force': 'wind_force',
    'wind force': 'wind_force',
    'wind (bf)': 'wind_force',
    'beaufort': 'wind_force',
    'wind_direction': 'wind_direction',
    'wind direction': 'wind_direction',
    'wind dir': 'wind_direction',
    'sea_state': 'sea_state',
    'sea state': 'sea_state',
    'douglas scale': 'sea_state',
    'swell_height': 'swell_height',
    'swell height': 'swell_height',
    'swell': 'swell_height',
    'current_knots': 'current_knots',
    'current knots': 'current_knots',
    'current': 'current_knots',
    'current_direction': 'current_direction',
    'current direction': 'current_direction',
    'current dir': 'current_direction',
    'visibility': 'visibility',
    'air_temp': 'air_temp',
    'air temp': 'air_temp',
    'air temperature': 'air_temp',
    'sea_water_temp': 'sea_water_temp',
    'sea water temp': 'sea_water_temp',
    'sea temp': 'sea_water_temp',
    'sea water temperature': 'sea_water_temp',
    'barometric_pressure': 'barometric_pressure',
    'barometric pressure': 'barometric_pressure',
    'pressure': 'barometric_pressure',
    'baro pressure': 'barometric_pressure',

    # Steaming
    'hours_steaming': 'hours_steaming',
    'hours steaming': 'hours_steaming',
    'steaming hours': 'hours_steaming',
    'hours_stopped': 'hours_stopped',
    'hours stopped': 'hours_stopped',
    'stopped hours': 'hours_stopped',

    # Notes
    'remarks': 'remarks',
    'remark': 'remarks',
    'notes': 'remarks',
    'comment': 'remarks',
    'comments': 'remarks',
}


def _normalize_column_name(name: str) -> str | None:
    """Normalize a raw column header to a model field name, or None if unrecognized."""
    cleaned = re.sub(r'[^\w\s/()%]', '', str(name)).strip().lower()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return COLUMN_ALIASES.get(cleaned)


def _map_columns(headers: list[str]) -> tuple[dict[int, str], list[str]]:
    """
    Map column indices to model field names.
    Returns (index_to_field_map, unmapped_columns).
    """
    mapping = {}
    unmapped = []
    for idx, header in enumerate(headers):
        field = _normalize_column_name(header)
        if field:
            mapping[idx] = field
        else:
            unmapped.append(header)
    return mapping, unmapped


def parse_csv(file_obj) -> tuple[list[dict], list[str], list[str]]:
    """
    Parse a CSV file into a list of row dicts with normalized field names.

    Returns:
        (rows, unmapped_columns, parse_errors)
    """
    parse_errors = []
    try:
        content = file_obj.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8-sig')
        reader = csv.reader(io.StringIO(content))
        headers = next(reader, None)
        if not headers:
            return [], [], ['CSV file is empty or has no header row.']

        col_map, unmapped = _map_columns(headers)
        if not col_map:
            return [], unmapped, ['No recognizable column headers found in the CSV.']

        rows = []
        for line_num, raw_row in enumerate(reader, start=2):
            if not any(cell.strip() for cell in raw_row):
                continue  # skip blank lines
            row_dict = {}
            for idx, field in col_map.items():
                if idx < len(raw_row):
                    row_dict[field] = raw_row[idx].strip()
                else:
                    row_dict[field] = None
            rows.append(row_dict)

        return rows, unmapped, parse_errors

    except UnicodeDecodeError:
        return [], [], ['File encoding error. Please use UTF-8 encoded CSV files.']
    except Exception as e:
        return [], [], [f'Failed to parse CSV: {str(e)}']


def parse_excel(file_obj) -> tuple[list[dict], list[str], list[str]]:
    """
    Parse an Excel (.xlsx) file into a list of row dicts with normalized field names.

    Returns:
        (rows, unmapped_columns, parse_errors)
    """
    parse_errors = []
    try:
        import openpyxl
    except ImportError:
        return [], [], ['openpyxl is required for Excel file support. Install it with: pip install openpyxl']

    try:
        wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)

        header_row = next(rows_iter, None)
        if not header_row:
            return [], [], ['Excel file is empty or has no header row.']

        headers = [str(h) if h is not None else '' for h in header_row]
        col_map, unmapped = _map_columns(headers)
        if not col_map:
            return [], unmapped, ['No recognizable column headers found in the Excel file.']

        rows = []
        for raw_row in rows_iter:
            if not any(cell is not None for cell in raw_row):
                continue  # skip blank lines
            row_dict = {}
            for idx, field in col_map.items():
                if idx < len(raw_row):
                    row_dict[field] = raw_row[idx]
                else:
                    row_dict[field] = None
            rows.append(row_dict)

        wb.close()
        return rows, unmapped, parse_errors

    except Exception as e:
        return [], [], [f'Failed to parse Excel file: {str(e)}']
