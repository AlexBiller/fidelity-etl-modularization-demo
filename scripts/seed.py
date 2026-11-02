#!/usr/bin/env python3
"""Seed script for the unofficial ETL modularization demo.

Generates a fictional legacy ETL monolith ("ledger-etl") with 32 modules,
their dependency graph, a migration risk score, and before/after code plus
tests for each module. Every name, number and record is synthetic.

Usage: python3 scripts/seed.py   (writes data/seed.json and data/seed.js)
"""
import json
import random
from pathlib import Path

SEED = 20261102
ROOT = Path(__file__).resolve().parent.parent

TEAMS = ["Team Atlas", "Team Juniper", "Team Halyard", "Team Meridian", "Team Kestrel",
         "Team Sextant", "Team Bramble", "Team Lantern"]

# (id, domain, archetype, layer, entity label, table)
MODULES = [
    ("refdata.security_master", "Reference Data", "refdata", 0, "security", "ref_security"),
    ("refdata.account_master", "Reference Data", "refdata", 0, "account", "ref_account"),
    ("refdata.business_calendar", "Reference Data", "refdata", 0, "calendar_day", "ref_calendar"),
    ("refdata.fund_universe", "Reference Data", "refdata", 0, "fund", "ref_fund"),
    ("marketdata.eod_prices", "Market Data", "ingest", 0, "eod_price", "md_eod_price"),
    ("marketdata.fx_rates", "Market Data", "ingest", 0, "fx_rate", "md_fx_rate"),
    ("marketdata.price_normalize", "Market Data", "rollup", 1, "normalized_price", "md_price_norm"),
    ("custody.trade_capture", "Custody & Clearing", "ingest", 1, "trade", "cst_trade"),
    ("custody.corporate_actions", "Custody & Clearing", "ingest", 1, "corp_action", "cst_corp_action"),
    ("brokerage.order_fills_ingest", "Brokerage", "ingest", 1, "order_fill", "brk_order_fill"),
    ("retirement.payroll_contrib_ingest", "Workplace Retirement", "ingest", 1, "contribution", "ret_contribution"),
    ("funds.share_class_map", "Asset Management", "refdata", 1, "share_class", "fnd_share_class"),
    ("custody.settlement_recon", "Custody & Clearing", "recon", 2, "settlement", "cst_settle_break"),
    ("brokerage.positions_daily", "Brokerage", "rollup", 2, "position", "brk_position_daily"),
    ("brokerage.cash_sweep", "Brokerage", "calc", 2, "sweep", "brk_cash_sweep"),
    ("funds.nav_calc", "Asset Management", "calc", 2, "nav", "fnd_nav"),
    ("retirement.plan_balances", "Workplace Retirement", "rollup", 2, "plan_balance", "ret_plan_balance"),
    ("compliance.surveillance_feed", "Compliance", "export", 2, "surveillance", "cmp_surveillance"),
    ("brokerage.cost_basis", "Brokerage", "calc", 3, "cost_basis", "brk_cost_basis"),
    ("brokerage.margin_exposure", "Brokerage", "calc", 3, "margin", "brk_margin_exposure"),
    ("retirement.vesting_calc", "Workplace Retirement", "calc", 3, "vesting", "ret_vesting"),
    ("retirement.contrib_recon", "Workplace Retirement", "recon", 3, "contrib_break", "ret_contrib_break"),
    ("funds.fund_flows_rollup", "Asset Management", "rollup", 3, "fund_flow", "fnd_flow_daily"),
    ("compliance.wash_sale_flags", "Compliance", "calc", 3, "wash_sale", "cmp_wash_sale"),
    ("wealth.household_rollup", "Wealth Management", "rollup", 3, "household", "wlt_household"),
    ("funds.performance_attribution", "Asset Management", "calc", 4, "attribution", "fnd_attribution"),
    ("tax.form_1099b_prep", "Tax & Statements", "export", 4, "form_1099b", "tax_1099b"),
    ("statements.monthly_brokerage", "Tax & Statements", "export", 4, "brokerage_stmt", "stm_brokerage_monthly"),
    ("statements.retirement_quarterly", "Tax & Statements", "export", 4, "retirement_stmt", "stm_retirement_qtr"),
    ("compliance.reg_reporting_extract", "Compliance", "export", 4, "reg_report", "cmp_reg_extract"),
    ("wealth.advisor_book_rollup", "Wealth Management", "rollup", 4, "advisor_book", "wlt_advisor_book"),
    ("statements.consolidated_annual", "Tax & Statements", "export", 5, "annual_stmt", "stm_consolidated_annual"),
]

