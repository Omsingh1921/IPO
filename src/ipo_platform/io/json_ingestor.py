"""
JSON Ingestion & Parser Engine for Indian IPO Research Platform.
Parses, normalizes, and validates Schema Version 1.0 JSON reports and raw data files.
"""

import json
from typing import Any, Dict, Union
from ..models.schema import (
    MasterIPORecord,
    IPOEntity,
    IPOStatus,
    IssueStructure,
    ValuationData,
    Scenario40Percent,
    DataQuality,
    ProvenanceEnvelope,
    ObjectOfIssue,
    FinancialRecord,
    SubscriptionCategory,
    AnchorData,
    AnchorInvestor,
    GMPData,
    PeerCompany,
    RiskRecord,
    HistoricalIPO,
    PerformanceEvent,
    SourceRecord,
)
from ..models.enums import (
    SegmentEnum,
    IPOStatusEnum,
    ListingStatusEnum,
    PeriodTypeEnum,
    DataTypeEnum,
    SourceTypeEnum,
    ScenarioStatusEnum,
    InvestorTypeEnum,
    RiskCategoryEnum,
    RiskSeverityEnum,
    PerformanceEventTypeEnum,
    ObjectsDisclosureStatusEnum,
    DataCompletenessEnum,
    SourceVerificationEnum,
)
from ..engine.validators import IPOValidator, SchemaValidationError


