"""Scope allow-list loader and matcher.

The allow-list YAML (see docs/scope-allowlist.template.yaml) is the
contract between Sirens and counsel. This module is the ONLY place that
reads it; every other enforcement point receives a validated `ScopeAllowlist`.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from schemas.tasking import Posture, Target, TargetKind


class EngagementMeta(BaseModel):
    customer: str
    contract_reference: str | None = None
    starts_at: datetime
    ends_at: datetime
    point_of_contact: dict[str, str] = Field(default_factory=dict)


class ApprovalRecord(BaseModel):
    approver: str
    approved_at: datetime
    reference: str | None = None


class Approvals(BaseModel):
    legal: ApprovalRecord
    customer: ApprovalRecord | None = None


class TargetSet(BaseModel):
    domains: list[str] = Field(default_factory=list)
    ips: list[str] = Field(default_factory=list)
    asns: list[str] = Field(default_factory=list)
    file_hashes: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    malware_families: list[str] = Field(default_factory=list)
    cves: list[str] = Field(default_factory=list)
    campaigns: list[str] = Field(default_factory=list)
    report_urls: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)


class Restrictions(BaseModel):
    domains: list[str] = Field(default_factory=list)
    ips: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    data_classes: list[str] = Field(default_factory=list)


class Collectors(BaseModel):
    enabled: list[str] = Field(default_factory=list)
    disabled: list[str] = Field(default_factory=list)


class ActiveCapabilities(BaseModel):
    honey_tokens: list[str] = Field(default_factory=list)
    honeypots: list[str] = Field(default_factory=list)
    sinkholes: list[str] = Field(default_factory=list)
    decoy_interactions: list[str] = Field(default_factory=list)


class Budget(BaseModel):
    max_cost_usd_per_day: float = 0
    max_cost_usd_per_engagement: float = 0
    max_input_tokens_per_day: int = 0
    max_output_tokens_per_day: int = 0


class Sharing(BaseModel):
    default_tlp: str = "TLP:AMBER"
    external_communities: list[str] = Field(default_factory=list)


class ScopeAllowlist(BaseModel):
    allowlist_id: str
    schema_version: Literal["1.0.0"] = "1.0.0"
    engagement: EngagementMeta
    approvals: Approvals
    posture: Posture = Posture.PASSIVE_PUBLIC
    targets: TargetSet = Field(default_factory=TargetSet)
    restrictions: Restrictions = Field(default_factory=Restrictions)
    collectors: Collectors = Field(default_factory=Collectors)
    active_capabilities: ActiveCapabilities = Field(default_factory=ActiveCapabilities)
    budget: Budget = Field(default_factory=Budget)
    sharing: Sharing = Field(default_factory=Sharing)

    # ---- Matchers ----

    def covers(self, target: Target) -> bool:
        """Is this target enumerated in the allow-list?"""
        bucket = {
            TargetKind.DOMAIN: self.targets.domains,
            TargetKind.IP: self.targets.ips,
            TargetKind.ASN: self.targets.asns,
            TargetKind.FILE_HASH: self.targets.file_hashes,
            TargetKind.ACTOR: self.targets.actors,
            TargetKind.MALWARE_FAMILY: self.targets.malware_families,
            TargetKind.CVE: self.targets.cves,
            TargetKind.CAMPAIGN: self.targets.campaigns,
            TargetKind.REPORT_URL: self.targets.report_urls,
            TargetKind.EMAIL: self.targets.emails,
        }.get(target.kind, [])
        return target.value in bucket

    def forbids(self, target: Target) -> bool:
        """Is this target explicitly restricted?"""
        if target.kind == TargetKind.DOMAIN and target.value in self.restrictions.domains:
            return True
        if target.kind == TargetKind.IP and target.value in self.restrictions.ips:
            return True
        return False

    def allows_collector(self, name: str) -> bool:
        if name in self.collectors.disabled:
            return False
        return name in self.collectors.enabled

    def window_active(self, at: datetime) -> bool:
        return self.engagement.starts_at <= at <= self.engagement.ends_at


def load_allowlist(path: Path | str) -> ScopeAllowlist:
    raw = yaml.safe_load(Path(path).read_text())
    return ScopeAllowlist.model_validate(raw)