# Hand-picked upstream dependencies so the graph reads sensibly.
DEPS = {
    "marketdata.eod_prices": ["refdata.security_master", "refdata.business_calendar"],
    "marketdata.fx_rates": ["refdata.business_calendar"],
    "marketdata.price_normalize": ["marketdata.eod_prices", "marketdata.fx_rates"],
    "custody.trade_capture": ["refdata.security_master", "refdata.account_master"],
    "custody.corporate_actions": ["refdata.security_master"],
    "brokerage.order_fills_ingest": ["refdata.security_master", "refdata.account_master"],
    "retirement.payroll_contrib_ingest": ["refdata.account_master", "refdata.business_calendar"],
    "funds.share_class_map": ["refdata.fund_universe"],
    "custody.settlement_recon": ["custody.trade_capture", "refdata.business_calendar"],
    "brokerage.positions_daily": ["brokerage.order_fills_ingest", "marketdata.price_normalize", "custody.corporate_actions"],
    "brokerage.cash_sweep": ["brokerage.order_fills_ingest", "refdata.account_master"],
    "funds.nav_calc": ["funds.share_class_map", "marketdata.price_normalize"],
    "retirement.plan_balances": ["retirement.payroll_contrib_ingest", "marketdata.price_normalize"],
    "compliance.surveillance_feed": ["custody.trade_capture", "brokerage.order_fills_ingest"],
    "brokerage.cost_basis": ["brokerage.positions_daily", "custody.corporate_actions"],
    "brokerage.margin_exposure": ["brokerage.positions_daily", "brokerage.cash_sweep"],
    "retirement.vesting_calc": ["retirement.plan_balances"],
    "retirement.contrib_recon": ["retirement.payroll_contrib_ingest", "retirement.plan_balances"],
    "funds.fund_flows_rollup": ["funds.nav_calc", "retirement.plan_balances"],
    "compliance.wash_sale_flags": ["brokerage.positions_daily", "custody.trade_capture"],
    "wealth.household_rollup": ["brokerage.positions_daily", "retirement.plan_balances"],
    "funds.performance_attribution": ["funds.nav_calc", "funds.fund_flows_rollup"],
    "tax.form_1099b_prep": ["brokerage.cost_basis", "compliance.wash_sale_flags"],
    "statements.monthly_brokerage": ["brokerage.positions_daily", "brokerage.cost_basis", "brokerage.cash_sweep"],
    "statements.retirement_quarterly": ["retirement.plan_balances", "retirement.vesting_calc"],
    "compliance.reg_reporting_extract": ["compliance.surveillance_feed", "compliance.wash_sale_flags"],
    "wealth.advisor_book_rollup": ["wealth.household_rollup", "brokerage.margin_exposure"],
    "statements.consolidated_annual": ["statements.monthly_brokerage", "statements.retirement_quarterly", "tax.form_1099b_prep"],
}

# ---------------------------------------------------------------- templates
# Tokens: __MOD__ (dotted id), __PATH__ (monolith path), __PKG__ (submodule
# package), __CLASS__, __TABLE__, __ENTITY__, __UP__ (first upstream dotted
# id), __UP_PKG__, __UP_CLASS__, __UP_TABLE__, __KEY__, __FEED__.

TEMPLATES = {}