class JSONIngestor:
    """Ingests Schema v1.0 JSON payloads into strongly-typed MasterIPORecord structures."""

    @staticmethod
    def _parse_provenance(data: Union[Dict[str, Any], Any]) -> ProvenanceEnvelope:
        if isinstance(data, dict):
            val = data.get("value", "Not available")
            d_type_str = data.get("data_type", "Reported")
            try:
                d_type = DataTypeEnum(d_type_str)
            except ValueError:
                d_type = DataTypeEnum.REPORTED
            return ProvenanceEnvelope(
                value=val,
                unit=data.get("unit"),
                currency=data.get("currency", "INR"),
                data_type=d_type,
                source=data.get("source", "Unspecified"),
                source_date=data.get("source_date"),
                retrieval_timestamp=data.get("retrieval_timestamp"),
            )
        return ProvenanceEnvelope(value=data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MasterIPORecord:
        """Parses a dictionary into a validated MasterIPORecord instance."""
        # 1. Prohibited keys check
        prohibited_violations = IPOValidator.validate_prohibited_keys(data)
        if prohibited_violations:
            raise SchemaValidationError(
                f"Validation failed due to prohibited keys: {'; '.join(prohibited_violations)}"
            )

        # 2. Parse IPOEntity
        ent_data = data["ipo_entity"]
        entity = IPOEntity(
            ipo_id=ent_data["ipo_id"],
            company_name=ent_data["company_name"],
            company_legal_name=ent_data["company_legal_name"],
            ticker_symbol=ent_data.get("ticker_symbol", "Not available"),
            isin=ent_data.get("isin", "Not available"),
            segment=SegmentEnum(ent_data["segment"]),
            sector=ent_data["sector"],
            industry=ent_data["industry"],
        )

        # 3. Parse IPOStatus
        st_data = data["ipo_status"]
        status = IPOStatus(
            status=IPOStatusEnum(st_data["status"]),
            research_date=st_data["research_date"],
            research_time=st_data["research_time"],
            data_cutoff=st_data["data_cutoff"],
            open_date=st_data["open_date"],
            close_date=st_data["close_date"],
            listing_date=st_data.get("listing_date", "Not available"),
            listing_status=ListingStatusEnum(st_data.get("listing_status", "Pre-Listing")),
        )

        # 4. Parse IssueStructure
        iss_data = data["issue_structure"]
        issue_structure = IssueStructure(
            issue_size=cls._parse_provenance(iss_data["issue_size"]),
            fresh_issue_amount=cls._parse_provenance(iss_data["fresh_issue_amount"]),
            ofs_amount=cls._parse_provenance(iss_data["ofs_amount"]),
            fresh_issue_percentage=cls._parse_provenance(iss_data["fresh_issue_percentage"]),
            ofs_percentage=cls._parse_provenance(iss_data["ofs_percentage"]),
            face_value=cls._parse_provenance(iss_data["face_value"]),
            price_band_low=cls._parse_provenance(iss_data["price_band_low"]),
            price_band_high=cls._parse_provenance(iss_data["price_band_high"]),
            issue_price=cls._parse_provenance(iss_data["issue_price"]),
            lot_size=cls._parse_provenance(iss_data["lot_size"]),
            minimum_investment=cls._parse_provenance(iss_data["minimum_investment"]),
        )

        # 5. Parse ValuationData
        val_data = data["valuation_data"]
        valuation_data = ValuationData(
            reference_price=float(val_data["reference_price"]),
            reference_eps=float(val_data["reference_eps"]),
            issue_pe=cls._parse_provenance(val_data["issue_pe"]),
            valuation_method=val_data.get("valuation_method", ""),
            valuation_source=val_data.get("valuation_source", ""),
            valuation_date=val_data.get("valuation_date", ""),
            issue_pb=cls._parse_provenance(val_data["issue_pb"]) if "issue_pb" in val_data else None,
            industry_pe=cls._parse_provenance(val_data["industry_pe"]) if "industry_pe" in val_data else None,
        )

        # 6. Parse Scenario40Percent
        scen_data = data["scenario_40_percent"]
        scenario = Scenario40Percent(
            reference_price=float(scen_data["reference_price"]),
            target_price=float(scen_data["target_price"]),
            required_price_movement=float(scen_data.get("required_price_movement", 40.00)),
            target_pe=float(scen_data["target_pe"]) if scen_data.get("target_pe") else None,
            target_pb=float(scen_data["target_pb"]) if scen_data.get("target_pb") else None,
            supporting_factors=scen_data.get("supporting_factors", []),
            contradictory_factors=scen_data.get("contradictory_factors", []),
            scenario_status=ScenarioStatusEnum(scen_data["scenario_status"]),
            scenario_methodology=scen_data.get("scenario_methodology", ""),
            scenario_data_timestamp=scen_data.get("scenario_data_timestamp", ""),
        )

        # 7. Parse DataQuality
        dq_data = data.get("data_quality", {})
        data_quality = DataQuality(
            completeness_status=DataCompletenessEnum(dq_data.get("completeness_status", "Partial")),
            source_verification_status=SourceVerificationEnum(dq_data.get("source_verification_status", "Verified")),
            last_verified=dq_data.get("last_verified", ""),
            missing_fields=dq_data.get("missing_fields", []),
            conflicting_data=dq_data.get("conflicting_data", []),
            notes=dq_data.get("notes", ""),
        )

        # 8. Objects of issue
        objects_list = []
        for obj in data.get("objects_of_issue", []):
            objects_list.append(
                ObjectOfIssue(
                    purpose=obj["purpose"],
                    amount=float(obj["amount"]),
                    source=obj.get("source", ""),
                    source_date=obj.get("source_date", ""),
                    percentage_of_fresh_issue=obj.get("percentage_of_fresh_issue"),
                    disclosure_status=ObjectsDisclosureStatusEnum(obj.get("disclosure_status", "Disclosed")),
                )
            )

        # 9. Financial data
        fin_list = []
        for fin in data.get("financial_data", []):
            fin_list.append(
                FinancialRecord(
                    financial_period=fin["financial_period"],
                    period_type=PeriodTypeEnum(fin.get("period_type", "FY")),
                    revenue=cls._parse_provenance(fin["revenue"]) if "revenue" in fin else None,
                    revenue_growth=cls._parse_provenance(fin["revenue_growth"]) if "revenue_growth" in fin else None,
                    EBITDA=cls._parse_provenance(fin["EBITDA"]) if "EBITDA" in fin else None,
                    EBITDA_margin=cls._parse_provenance(fin["EBITDA_margin"]) if "EBITDA_margin" in fin else None,
                    PAT=cls._parse_provenance(fin["PAT"]) if "PAT" in fin else None,
                    PAT_growth=cls._parse_provenance(fin["PAT_growth"]) if "PAT_growth" in fin else None,
                    EPS=cls._parse_provenance(fin["EPS"]) if "EPS" in fin else None,
                )
            )

        # Construct MasterIPORecord
        record = MasterIPORecord(
            schema_version=data.get("schema_version", "1.0"),
            ipo_entity=entity,
            ipo_status=status,
            issue_structure=issue_structure,
            valuation_data=valuation_data,
            scenario_40_percent=scenario,
            data_quality=data_quality,
            objects_of_issue=objects_list,
            financial_data=fin_list,
        )

        # Validate complete record
        valid, errors = IPOValidator.validate_record(record)
        if not valid:
            raise SchemaValidationError(f"MasterIPORecord validation failed: {'; '.join(errors)}")

        return record

    @classmethod
    def from_json_string(cls, json_str: str) -> MasterIPORecord:
        """Parses a JSON string into a validated MasterIPORecord instance."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_json_file(cls, filepath: str) -> MasterIPORecord:
        """Loads and parses a JSON file into a validated MasterIPORecord instance."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
