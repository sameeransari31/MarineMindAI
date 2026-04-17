"""
Seed realistic dummy noon reports for analytics testing.

Creates 3 vessels (if they don't exist) and populates ~30 days of daily
noon reports per vessel with correlated, physically plausible data:

  - Positions advance along real shipping routes
  - Fuel ROB depletes day-over-day based on consumption
  - Speed, RPM, ME load, and SFOC are correlated
  - Weather varies smoothly with occasional rough patches
  - Cargo condition changes between voyages
  - Draft adjusts with cargo condition
  - Anomalies are injected on ~5 % of days for anomaly detection testing

Usage:
    python manage.py seed_noon_reports          # seed if no noon reports exist
    python manage.py seed_noon_reports --force   # wipe existing and reseed
"""

import math
import random
from datetime import date, time, timedelta, datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from administration.models import Vessel, NoonReport


# ─────────────────────────────────────────────────────────────────────────────
# VESSEL TEMPLATES
# ─────────────────────────────────────────────────────────────────────────────

VESSEL_TEMPLATES = [
    {
        'name': 'MV Pacific Voyager',
        'vessel_type': 'bulk_carrier',
        'imo_number': '9876543',
        'call_sign': 'V7PV1',
        'flag_state': 'Panama',
        'classification_society': 'Lloyd\'s Register',
        'year_built': 2018,
        'dwt': 82000,
        'grt': 43500,
        'main_engine_type': 'MAN B&W 6S60MC-C',
        'main_engine_maker': 'MAN Energy Solutions',
        'main_engine_power_kw': 12240,
        'propeller_type': 'Fixed Pitch',
        'fleet_name': 'Asia-Pacific Fleet',
        'owner': 'Pacific Bulk Shipping Ltd',
        'manager': 'MarineMind Ship Management',
        'operational_status': 'active',
    },
    {
        'name': 'MT Arabian Star',
        'vessel_type': 'tanker',
        'imo_number': '9876544',
        'call_sign': 'A9AS2',
        'flag_state': 'Marshall Islands',
        'classification_society': 'DNV',
        'year_built': 2020,
        'dwt': 115000,
        'grt': 62000,
        'main_engine_type': 'MAN B&W 7S50ME-C',
        'main_engine_maker': 'MAN Energy Solutions',
        'main_engine_power_kw': 14280,
        'propeller_type': 'Fixed Pitch',
        'fleet_name': 'Middle East Fleet',
        'owner': 'Arabian Maritime Corp',
        'manager': 'MarineMind Ship Management',
        'operational_status': 'active',
    },
    {
        'name': 'MV Nordic Spirit',
        'vessel_type': 'container',
        'imo_number': '9876545',
        'call_sign': 'LABC3',
        'flag_state': 'Liberia',
        'classification_society': 'Bureau Veritas',
        'year_built': 2019,
        'dwt': 68000,
        'grt': 51000,
        'main_engine_type': 'Wärtsilä 8RT-flex68D',
        'main_engine_maker': 'Wärtsilä',
        'main_engine_power_kw': 27160,
        'propeller_type': 'Controllable Pitch',
        'fleet_name': 'Europe Fleet',
        'owner': 'Nordic Container Lines',
        'manager': 'MarineMind Ship Management',
        'operational_status': 'active',
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# ROUTE DEFINITIONS  (start → end waypoints for each vessel)
# ─────────────────────────────────────────────────────────────────────────────

ROUTES = {
    '9876543': {
        'voyages': [
            {
                'number': 'PV-2026-001',
                'departure': 'Singapore',
                'arrival': 'Qingdao',
                'cargo_condition': 'laden',
                'cargo_type': 'Iron Ore',
                'cargo_qty': 76000,
                'start_lat': 1.26, 'start_lon': 103.84,
                'end_lat': 36.07, 'end_lon': 120.38,
                'days': 14,
            },
            {
                'number': 'PV-2026-002',
                'departure': 'Qingdao',
                'arrival': 'Newcastle',
                'cargo_condition': 'ballast',
                'cargo_type': '',
                'cargo_qty': 0,
                'start_lat': 36.07, 'start_lon': 120.38,
                'end_lat': -32.93, 'end_lon': 151.78,
                'days': 16,
            },
        ],
    },
    '9876544': {
        'voyages': [
            {
                'number': 'AS-2026-001',
                'departure': 'Ras Tanura',
                'arrival': 'Rotterdam',
                'cargo_condition': 'laden',
                'cargo_type': 'Crude Oil',
                'cargo_qty': 105000,
                'start_lat': 26.68, 'start_lon': 50.16,
                'end_lat': 51.92, 'end_lon': 4.48,
                'days': 18,
            },
            {
                'number': 'AS-2026-002',
                'departure': 'Rotterdam',
                'arrival': 'Jebel Ali',
                'cargo_condition': 'ballast',
                'cargo_type': '',
                'cargo_qty': 0,
                'start_lat': 51.92, 'start_lon': 4.48,
                'end_lat': 25.01, 'end_lon': 55.08,
                'days': 12,
            },
        ],
    },
    '9876545': {
        'voyages': [
            {
                'number': 'NS-2026-001',
                'departure': 'Shanghai',
                'arrival': 'Hamburg',
                'cargo_condition': 'laden',
                'cargo_type': 'Containers (Mixed)',
                'cargo_qty': 52000,
                'start_lat': 31.23, 'start_lon': 121.47,
                'end_lat': 53.55, 'end_lon': 9.99,
                'days': 20,
            },
            {
                'number': 'NS-2026-002',
                'departure': 'Hamburg',
                'arrival': 'Algeciras',
                'cargo_condition': 'part_laden',
                'cargo_type': 'Containers (Mixed)',
                'cargo_qty': 28000,
                'start_lat': 53.55, 'start_lon': 9.99,
                'end_lat': 36.13, 'end_lon': -5.45,
                'days': 10,
            },
        ],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# DATA GENERATION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

WIND_DIRECTIONS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
CURRENT_DIRECTIONS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
REMARKS_POOL = [
    'Normal sea passage.',
    'All machinery operating normally.',
    'Slight vibration noted in ME exhaust valve #3 — monitoring.',
    'Carried out weekly lifeboat drill.',
    'Encountered fishing fleet — reduced speed temporarily.',
    'Minor swell from NW, no impact on schedule.',
    'Fresh water generator serviced during the watch.',
    'AE #2 taken offline for planned maintenance; AE #1 and #3 in service.',
    'Navigation in dense traffic — extra lookout posted.',
    'Completed bunkering report for charterers.',
    'Sighted dolphins — crew morale high.',
    'Deck washing carried out after cargo hold inspection.',
    'ETA revised due to weather routing advice.',
    'Good weather — all deck maintenance on schedule.',
    'Safety meeting held per SMS requirements.',
]


def _d(val, places=2):
    """Round to Decimal."""
    return Decimal(str(round(val, places)))


def _smooth_random(base, amplitude, day, period=7):
    """Sinusoidal base + small noise for smooth day-over-day variation."""
    return base + amplitude * math.sin(2 * math.pi * day / period) + random.gauss(0, amplitude * 0.3)


def _generate_weather_sequence(n_days):
    """
    Generate a correlated weather sequence so values don't jump wildly.
    Includes one or two rough-weather windows.
    """
    wind_forces = []
    base_wind = random.choice([3, 4])  # calm-ish
    rough_start = random.randint(4, n_days - 5) if n_days > 10 else -1

    for d in range(n_days):
        if rough_start <= d <= rough_start + 2:
            wf = random.randint(6, 8)
        else:
            wf = max(1, min(8, int(base_wind + random.gauss(0, 1.2))))
        wind_forces.append(wf)

    return wind_forces


class Command(BaseCommand):
    help = 'Seed realistic noon-report dummy data for analytics testing (3 vessels, ~30 days each).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Delete all existing noon reports and vessels before seeding.',
        )
        parser.add_argument(
            '--start-date',
            type=str,
            default=None,
            help='Start date for reports in YYYY-MM-DD format (default: 30 days ago).',
        )

    # ──────────────────────────────────────────────────────────────────────
    def handle(self, *args, **options):
        if options['force']:
            deleted_nr, _ = NoonReport.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Deleted {deleted_nr} existing noon report(s).'))
        elif NoonReport.objects.exists():
            self.stdout.write(self.style.NOTICE(
                'Noon reports already exist. Use --force to wipe and reseed.'
            ))
            return

        start_date = (
            datetime.strptime(options['start_date'], '%Y-%m-%d').date()
            if options['start_date']
            else date.today() - timedelta(days=30)
        )

        vessels = self._ensure_vessels()
        total = 0

        for vessel in vessels:
            count = self._generate_reports_for_vessel(vessel, start_date)
            total += count
            self.stdout.write(f'  → {vessel.name}: {count} noon reports')

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Seeded {total} noon reports across {len(vessels)} vessels.'
        ))

    # ──────────────────────────────────────────────────────────────────────
    def _ensure_vessels(self):
        """Create or fetch the three template vessels."""
        vessels = []
        for tpl in VESSEL_TEMPLATES:
            vessel, created = Vessel.objects.get_or_create(
                imo_number=tpl['imo_number'],
                defaults=tpl,
            )
            tag = 'created' if created else 'exists'
            self.stdout.write(f'  Vessel {vessel.name} [{tag}]')
            vessels.append(vessel)
        return vessels

    # ──────────────────────────────────────────────────────────────────────
    def _generate_reports_for_vessel(self, vessel, global_start):
        """Generate realistic noon reports across voyage legs."""
        route = ROUTES.get(vessel.imo_number)
        if not route:
            return 0

        reports = []
        current_date = global_start

        # Initial fuel/water ROB
        fo_rob = round(random.uniform(1800, 2200), 2)
        bf_rob = round(random.uniform(150, 250), 2)

        for voy in route['voyages']:
            n_days = voy['days']
            weather_seq = _generate_weather_sequence(n_days)

            # Speed profile depends on cargo condition
            if voy['cargo_condition'] == 'laden':
                base_speed = random.uniform(11.5, 13.0)
            elif voy['cargo_condition'] == 'ballast':
                base_speed = random.uniform(12.5, 14.0)
            else:
                base_speed = random.uniform(12.0, 13.5)

            speed_ordered = round(base_speed + random.uniform(0, 0.5), 1)
            base_rpm = base_speed * random.uniform(5.2, 5.6)

            # Distance for the whole voyage
            total_voyage_distance = base_speed * 24 * n_days * random.uniform(0.95, 1.02)

            # Draft depends on cargo
            if voy['cargo_condition'] == 'laden':
                draft_fore = random.uniform(12.0, 13.5)
                draft_aft = draft_fore + random.uniform(0.3, 0.8)
            elif voy['cargo_condition'] == 'ballast':
                draft_fore = random.uniform(5.5, 7.0)
                draft_aft = draft_fore + random.uniform(1.0, 2.0)
            else:
                draft_fore = random.uniform(9.0, 10.5)
                draft_aft = draft_fore + random.uniform(0.5, 1.0)

            for day_idx in range(n_days):
                progress = day_idx / max(n_days - 1, 1)  # 0→1

                # ── Position (linear interpolation with jitter) ──────
                lat = voy['start_lat'] + (voy['end_lat'] - voy['start_lat']) * progress
                lon = voy['start_lon'] + (voy['end_lon'] - voy['start_lon']) * progress
                lat += random.gauss(0, 0.15)
                lon += random.gauss(0, 0.15)

                # ── Weather ──────────────────────────────────────────
                wf = weather_seq[day_idx]
                sea_state = max(0, min(9, wf - random.randint(0, 1)))
                swell = round(max(0.2, wf * 0.45 + random.gauss(0, 0.3)), 1)

                # Weather penalty on speed
                weather_penalty = max(0, (wf - 5) * 0.4) if wf > 5 else 0

                # ── Speed / RPM / distance ───────────────────────────
                day_speed = _smooth_random(base_speed - weather_penalty, 0.5, day_idx, period=5)
                day_speed = max(5.0, min(16.0, day_speed))
                day_rpm = _smooth_random(base_rpm, 1.5, day_idx, period=6)
                day_rpm = max(40, min(95, day_rpm))
                distance_sailed = day_speed * random.uniform(22.5, 24.0)
                distance_to_go = max(0, total_voyage_distance * (1 - progress))
                slip = random.uniform(1.5, 5.5) + (weather_penalty * 0.8)

                # ── Steaming hours ───────────────────────────────────
                hours_steaming = round(random.uniform(23.0, 24.0), 2)
                hours_stopped = round(24.0 - hours_steaming, 2)

                # ── Engine performance ───────────────────────────────
                me_load = _smooth_random(65, 8, day_idx, period=8)
                me_load = max(40, min(90, me_load))
                me_power = vessel.main_engine_power_kw * (me_load / 100) if vessel.main_engine_power_kw else 8000
                me_exhaust_temp = 280 + me_load * 1.2 + random.gauss(0, 5)

                # ── Fuel consumption (correlated with load) ──────────
                fo_consumption = (me_load / 100) * random.uniform(28, 36)
                if voy['cargo_condition'] == 'laden':
                    fo_consumption *= 1.08  # laden burns more
                bf_consumption = random.uniform(0.5, 2.0)
                ae_fo = random.uniform(2.5, 5.0)
                boiler_fo = random.uniform(0.8, 2.0)

                sfoc = (fo_consumption * 1000) / max(me_power * (hours_steaming / 24), 1)  # g/kWh approx
                sfoc = max(150, min(220, sfoc))

                # Deplete ROB
                fo_rob = max(100, fo_rob - fo_consumption - ae_fo - boiler_fo)
                bf_rob = max(10, bf_rob - bf_consumption)

                # ── Lube oil ─────────────────────────────────────────
                me_cyl_oil = round(random.uniform(40, 80), 2)
                me_sys_oil = round(random.uniform(5, 15), 2)
                ae_lub = round(random.uniform(2, 8), 2)

                # ── Fresh water ──────────────────────────────────────
                fw_consumption = round(random.uniform(8, 18), 2)
                fw_produced = round(fw_consumption * random.uniform(0.7, 1.1), 2)

                # ── AE running hours ─────────────────────────────────
                ae_hours = round(random.uniform(36, 72), 1)  # across AEs

                # ── Misc weather ─────────────────────────────────────
                air_temp = _smooth_random(26, 4, day_idx, period=10) + (lat * -0.15)
                sea_temp = air_temp - random.uniform(0.5, 2.5)
                baro = _smooth_random(1013, 5, day_idx, period=12)
                visibility = max(1.0, random.uniform(5, 15) - wf * 0.5)
                current_kn = round(random.uniform(0.2, 2.0), 1)

                # ── ETA ──────────────────────────────────────────────
                days_remaining = n_days - day_idx
                eta = datetime.combine(
                    current_date + timedelta(days=days_remaining),
                    time(random.randint(6, 18), random.choice([0, 30])),
                )
                eta = timezone.make_aware(eta) if timezone.is_naive(eta) else eta

                # ── Anomaly injection (~5 % of reports) ──────────────
                is_anomaly = random.random() < 0.05
                if is_anomaly:
                    anomaly_type = random.choice(['high_fo', 'low_speed', 'high_sfoc'])
                    if anomaly_type == 'high_fo':
                        fo_consumption *= 1.6
                    elif anomaly_type == 'low_speed':
                        day_speed *= 0.55
                    elif anomaly_type == 'high_sfoc':
                        sfoc *= 1.5

                report = NoonReport(
                    vessel=vessel,
                    report_date=current_date,
                    report_time=time(12, 0),
                    latitude=_d(lat, 6),
                    longitude=_d(lon, 6),
                    voyage_number=voy['number'],
                    port_of_departure=voy['departure'],
                    port_of_arrival=voy['arrival'],
                    eta=eta,
                    speed_avg=_d(day_speed),
                    speed_ordered=_d(speed_ordered),
                    distance_sailed=_d(distance_sailed),
                    distance_to_go=_d(distance_to_go),
                    rpm_avg=_d(day_rpm),
                    slip_percent=_d(slip),
                    fo_consumption=_d(fo_consumption),
                    bf_consumption=_d(bf_consumption),
                    fo_rob=_d(fo_rob),
                    bf_rob=_d(bf_rob),
                    me_load_percent=_d(me_load),
                    me_power_kw=_d(me_power, 1),
                    me_exhaust_temp=_d(me_exhaust_temp, 1),
                    sfoc=_d(sfoc),
                    me_cylinder_oil_consumption=_d(me_cyl_oil),
                    me_system_oil_consumption=_d(me_sys_oil),
                    ae_lub_oil_consumption=_d(ae_lub),
                    draft_fore=_d(draft_fore),
                    draft_aft=_d(draft_aft),
                    draft_mean=_d((draft_fore + draft_aft) / 2),
                    cargo_condition=voy['cargo_condition'],
                    cargo_quantity=_d(voy['cargo_qty']),
                    cargo_type=voy['cargo_type'],
                    ae_running_hours=_d(ae_hours, 1),
                    ae_fo_consumption=_d(ae_fo),
                    boiler_fo_consumption=_d(boiler_fo),
                    fw_consumption=_d(fw_consumption),
                    fw_produced=_d(fw_produced),
                    wind_force=wf,
                    wind_direction=random.choice(WIND_DIRECTIONS),
                    sea_state=sea_state,
                    swell_height=_d(swell, 1),
                    current_knots=_d(current_kn, 1),
                    current_direction=random.choice(CURRENT_DIRECTIONS),
                    visibility=_d(visibility, 1),
                    air_temp=_d(air_temp, 1),
                    sea_water_temp=_d(sea_temp, 1),
                    barometric_pressure=_d(baro, 1),
                    hours_steaming=_d(hours_steaming),
                    hours_stopped=_d(hours_stopped),
                    remarks=random.choice(REMARKS_POOL),
                    is_validated=True,
                )
                reports.append(report)
                current_date += timedelta(days=1)

        NoonReport.objects.bulk_create(reports, ignore_conflicts=True)
        return len(reports)