TEMPLATES["refdata"] = {
    "kind": "Reference-data cache",
    "before": '''# ledger_etl/jobs/__PATH__.py  (legacy monolith)
from ledger_etl.common.utils import *
from ledger_etl.common import db

_CACHE = {}          # read directly from __CALLERS__ call sites

def refresh(as_of=None):
    global _CACHE
    rows = db.query("SELECT * FROM __TABLE__ WHERE active_flag='Y'")
    _CACHE = dict((r["__KEY__"], r) for r in rows)
    log_info("loaded %d __ENTITY__ rows" % len(_CACHE))
    return len(_CACHE)

def get(key):
    if not _CACHE:
        refresh()
    return _CACHE.get(key)

def get_many(keys):
    return [get(k) for k in keys]
''',
    "after": '''# submodules/__PKG__/src/__PKG__/lookup.py
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Mapping, Optional

from ledger_contracts.refdata import __CLASS__, __CLASS__Lookup
from ledger_platform.io import TableReader
from ledger_platform.obs import get_logger

log = get_logger(__name__)

@dataclass(frozen=True)
class Snapshot__CLASS__Lookup(__CLASS__Lookup):
    """Immutable, point-in-time view of __TABLE__."""
    rows: Mapping[str, __CLASS__]
    as_of: date

    @classmethod
    def load(cls, reader: TableReader, as_of: date) -> "Snapshot__CLASS__Lookup":
        rows = {r.__KEY__: __CLASS__.from_row(r)
                for r in reader.where("__TABLE__", active_flag="Y", as_of=as_of)}
        log.info("loaded __ENTITY__ snapshot", count=len(rows), as_of=as_of)
        return cls(rows=rows, as_of=as_of)

    def get(self, key: str) -> Optional[__CLASS__]:
        return self.rows.get(key)

    def get_many(self, keys: Iterable[str]) -> list[Optional[__CLASS__]]:
        return [self.rows.get(k) for k in keys]
''',
    "changes": [
        "Replaced module-level mutable `_CACHE` with an immutable point-in-time snapshot",
        "Published a typed `__CLASS__Lookup` contract in `ledger_contracts.refdata`",
        "Rewired __CALLERS__ monolith call sites to the contract via a compatibility shim",
        "Removed the hidden lazy refresh that made job order matter",
    ],
    "tests": [
        ("test_contract_matches_legacy_columns", "contract"),
        ("test_snapshot_is_immutable", "unit"),
        ("test_get_many_preserves_order_and_missing", "unit"),
        ("test_parity_vs_legacy_cache[golden_2026-09-30]", "parity"),
        ("test_no_imports_of_legacy_cache", "boundary"),
    ],
}

TEMPLATES["ingest"] = {
    "kind": "Feed ingestion job",
    "before": '''# ledger_etl/jobs/__PATH__.py  (legacy monolith)
from ledger_etl.common.utils import *
from ledger_etl.common import db, config
from ledger_etl.jobs.__UP__ import _CACHE as UPSTREAM   # reach-in to private state

CONFIG = config.load_global()

def run(as_of=None):
    as_of = as_of or today_str()
    path = CONFIG["feeds"]["__FEED__"] % as_of
    rows = read_fixed_width(path, LAYOUT___UPPER__)
    out = []
    for r in rows:
        if r["rec_type"] == "99":            # trailer record
            continue
        ref = UPSTREAM.get(r["ref_key"])
        if ref is None:
            log_warn("unknown ref %s" % r["ref_key"])
            continue
        r["asset_class"] = ref["asset_class"]
        r["load_ts"] = now()
        out.append(r)
    db.write("__TABLE__", out, mode="append")
    db.execute("UPDATE etl_control SET last_run='%s' WHERE job='__MOD__'" % as_of)
    return len(out)
''',
    "after": '''# submodules/__PKG__/src/__PKG__/job.py
from dataclasses import dataclass
from datetime import date

from ledger_contracts.__UP_PKG__ import __UP_CLASS__Lookup
from ledger_platform.io import FeedReader, TableWriter, ControlStore
from .schema import __CLASS__Record, LAYOUT

@dataclass(frozen=True)
class __CLASS__Ingest:
    feeds: FeedReader
    refs: __UP_CLASS__Lookup
    sink: TableWriter
    control: ControlStore

    def run(self, as_of: date) -> int:
        records = []
        for raw in self.feeds.read_fixed_width("__FEED__", as_of, LAYOUT):
            if raw.rec_type == "99":         # trailer record
                continue
            ref = self.refs.get(raw.ref_key)
            if ref is None:
                self.feeds.quarantine(raw, reason="unknown_ref")
                continue
            records.append(__CLASS__Record.from_raw(raw, asset_class=ref.asset_class))
        self.sink.append("__TABLE__", records, partition=as_of)
        self.control.mark_complete("__MOD__", as_of)
        return len(records)
''',
    "changes": [
        "Injected the upstream lookup through its published contract instead of importing `_CACHE`",
        "Unknown references are quarantined for review instead of silently dropped",
        "Replaced string-formatted SQL on `etl_control` with `ControlStore.mark_complete`",
        "Added a typed `__CLASS__Record` schema generated from the legacy fixed-width layout",
    ],
    "tests": [
        ("test_layout_roundtrip_fixed_width", "unit"),
        ("test_trailer_records_skipped", "unit"),
        ("test_unknown_ref_is_quarantined", "unit"),
        ("test_parity_vs_legacy_output[golden_2026-09-30]", "parity"),
        ("test_parity_vs_legacy_output[golden_2026-10-31]", "parity"),
        ("test_no_cross_module_imports", "boundary"),
    ],
}

