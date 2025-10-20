/**
 * TypeScript types for Insurance API Mapping Configurations
 */

export interface ParamMapping {
  v2_param: string;
  v1_param: string;
  location: "path" | "query" | "body";
}

export interface V1ApiCall {
  name: string;
  endpoint: string;
  method: string;
  params?: {
    path?: ParamMapping[];
    query?: ParamMapping[];
    body?: ParamMapping[];
  };
}

export interface FieldMapping {
  v2_path: string;
  source: string;
  v1_path?: string;
  transform?: string;
  stub_value?: any;
  stub_type?: string;
  // UI state
  approved?: boolean;
  edited?: boolean;
}

export interface AmbiguousMapping {
  v2_field: string;
  proposals: Array<{
    v1_field: string;
    confidence: number;
  }>;
}

export interface MappingMetadata {
  generated_at: string;
  confidence_score: number;
  ambiguous_mappings?: AmbiguousMapping[];
}

export interface EndpointConfig {
  v2_path: string;
  v2_method: string;
}

export interface MappingConfig {
  version: string;
  endpoint: EndpointConfig;
  v1_calls: V1ApiCall[];
  field_mappings: FieldMapping[];
  metadata?: MappingMetadata;
}

// UI-specific types
export interface ConfigSummary {
  id: string;
  endpoint: EndpointConfig;
  confidence_score?: number;
  field_count: number;
  v1_call_count: number;
  has_ambiguous_mappings: boolean;
  generated_at?: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

// Form and validation types
export interface ValidationError {
  field: string;
  message: string;
}

export interface MappingValidation {
  isValid: boolean;
  errors: ValidationError[];
  warnings: string[];
}