export interface RuleNode {
  rule_id: string;
  rule_text: string;
  operator?: "AND" | "OR";
  rules?: RuleNode[];
}

export interface StructuredPolicy {
  title: string;
  insurance_name: string;
  rules: RuleNode;
}

export interface PolicySummary {
  id: number;
  title: string;
  pdf_url: string;
  source_page_url: string;
  discovered_at: string;
  has_structured_data: boolean;
  download_status: number | null;
}

export interface PolicyDetail {
  id: number;
  title: string;
  pdf_url: string;
  source_page_url: string;
  discovered_at: string;
  download_status: number | null;
  download_error: string | null;
  structured_json: StructuredPolicy | null;
  structured_at: string | null;
  llm_model: string | null;
  validation_error: string | null;
}

export interface Stats {
  total_policies: number;
  downloaded: number;
  structured: number;
  failed_structuring: number;
}