TEMPLATES["recon"] = {
    "kind": "Reconciliation job",
    "before": '''# ledger_etl/jobs/__PATH__.py  (legacy monolith)
from ledger_etl.common.utils import *
from ledger_etl.common import db
from ledger_etl.jobs.__UP__ import load_today   # calls into another job

TOLERANCE = 0.01

def run(as_of=None):
    as_of = as_of or today_str()
    ours = load_today(as_of)
    theirs = db.query("SELECT * FROM ext___TABLE__ WHERE as_of='%s'" % as_of)
    idx = dict((t["ref_id"], t) for t in theirs)
    breaks = []
    for o in ours:
        t = idx.pop(o["ref_id"], None)
        if t is None:
            breaks.append(dict(o, reason="MISSING_EXTERNAL"))
        elif abs(float(o["amount"]) - float(t["amount"])) > TOLERANCE:
            breaks.append(dict(o, reason="AMOUNT_MISMATCH", ext=t["amount"]))
    for t in idx.values():
        breaks.append(dict(t, reason="MISSING_INTERNAL"))
    db.write("__TABLE__", breaks, mode="overwrite")
    if len(breaks) > 500:
        send_email("ops-dl", "recon breaks: %d" % len(breaks))
    return breaks
''',
    "after": '''# submodules/__PKG__/src/__PKG__/recon.py
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ledger_contracts.__UP_PKG__ import __UP_CLASS__Source
from ledger_platform.io import TableReader, TableWriter, Alerts
from .schema import Break

TOLERANCE = Decimal("0.01")

@dataclass(frozen=True)
class __CLASS__Recon:
    internal: __UP_CLASS__Source
    external: TableReader
    sink: TableWriter
    alerts: Alerts
    alert_threshold: int = 500

    def run(self, as_of: date) -> list[Break]:
        ours = {r.ref_id: r for r in self.internal.for_date(as_of)}
        theirs = {r.ref_id: r for r in self.external.where("ext___TABLE__", as_of=as_of)}
        breaks = [Break.missing_external(r) for k, r in ours.items() if k not in theirs]
        breaks += [
            Break.amount_mismatch(ours[k], theirs[k])
            for k in ours.keys() & theirs.keys()
            if abs(ours[k].amount - theirs[k].amount) > TOLERANCE
        ]
        breaks += [Break.missing_internal(r) for k, r in theirs.items() if k not in ours]
        self.sink.overwrite("__TABLE__", breaks, partition=as_of)
        if len(breaks) > self.alert_threshold:
            self.alerts.notify("__MOD__", f"{len(breaks)} reconciliation breaks")
        return breaks
''',
    "changes": [
        "Switched money comparison from `float` to `Decimal` (removes rounding false positives)",
        "Replaced direct `load_today` import with the upstream `__UP_CLASS__Source` contract",
        "Parameterised the external query; alerting goes through the platform `Alerts` port",
        "Break output is now partitioned by `as_of`, so re-runs are idempotent",
    ],
    "tests": [
        ("test_decimal_tolerance_edge_cases", "unit"),
        ("test_missing_internal_and_external", "unit"),
        ("test_alert_threshold", "unit"),
        ("test_parity_vs_legacy_breaks[golden_2026-09-30]", "parity"),
        ("test_rerun_is_idempotent", "unit"),
        ("test_no_cross_module_imports", "boundary"),
    ],
}

