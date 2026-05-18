from pydantic import BaseModel, field_validator
from typing import Optional


class RuleNode(BaseModel):
    rule_id: str
    rule_text: str
    operator: Optional[str] = None
    rules: Optional[list["RuleNode"]] = None

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v):
        if v is not None and v not in ("AND", "OR"):
            raise ValueError(f"operator must be 'AND' or 'OR', got '{v}'")
        return v


class StructuredPolicy(BaseModel):
    title: str
    insurance_name: str
    rules: RuleNode
