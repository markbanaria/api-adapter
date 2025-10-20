# User Story 009: Mapping Viewer UI (Next.js)

## Story
As a developer, I want a web UI to review AI-generated mappings with side-by-side comparisons, confidence scores, and the ability to approve/reject/edit mappings before deployment.

## Acceptance Criteria
- [ ] Homepage lists all generated mapping configs
- [ ] Detail page shows V2 endpoint → V1 sources mapping
- [ ] Side-by-side view of V2 fields and V1 sources
- [ ] Confidence score visualization
- [ ] Ambiguous mappings highlighted with proposals
- [ ] Ability to edit transform expressions
- [ ] Ability to approve/reject individual mappings
- [ ] Export approved config as YAML
- [ ] Responsive design

## Technical Details

### Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                 # Homepage - list of configs
│   │   └── mapping/
│   │       └── [id]/
│   │           └── page.tsx         # Detail page - mapping viewer
│   ├── components/
│   │   ├── ConfigList.tsx
│   │   ├── MappingTable.tsx
│   │   ├── ConfidenceScore.tsx
│   │   ├── AmbiguousMapping.tsx
│   │   └── TransformEditor.tsx
│   └── lib/
│       ├── api.ts                   # API calls to backend
│       └── types.ts                 # TypeScript types
└── public/
```

### Types (frontend/src/lib/types.ts)

```typescript
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

export interface MappingConfig {
  version: string;
  endpoint: {
    v2_path: string;
    v2_method: string;
  };
  v1_calls: V1ApiCall[];
  field_mappings: FieldMapping[];
  metadata?: {
    generated_at: string;
    confidence_score: number;
    ambiguous_mappings?: AmbiguousMapping[];
  };
}
```

### API Client (frontend/src/lib/api.ts)

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

export async function getConfigs(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/configs`);
  if (!res.ok) throw new Error('Failed to fetch configs');
  return res.json();
}

export async function getConfig(id: string): Promise<MappingConfig> {
  const res = await fetch(`${API_BASE}/configs/${id}`);
  if (!res.ok) throw new Error('Failed to fetch config');
  return res.json();
}