TEMPLATES["rollup"] = {
    "kind": "Aggregation job",
    "before": '''# ledger_etl/jobs/__PATH__.py  (legacy monolith)
from ledger_etl.common.utils import *
from ledger_etl.common import db
from ledger_etl.jobs.__UP__ import TABLE as UPSTREAM_TABLE
import ledger_etl.jobs.marketdata.eod_prices as px

def run(as_of=None):
    as_of = as_of or today_str()
    rows = db.query("SELECT * FROM %s WHERE as_of='%s'" % (UPSTREAM_TABLE, as_of))
    prices = px.PRICE_CACHE      # populated as a side effect of an earlier job
    agg = {}
    for r in rows:
        key = (r["account_id"], r["__KEY__"])
        p = prices.get(r["security_id"], 0)      # missing price -> silently 0
        a = agg.setdefault(key, {"qty": 0, "mv": 0.0})
        a["qty"] += r["quantity"]
        a["mv"] += r["quantity"] * p
    out = [dict(account_id=k[0], __KEY__=k[1], **v) for k, v in agg.items()]
    db.write("__TABLE__", out, mode="overwrite")
    return out
''',
    "after": '''# submodules/__PKG__/src/__PKG__/rollup.py
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ledger_contracts.__UP_PKG__ import __UP_CLASS__Source
from ledger_contracts.marketdata import PriceSource
from ledger_platform.io import TableWriter
from .schema import __CLASS__Row, MissingPrice

@dataclass(frozen=True)
class __CLASS__Rollup:
    upstream: __UP_CLASS__Source
    prices: PriceSource
    sink: TableWriter

    def run(self, as_of: date) -> list[__CLASS__Row]:
        qty: dict[tuple, Decimal] = defaultdict(Decimal)
        mv: dict[tuple, Decimal] = defaultdict(Decimal)
        price_book = self.prices.close_for(as_of)
        for r in self.upstream.for_date(as_of):
            if r.security_id not in price_book:
                raise MissingPrice(r.security_id, as_of)
            key = (r.account_id, r.__KEY__)
            qty[key] += r.quantity
            mv[key] += r.quantity * price_book[r.security_id]
        out = [__CLASS__Row(account_id=a, __KEY__=g, qty=qty[(a, g)], mv=mv[(a, g)])
               for (a, g) in sorted(qty)]
        self.sink.overwrite("__TABLE__", out, partition=as_of)
        return out
''',
    "changes": [
        "Prices come from an explicit `PriceSource` contract, not a cache filled by job ordering",
        "Missing prices now fail loudly (`MissingPrice`) instead of valuing positions at 0",
        "Market value uses `Decimal`; output is sorted and partitioned for deterministic diffs",
        "Upstream rows read through `__UP_CLASS__Source` rather than a shared table name constant",
    ],
    "tests": [
        ("test_rollup_sums_by_account_and_key", "unit"),
        ("test_missing_price_raises", "unit"),
        ("test_decimal_market_value", "unit"),
        ("test_parity_vs_legacy_output[golden_2026-09-30]", "parity"),
        ("test_output_sorted_and_partitioned", "unit"),
        ("test_no_cross_module_imports", "boundary"),
    ],
}

TEMPLATES["calc"] = {
    "kind": "Calculation engine",
    "before": '''# ledger_etl/jobs/__PATH__.py  (legacy monolith)
from ledger_etl.common.utils import *
from ledger_etl.common import db, config
from ledger_etl.jobs.__UP__ import get_rows

CONFIG = config.load_global()

def compute(as_of=None):
    as_of = as_of or today_str()
    rows = get_rows(as_of)
    method = CONFIG.get("__ENTITY___method", "FIFO")
    results = []
    for acct, lots in group_by(rows, "account_id").items():
        lots = sorted(lots, key=lambda l: l["acquired"])
        if method == "LIFO":
            lots.reverse()
        total = 0.0
        for l in lots:
            total = total + round(l["qty"] * l["unit_cost"], 2)
        results.append({"account_id": acct, "value": total, "method": method})
    db.write("__TABLE__", results, mode="overwrite")
    return results
''',
    "after": '''# submodules/__PKG__/src/__PKG__/engine.py
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal
from enum import Enum
from itertools import groupby

from ledger_contracts.__UP_PKG__ import __UP_CLASS__Source
from ledger_platform.io import TableWriter
from .schema import __CLASS__Result

CENT = Decimal("0.01")

class LotMethod(str, Enum):
    FIFO = "FIFO"
    LIFO = "LIFO"

@dataclass(frozen=True)
class __CLASS__Engine:
    upstream: __UP_CLASS__Source
    sink: TableWriter
    method: LotMethod = LotMethod.FIFO

    def compute(self, as_of: date) -> list[__CLASS__Result]:
        rows = sorted(self.upstream.for_date(as_of), key=lambda l: (l.account_id, l.acquired))
        results = []
        for acct, lots in groupby(rows, key=lambda l: l.account_id):
            ordered = list(lots)
            if self.method is LotMethod.LIFO:
                ordered.reverse()
            total = sum(((l.qty * l.unit_cost).quantize(CENT, ROUND_HALF_EVEN)
                         for l in ordered), Decimal(0))
            results.append(__CLASS__Result(account_id=acct, value=total, method=self.method))
        self.sink.overwrite("__TABLE__", results, partition=as_of)
        return results
''',
    "changes": [
        "Lot method is an explicit `LotMethod` parameter instead of a global config lookup",
        "Per-lot rounding uses `Decimal` with banker's rounding to match the ledger of record",
        "Removed the hidden dependency on `ledger_etl.common.utils.group_by`",
        "Upstream rows read via the `__UP_CLASS__Source` contract",
    ],
    "tests": [
        ("test_fifo_matches_legacy[golden_2026-09-30]", "parity"),
        ("test_lifo_matches_legacy[golden_2026-09-30]", "parity"),
        ("test_rounding_half_even_per_lot", "unit"),
        ("test_empty_account_has_no_result", "unit"),
        ("test_property_total_is_order_independent_for_fifo", "property"),
        ("test_no_cross_module_imports", "boundary"),
    ],
}

