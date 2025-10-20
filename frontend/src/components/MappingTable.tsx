'use client';

import { useState } from 'react';
import { FieldMapping, V1ApiCall } from '@/lib/types';

interface MappingTableProps {
  fieldMappings: FieldMapping[];
  v1Calls: V1ApiCall[];
  onChange: (mappings: FieldMapping[]) => void;
}

export default function MappingTable({ fieldMappings, v1Calls, onChange }: MappingTableProps) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editValue, setEditValue] = useState<string>('');

  const toggleApproval = (index: number) => {
    const updated = [...fieldMappings];
    updated[index].approved = !updated[index].approved;
    onChange(updated);
  };

  const startEdit = (index: number) => {
    const mapping = fieldMappings[index];
    setEditValue(mapping.transform || mapping.v1_path || '');
    setEditingIndex(index);
  };

  const saveEdit = (index: number) => {
    const updated = [...fieldMappings];
    const mapping = updated[index];

    // Determine if it's a transform or v1_path
    if (editValue.includes('{{') && editValue.includes('}}')) {
      mapping.transform = editValue;
      mapping.v1_path = undefined;
    } else {
      mapping.v1_path = editValue;
      mapping.transform = undefined;
    }

    mapping.edited = true;
    onChange(updated);
    setEditingIndex(null);
  };

  const cancelEdit = () => {
    setEditingIndex(null);
    setEditValue('');
  };

  const getSourceBadgeColor = (source: string) => {
    if (source === 'stub') return 'bg-yellow-100 text-yellow-800';
    return 'bg-blue-100 text-blue-800';
  };

  const getApprovalStats = () => {
    const approved = fieldMappings.filter(m => m.approved).length;
    const total = fieldMappings.length;
    return { approved, total, percentage: total > 0 ? Math.round((approved / total) * 100) : 0 };
  };

  const stats = getApprovalStats();

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      {/* Header with stats */}
      <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-medium text-gray-900">
            Field Mappings ({fieldMappings.length})
          </h2>
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-600">
              <span className="font-medium text-green-600">{stats.approved}</span> approved of{' '}
              <span className="font-medium">{stats.total}</span> ({stats.percentage}%)
            </div>
            {stats.approved === stats.total && stats.total > 0 && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                All Approved
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
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
              <tr
                key={index}
                className={`${mapping.approved ? 'bg-green-50' : ''} hover:bg-gray-50 transition-colors`}
              >
                {/* V2 Field */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <span className="text-sm font-medium text-gray-900">
                      {mapping.v2_path}
                    </span>
                    {mapping.edited && (
                      <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                        edited
                      </span>
                    )}
                  </div>
                </td>

                {/* Source */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getSourceBadgeColor(mapping.source)}`}>
                    {mapping.source}
                  </span>
                </td>

                {/* V1 Field / Transform */}
                <td className="px-6 py-4">
                  {editingIndex === index ? (
                    <div className="space-y-2">
                      <textarea
                        className="w-full border border-gray-300 rounded px-3 py-2 text-sm font-mono resize-none"
                        rows={mapping.transform ? 2 : 1}
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        placeholder="Enter field path or Jinja2 transform..."
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => saveEdit(index)}
                          className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700"
                        >
                          Save
                        </button>
                        <button
                          onClick={cancelEdit}
                          className="px-3 py-1 text-xs bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-1">
                      <div className="font-mono text-sm">
                        {mapping.transform && (
                          <div className="text-purple-700 bg-purple-50 px-2 py-1 rounded">
                            {mapping.transform}
                          </div>
                        )}
                        {mapping.v1_path && !mapping.transform && (
                          <div className="text-blue-700">
                            {mapping.v1_path}
                          </div>
                        )}
                        {mapping.source === 'stub' && (
                          <div className="text-yellow-700 bg-yellow-50 px-2 py-1 rounded">
                            stub: {JSON.stringify(mapping.stub_value)} ({mapping.stub_type})
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </td>

                {/* Status */}
                <td className="px-6 py-4 whitespace-nowrap">
                  {mapping.approved ? (
                    <span className="inline-flex items-center text-green-600 font-medium text-sm">
                      <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      Approved
                    </span>
                  ) : (
                    <span className="text-gray-400 text-sm">Pending</span>
                  )}
                </td>

                {/* Actions */}
                <td className="px-6 py-4 whitespace-nowrap">
                  {editingIndex === index ? (
                    <span className="text-xs text-gray-500">Editing...</span>
                  ) : (
                    <div className="flex gap-2">
                      <button
                        onClick={() => toggleApproval(index)}
                        className={`px-3 py-1 text-xs rounded font-medium transition ${
                          mapping.approved
                            ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                            : 'bg-green-600 text-white hover:bg-green-700'
                        }`}
                      >
                        {mapping.approved ? 'Unapprove' : 'Approve'}
                      </button>
                      <button
                        onClick={() => startEdit(index)}
                        className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition"
                      >
                        Edit
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      {fieldMappings.length === 0 && (
        <div className="px-6 py-8 text-center text-gray-500">
          No field mappings defined
        </div>
      )}
    </div>
  );
}