export async function updateConfig(id: string, config: MappingConfig): Promise<void> {
  const res = await fetch(`${API_BASE}/configs/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error('Failed to update config');
}

export function downloadYaml(config: MappingConfig, filename: string) {
  const yaml = convertToYaml(config);
  const blob = new Blob([yaml], { type: 'text/yaml' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function convertToYaml(config: MappingConfig): string {
  // Simple YAML serialization (could use js-yaml library)
  return JSON.stringify(config, null, 2); // TODO: proper YAML
}
```

### Homepage (frontend/src/app/page.tsx)

```typescript
'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getConfigs } from '@/lib/api';

export default function HomePage() {
  const [configs, setConfigs] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getConfigs()
      .then(setConfigs)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading configurations...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            API Mapping Configurations
          </h1>
          <p className="text-gray-600 mt-2">
            Review and approve AI-generated V1→V2 API mappings
          </p>
        </header>

        <div className="bg-white rounded-lg shadow">
          {configs.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No configurations found. Generate some configs first.
            </div>
          ) : (
            <ul className="divide-y divide-gray-200">
              {configs.map((configId) => (
                <li key={configId}>
                  <Link
                    href={`/mapping/${configId}`}
                    className="block p-6 hover:bg-gray-50 transition"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-lg font-medium text-gray-900">
                          {configId}
                        </h3>
                        <p className="text-sm text-gray-500 mt-1">
                          Click to review mapping
                        </p>
                      </div>
                      <svg
                        className="w-5 h-5 text-gray-400"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 5l7 7-7 7"
                        />
                      </svg>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
```

### Mapping Detail Page (frontend/src/app/mapping/[id]/page.tsx)

```typescript
'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { getConfig, updateConfig, downloadYaml } from '@/lib/api';
import { MappingConfig } from '@/lib/types';
import MappingTable from '@/components/MappingTable';
import ConfidenceScore from '@/components/ConfidenceScore';
import AmbiguousMappings from '@/components/AmbiguousMappings';

export default function MappingDetailPage() {
  const params = useParams();
  const configId = params.id as string;

  const [config, setConfig] = useState<MappingConfig | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getConfig(configId)
      .then(setConfig)
      .finally(() => setLoading(false));
  }, [configId]);

  const handleSave = async () => {
    if (!config) return;
    await updateConfig(configId, config);
    alert('Configuration saved!');
  };

  const handleExport = () => {
    if (!config) return;
    downloadYaml(config, `${configId}.yaml`);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading configuration...</div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg text-red-600">Configuration not found</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                {config.endpoint.v2_method} {config.endpoint.v2_path}
              </h1>
              <p className="text-gray-600 mt-2">
                Generated: {new Date(config.metadata?.generated_at || '').toLocaleString()}
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleSave}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Save Changes
              </button>
              <button
                onClick={handleExport}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                Export YAML
              </button>
            </div>
          </div>

          {/* Confidence Score */}
          {config.metadata && (
            <div className="mt-4">
              <ConfidenceScore score={config.metadata.confidence_score} />
            </div>
          )}
        </div>

        {/* V1 API Calls Summary */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">V1 API Calls</h2>
          <div className="space-y-2">
            {config.v1_calls.map((call) => (
              <div key={call.name} className="flex items-center gap-3">
                <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded text-sm font-medium">
                  {call.name}
                </span>
                <span className="text-gray-600">
                  {call.method} {call.endpoint}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Ambiguous Mappings Warning */}
        {config.metadata?.ambiguous_mappings && config.metadata.ambiguous_mappings.length > 0 && (
          <AmbiguousMappings mappings={config.metadata.ambiguous_mappings} />
        )}

        {/* Field Mappings Table */}
        <MappingTable
          fieldMappings={config.field_mappings}
          v1Calls={config.v1_calls}
          onChange={(updated) => setConfig({ ...config, field_mappings: updated })}
        />
      </div>
    </div>
  );
}
```

### Mapping Table Component (frontend/src/components/MappingTable.tsx)

```typescript
import { useState } from 'react';
import { FieldMapping, V1ApiCall } from '@/lib/types';

interface Props {
  fieldMappings: FieldMapping[];
  v1Calls: V1ApiCall[];
  onChange: (mappings: FieldMapping[]) => void;
}

export default function MappingTable({ fieldMappings, v1Calls, onChange }: Props) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  const toggleApproval = (index: number) => {
    const updated = [...fieldMappings];
    updated[index].approved = !updated[index].approved;
    onChange(updated);
  };

  const updateTransform = (index: number, transform: string) => {
    const updated = [...fieldMappings];
    updated[index].transform = transform;
    updated[index].edited = true;
    onChange(updated);
    setEditingIndex(null);
  };

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              V2 Field
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Source
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              V1 Field / Transform
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {fieldMappings.map((mapping, index) => (
            <tr key={index} className={mapping.approved ? 'bg-green-50' : ''}>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                {mapping.v2_path}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                <span className={`px-2 py-1 rounded text-xs ${
                  mapping.source === 'stub' 
                    ? 'bg-yellow-100 text-yellow-800' 
                    : 'bg-blue-100 text-blue-800'
                }`}>
                  {mapping.source}
                </span>
              </td>
              <td className="px-6 py-4 text-sm text-gray-500">
                {editingIndex === index ? (
                  <input
                    type="text"
                    className="border rounded px-2 py-1 w-full"
                    defaultValue={mapping.transform || mapping.v1_path || ''}
                    onBlur={(e) => updateTransform(index, e.target.value)}
                    autoFocus
                  />
                ) : (
                  <div className="font-mono text-xs">
                    {mapping.transform || mapping.v1_path || `stub: ${mapping.stub_value}`}
                  </div>
                )}
                {mapping.edited && (
                  <span className="text-xs text-orange-600 ml-2">(edited)</span>
                )}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm">
                {mapping.approved ? (
                  <span className="text-green-600 font-medium">✓ Approved</span>
                ) : (
                  <span className="text-gray-400">Pending</span>
                )}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                <button
                  onClick={() => toggleApproval(index)}
                  className={`px-3 py-1 rounded ${
                    mapping.approved
                      ? 'bg-gray-200 text-gray-700'
                      : 'bg-green-600 text-white'
                  }`}
                >
                  {mapping.approved ? 'Unapprove' : 'Approve'}
                </button>
                <button
                  onClick={() => setEditingIndex(index)}
                  className="px-3 py-1 bg-blue-600 text-white rounded"
                >
                  Edit
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

### Confidence Score Component (frontend/src/components/ConfidenceScore.tsx)

```typescript
interface Props {
  score: number;
}

export default function ConfidenceScore({ score }: Props) {
  const percentage = Math.round(score * 100);
  const color = score >= 0.9 ? 'green' : score >= 0.7 ? 'yellow' : 'red';

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm font-medium text-gray-700">Confidence Score:</span>
      <div className="flex-1 max-w-xs">
        <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full bg-${color}-500`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
      <span className={`text-sm font-bold text-${color}-600`}>
        {percentage}%
      </span>
    </div>
  );
}
```

### Ambiguous Mappings Component (frontend/src/components/AmbiguousMappings.tsx)

```typescript
import { AmbiguousMapping } from '@/lib/types';

interface Props {
  mappings: AmbiguousMapping[];
}

export default function AmbiguousMappings({ mappings }: Props) {
  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
      <div className="flex items-start gap-3">
        <svg
          className="w-6 h-6 text-yellow-600 flex-shrink-0 mt-0.5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-yellow-900 mb-2">
            Ambiguous Mappings Detected
          </h3>
          <p className="text-sm text-yellow-800 mb-4">
            The AI found multiple possible mappings for the following fields. Please review:
          </p>
          <div className="space-y-3">
            {mappings.map((mapping, index) => (
              <div key={index} className="bg-white rounded p-3">
                <div className="font-medium text-gray-900 mb-2">
                  {mapping.v2_field}
                </div>
                <div className="space-y-1">
                  {mapping.proposals.map((proposal, pIndex) => (
                    <div key={pIndex} className="flex items-center gap-2 text-sm">
                      <span className="text-gray-600">{proposal.v1_field}</span>
                      <span className="text-xs text-gray-500">
                        ({Math.round(proposal.confidence * 100)}% confidence)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
```

## Testing Checklist
- [ ] Homepage lists all configs
- [ ] Detail page loads config correctly
- [ ] Mapping table displays all fields
- [ ] Confidence score visualization works
- [ ] Ambiguous mappings highlighted
- [ ] Approve/unapprove toggles work
- [ ] Edit transform expressions works
- [ ] Export YAML downloads file
- [ ] Responsive on mobile/tablet

## Definition of Done
- Next.js app runs on localhost:3000
- All components implemented and styled
- Config list and detail views functional
- Approve/reject/edit functionality works
- YAML export works
- UI is clean and professional
- TypeScript types defined