TEMPLATES["export"] = {
    "kind": "Extract / statement export",
    "before": '''# ledger_etl/jobs/__PATH__.py  (legacy monolith)
from ledger_etl.common.utils import *
from ledger_etl.common import db, config
from ledger_etl.jobs.__UP__ import *          # wildcard import of another job
import os

def run(as_of=None):
    as_of = as_of or today_str()
    rows = db.query("SELECT * FROM __UP_TABLE__ WHERE period='%s'" % period_of(as_of))
    out_dir = config.load_global()["exports"]["root"] + "/__ENTITY__/" + as_of
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    f = open(out_dir + "/part-0000.psv", "w")
    for a in rows:
        line = "|".join([a["account_id"], a["tax_id"], str(a["total"])])  # raw tax id
        f.write(line + "\\n")
    f.close()
    db.execute("INSERT INTO export_log VALUES ('__MOD__', '%s')" % as_of)
''',
    "after": '''# submodules/__PKG__/src/__PKG__/export.py
from dataclasses import dataclass
from datetime import date

from ledger_contracts.__UP_PKG__ import __UP_CLASS__Source
from ledger_platform.io import ExportSink, ExportLog
from ledger_platform.security import TokenVault
from ledger_platform.time import period_of
from .schema import __CLASS__Line

@dataclass(frozen=True)
class __CLASS__Export:
    upstream: __UP_CLASS__Source
    vault: TokenVault
    sink: ExportSink
    audit: ExportLog

    def run(self, as_of: date) -> int:
        lines = [
            __CLASS__Line(account_id=r.account_id,
                          tax_id_token=self.vault.tokenize(r.tax_id),
                          total=r.total)
            for r in self.upstream.for_period(period_of(as_of))
        ]
        with self.sink.atomic("__ENTITY__", as_of) as out:   # temp file + rename
            out.write_psv(lines)
        self.audit.record("__MOD__", as_of, count=len(lines))
        return len(lines)
''',
    "changes": [
        "Removed the wildcard import; upstream data read via `__UP_CLASS__Source`",
        "Tax IDs are tokenized through `TokenVault` instead of written in plain text",
        "Atomic write (temp file + rename) so downstream readers never see partial files",
        "Parameterised audit logging through `ExportLog`",
    ],
    "tests": [
        ("test_psv_layout_matches_legacy", "contract"),
        ("test_tax_id_never_written_in_clear", "unit"),
        ("test_atomic_write_on_failure_leaves_no_file", "unit"),
        ("test_parity_vs_legacy_export[golden_2026-09-30]", "parity"),
        ("test_audit_record_written_once", "unit"),
        ("test_no_cross_module_imports", "boundary"),
    ],
}

TEST_CODE = '''# submodules/__PKG__/tests/test_parity.py
import pytest
from ledger_testkit import golden, fakes
from __PKG__ import __ENTRY__

@pytest.mark.parametrize("snapshot", golden.snapshots("__MOD__"))
def test_parity_vs_legacy(snapshot):
    """New sub-module output must equal the legacy job's output row for row."""
    job = __ENTRY__(**fakes.ports_from(snapshot))
    new = job.__RUN__(snapshot.as_of)
    assert golden.normalize(new) == golden.normalize(snapshot.legacy_output)

def test_no_cross_module_imports():
    assert golden.imports_of("__PKG__").isdisjoint(golden.MONOLITH_PRIVATE)
'''

