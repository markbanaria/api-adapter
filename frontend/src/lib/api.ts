/**
 * API client for Insurance API Adapter backend
 */

import { MappingConfig, ConfigSummary, ApiResponse } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchWithErrorHandling<T>(url: string, options?: RequestInit): Promise<T> {
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new ApiError(response.status, errorText || response.statusText);
    }

    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }

    return response.text() as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(0, `Network error: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Get list of all available mapping configurations
 */
export async function getConfigs(): Promise<ConfigSummary[]> {
  const response = await fetchWithErrorHandling<ApiResponse<ConfigSummary[]>>(`${API_BASE}/configs`);

  if (!response.success || !response.data) {
    throw new Error(response.error || 'Failed to fetch configurations');
  }

  return response.data;
}

/**
 * Get a specific mapping configuration by ID
 */
export async function getConfig(id: string): Promise<MappingConfig> {
  const response = await fetchWithErrorHandling<ApiResponse<MappingConfig>>(`${API_BASE}/configs/${encodeURIComponent(id)}`);

  if (!response.success || !response.data) {
    throw new Error(response.error || 'Failed to fetch configuration');
  }

  return response.data;
}

/**
 * Update a mapping configuration
 */
export async function updateConfig(id: string, config: MappingConfig): Promise<void> {
  const response = await fetchWithErrorHandling<ApiResponse<void>>(`${API_BASE}/configs/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(config),
  });

  if (!response.success) {
    throw new Error(response.error || 'Failed to update configuration');
  }
}

/**
 * Delete a mapping configuration
 */