ENTRY_SUFFIX = {"refdata": ("Snapshot{c}Lookup", "load"), "ingest": ("{c}Ingest", "run"),
                "recon": ("{c}Recon", "run"), "rollup": ("{c}Rollup", "run"),
                "calc": ("{c}Engine", "compute"), "export": ("{c}Export", "run")}

KEYS = {"refdata": "id", "rollup": "group_key"}


def camel(s):
    return "".join(p.capitalize() for p in s.replace(".", "_").split("_"))


def render(text, ctx):
    for k in sorted(ctx, key=len, reverse=True):
        text = text.replace(k, str(ctx[k]))
    return text


def risk_score(m, max_loc, max_fanin):
    size = m["loc"] / max_loc
    cov = 1 - m["test_coverage"] / 100
    fanin = m["fan_in"] / max_fanin if max_fanin else 0
    cx = (m["avg_complexity"] - 3) / 15
    coupling = min(1, m["private_reach_ins"] / 40)
    sensitive = 1 if m["touches_sensitive_data"] else 0
    factors = {
        "Size": (0.20, size, f'{m["loc"]:,} lines'),
        "Low test coverage": (0.22, cov, f'{m["test_coverage"]}% covered'),
        "Fan-in": (0.18, fanin, f'{m["fan_in"]} downstream modules, {m["call_sites"]} call sites'),
        "Complexity": (0.12, max(0, min(1, cx)), f'avg cyclomatic {m["avg_complexity"]}'),
        "Private reach-ins": (0.16, coupling, f'{m["private_reach_ins"]} imports of private state'),
        "Sensitive data": (0.12, sensitive, "handles synthetic tax-ID fields" if sensitive else "no sensitive fields"),
    }
    score = sum(w * v for w, v, _ in factors.values()) * 100
    drivers = sorted(
        [{"factor": k, "weight": w, "value": round(v, 3), "contribution": round(w * v * 100, 1), "detail": d}
         for k, (w, v, d) in factors.items()],
        key=lambda d: -d["contribution"])
    return round(min(99, score * 1.35)), drivers


def band(score):
    return "Critical" if score >= 68 else "High" if score >= 52 else "Medium" if score >= 35 else "Low"


def main():
    rng = random.Random(SEED)
    ids = [m[0] for m in MODULES]
    downstream = {i: [] for i in ids}
    for child, ups in DEPS.items():
        for u in ups:
            downstream[u].append(child)

    mods = []
    for (mid, domain, arch, layer, entity, table) in MODULES:
        ups = DEPS.get(mid, [])
        up = ups[0] if ups else "refdata.business_calendar"
        up_id_short = up.split(".")[1]
        up_table = next(t for (i, _, _, _, _, t) in MODULES if i == up)
        fan_in = len(downstream[mid])
        base_loc = {"refdata": 30000, "ingest": 45000, "recon": 55000, "rollup": 60000,
                    "calc": 85000, "export": 50000}[arch]
        loc = int(base_loc * rng.uniform(0.45, 1.9) + fan_in * 6000) // 10 * 10
        if mid in ("brokerage.cost_basis", "brokerage.positions_daily", "refdata.security_master"):
            loc = int(loc * 1.6) // 10 * 10
        coverage = max(9, min(81, int(rng.gauss(46, 17))))
        if arch == "refdata":
            coverage = min(81, coverage + 12)
        complexity = round(rng.uniform(4, 9) + (6 if arch == "calc" else 0) + layer * 0.6, 1)
        call_sites = fan_in * rng.randint(9, 26) + rng.randint(2, 14)
        if arch == "refdata":
            call_sites += rng.randint(30, 70)
        reach_ins = rng.randint(2, 12) + fan_in * 3 + (12 if arch == "refdata" else 0)
        sensitive = domain == "Tax & Statements" or mid in (
            "refdata.account_master", "retirement.payroll_contrib_ingest", "compliance.reg_reporting_extract",
            "wealth.household_rollup")
        m = {
            "id": mid,
            "domain": domain,
            "archetype": arch,
            "kind": TEMPLATES[arch]["kind"],
            "layer": layer,
            "owner": TEAMS[(ids.index(mid) * 3) % len(TEAMS)],
            "language": "Python 3 (legacy, Python 2 era idioms)",
            "loc": loc,
            "files": max(12, loc // rng.randint(380, 620)),
            "test_coverage": coverage,
            "avg_complexity": complexity,
            "fan_in": fan_in,
            "call_sites": call_sites,
            "private_reach_ins": reach_ins,
            "touches_sensitive_data": sensitive,
            "years_since_rewrite": rng.randint(3, 9),
            "upstream": ups,
            "downstream": sorted(downstream[mid]),
            "table": table,
            "submodule": "ledger-" + mid.replace(".", "-").replace("_", "-"),
        }
        pkg = mid.replace(".", "_")
        cls = camel(entity)
        up_entity = next(e for (i, _, _, _, e, _) in MODULES if i == up)
        ctx = {
            "__MOD__": mid, "__PATH__": mid.replace(".", "/"), "__PKG__": pkg, "__CLASS__": cls,
            "__TABLE__": table, "__ENTITY__": entity, "__UP__": up, "__UP_PKG__": up.split(".")[0],
            "__UP_CLASS__": camel(up_entity), "__UP_TABLE__": up_table, "__KEY__": KEYS.get(arch, "id"),
            "__FEED__": entity + "_feed", "__UPPER__": entity.upper(), "__CALLERS__": call_sites,
        }
        if arch == "rollup":
            ctx["__KEY__"] = {"position": "security_id", "plan_balance": "fund_id", "fund_flow": "share_class",
                              "household": "household_id", "advisor_book": "advisor_id",
                              "normalized_price": "currency"}.get(entity, "group_key")
        if arch == "refdata":
            ctx["__KEY__"] = {"security": "cusip", "account": "account_id", "calendar_day": "cal_date",
                              "fund": "fund_id", "share_class": "share_class_id"}.get(entity, "id")
        t = TEMPLATES[arch]
        entry, run = ENTRY_SUFFIX[arch]
        m["code_before"] = render(t["before"], ctx)
        m["code_after"] = render(t["after"], ctx)
        m["changes"] = [render(c, ctx) for c in t["changes"]]
        m["test_code"] = render(TEST_CODE.replace("__ENTRY__", entry.format(c=cls)).replace("__RUN__", run), ctx)
        rows = rng.randint(180_000, 4_800_000)
        m["tests"] = [{"name": n, "type": ty, "ms": rng.randint(40, 900) if ty != "parity" else rng.randint(2500, 19000),
                       "rows_compared": rows if ty == "parity" else None} for n, ty in t["tests"]]
        mods.append(m)

    max_loc = max(m["loc"] for m in mods)
    max_fanin = max(m["fan_in"] for m in mods)
    for m in mods:
        m["risk_score"], m["risk_drivers"] = risk_score(m, max_loc, max_fanin)
        m["risk_band"] = band(m["risk_score"])
        m["devin_hours"] = round(1.2 + m["loc"] / 22000 + m["risk_score"] / 30, 1)
        m["manual_hours"] = round(m["devin_hours"] * rng.uniform(8.5, 12.5) + m["call_sites"] * 0.4)
        m["review_hours"] = round(0.5 + m["risk_score"] / 40, 1)
        # Engineer time with Devin (scoping, reviewing, fixing up), in the 8-12x band of the public story.
        m["engineer_hours"] = round(m["manual_hours"] / rng.uniform(8, 12), 1)

    seed = {
        "meta": {
            "seed": SEED,
            "generated_by": "scripts/seed.py",
            "label": "Unofficial demo built with Devin - synthetic data",
            "prepared_for": "Fidelity Investments (unofficial, not affiliated or endorsed)",
            "monolith": "ledger-etl",
            "monolith_age_years": 9,
            "total_loc": sum(m["loc"] for m in mods),
            "total_modules": len(mods),
            "golden_snapshots": ["2026-09-30", "2026-10-31"],
            "proof_point": {
                "customer": "Nubank",
                "text": "Nubank used Devin to migrate an 8-year-old, multi-million-line ETL monolith to sub-modules, reporting an 8-12x engineering-time efficiency gain and 20x cost savings.",
                "source": "https://devin.ai/customers/nubank",
            },
        },
        "modules": mods,
    }
    (ROOT / "data").mkdir(exist_ok=True)
    js = json.dumps(seed, indent=1, sort_keys=False)
    (ROOT / "data" / "seed.json").write_text(js + "\n")
    (ROOT / "data" / "seed.js").write_text("// Generated by scripts/seed.py - do not edit.\nwindow.SEED = " + js + ";\n")
    bands = {}
    for m in mods:
        bands[m["risk_band"]] = bands.get(m["risk_band"], 0) + 1
    print(f"wrote {len(mods)} modules, {seed['meta']['total_loc']:,} LOC, bands={bands}")


if __name__ == "__main__":
    main()