export async function deleteConfig(id: string): Promise<void> {
  const response = await fetchWithErrorHandling<ApiResponse<void>>(`${API_BASE}/configs/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });

  if (!response.success) {
    throw new Error(response.error || 'Failed to delete configuration');
  }
}

/**
 * Export configuration as YAML
 */
export async function exportConfigAsYaml(id: string): Promise<string> {
  return await fetchWithErrorHandling<string>(`${API_BASE}/configs/${encodeURIComponent(id)}/export`);
}

/**
 * Download YAML configuration file
 */
export function downloadYaml(yamlContent: string, filename: string): void {
  const blob = new Blob([yamlContent], { type: 'text/yaml;charset=utf-8' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = filename.endsWith('.yaml') ? filename : `${filename}.yaml`;
  document.body.appendChild(link);
  link.click();

  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Convert MappingConfig to YAML string (client-side fallback)
 */
export function configToYaml(config: MappingConfig): string {
  // Simple YAML serialization - in production you might want to use js-yaml library
  const indent = (level: number) => '  '.repeat(level);

  let yaml = `version: "${config.version}"\n`;
  yaml += `endpoint:\n`;
  yaml += `${indent(1)}v2_path: "${config.endpoint.v2_path}"\n`;
  yaml += `${indent(1)}v2_method: "${config.endpoint.v2_method}"\n\n`;

  yaml += `v1_calls:\n`;
  config.v1_calls.forEach(call => {
    yaml += `${indent(1)}- name: "${call.name}"\n`;
    yaml += `${indent(2)}endpoint: "${call.endpoint}"\n`;
    yaml += `${indent(2)}method: "${call.method}"\n`;

    if (call.params) {
      yaml += `${indent(2)}params:\n`;
      Object.entries(call.params).forEach(([type, mappings]) => {
        if (mappings && mappings.length > 0) {
          yaml += `${indent(3)}${type}:\n`;
          mappings.forEach(param => {
            yaml += `${indent(4)}- v2_param: "${param.v2_param}"\n`;
            yaml += `${indent(5)}v1_param: "${param.v1_param}"\n`;
            yaml += `${indent(5)}location: "${param.location}"\n`;
          });
        }
      });
    }
    yaml += '\n';
  });

  yaml += `field_mappings:\n`;
  config.field_mappings.forEach(mapping => {
    yaml += `${indent(1)}- v2_path: "${mapping.v2_path}"\n`;
    yaml += `${indent(2)}source: "${mapping.source}"\n`;

    if (mapping.v1_path) {
      yaml += `${indent(2)}v1_path: "${mapping.v1_path}"\n`;
    }

    if (mapping.transform) {
      yaml += `${indent(2)}transform: "${mapping.transform}"\n`;
    }

    if (mapping.stub_value !== undefined) {
      yaml += `${indent(2)}stub_value: ${mapping.stub_value === null ? 'null' : JSON.stringify(mapping.stub_value)}\n`;
    }

    if (mapping.stub_type) {
      yaml += `${indent(2)}stub_type: "${mapping.stub_type}"\n`;
    }
  });

  if (config.metadata) {
    yaml += '\nmetadata:\n';
    yaml += `${indent(1)}generated_at: "${config.metadata.generated_at}"\n`;
    yaml += `${indent(1)}confidence_score: ${config.metadata.confidence_score}\n`;

    if (config.metadata.ambiguous_mappings && config.metadata.ambiguous_mappings.length > 0) {
      yaml += `${indent(1)}ambiguous_mappings:\n`;
      config.metadata.ambiguous_mappings.forEach(amb => {
        yaml += `${indent(2)}- v2_field: "${amb.v2_field}"\n`;
        yaml += `${indent(3)}proposals:\n`;
        amb.proposals.forEach(proposal => {
          yaml += `${indent(4)}- v1_field: "${proposal.v1_field}"\n`;
          yaml += `${indent(5)}confidence: ${proposal.confidence}\n`;
        });
      });
    }
  }

  return yaml;
}

/**
 * Check if backend is healthy
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetchWithErrorHandling<{ status: string }>(`${API_BASE}/health`);
    return response.status === 'healthy';
  } catch {
    return false;
  }
}

/**
 * Spec file interfaces
 */
export interface SpecFile {
  id: string;
  name: string;
  path: string;
  version: string;
  type: 'v1' | 'v2';
  title?: string;
  description?: string;
}

export interface EndpointInfo {
  path: string;
  method: string;
  operationId?: string;
  summary?: string;
  description?: string;
  parameters?: any[];
  requestBody?: any;
  responses?: any;
}

export interface SpecDetails {
  id: string;
  name: string;
  path: string;
  version: string;
  type: 'v1' | 'v2';
  title?: string;
  description?: string;
  endpoints: EndpointInfo[];
  content: any;
}

export interface GenerateConfigRequest {
  v2_endpoint_path: string;
  config_name: string;
  v1_spec_content: any;
  v2_spec_content: any;
}

export interface GeneratedConfigResponse {
  success: boolean;
  config?: any;
  confidence_score?: number;
  ambiguous_mappings?: any[];
  error_message?: string;
}

/**
 * Get list of available OpenAPI spec files
 */
export async function getSpecFiles(specType?: 'v1' | 'v2'): Promise<SpecFile[]> {
  const params = specType ? `?spec_type=${specType}` : '';
  return await fetchWithErrorHandling<SpecFile[]>(`${API_BASE}/specs/list${params}`);
}

/**
 * Get detailed information about a spec file including endpoints
 */
export async function getSpecDetails(specId: string): Promise<SpecDetails> {
  return await fetchWithErrorHandling<SpecDetails>(`${API_BASE}/specs/${encodeURIComponent(specId)}/details`);
}

/**
 * Upload a new OpenAPI spec file
 */
export async function uploadSpecFile(file: File, specType: 'v1' | 'v2'): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('spec_type', specType);

  const response = await fetch(`${API_BASE}/specs/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || 'Failed to upload spec file');
  }

  return await response.json();
}

/**
 * Generate configuration using AI
 */
export async function generateConfig(request: GenerateConfigRequest): Promise<GeneratedConfigResponse> {
  return await fetchWithErrorHandling<GeneratedConfigResponse>(`${API_BASE}/generate-config`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Save generated configuration
 */
export async function saveGeneratedConfig(configName: string, config: any): Promise<any> {
  return await fetchWithErrorHandling<any>(`${API_BASE}/save-generated-config/${encodeURIComponent(configName)}`, {
    method: 'POST',
    body: JSON.stringify(config),
  });
}

/**
 * Check Qwen AI status
 */
export async function checkQwenStatus(): Promise<any> {
  return await fetchWithErrorHandling<any>(`${API_BASE}/check-qwen-status`);
}