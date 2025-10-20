'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { getConfig, updateConfig, exportConfigAsYaml, downloadYaml, configToYaml } from '@/lib/api';
import { MappingConfig } from '@/lib/types';
import MappingTable from '@/components/MappingTable';
import ConfidenceScore from '@/components/ConfidenceScore';
import AmbiguousMappings from '@/components/AmbiguousMappings';

export default function MappingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const configId = params.id as string;

  // Check if config was just created
  const [justCreated, setJustCreated] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      setJustCreated(urlParams.get('created') === 'true');
    }
  }, []);

  const [config, setConfig] = useState<MappingConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    const loadConfig = async (retries = 0) => {
      try {
        const configData = await getConfig(configId);
        setConfig(configData);
      } catch (err) {
        // If config was just created and this is the first few attempts, retry
        if (justCreated && retries < 3) {
          setTimeout(() => {
            loadConfig(retries + 1);
          }, 1000); // Wait 1 second before retry
          return;
        }

        setError(err instanceof Error ? err.message : 'Failed to load configuration');
      } finally {
        if (!justCreated || retries >= 3) {
          setLoading(false);
        }
      }
    };

    loadConfig();
  }, [configId, justCreated]);

  const handleSave = async () => {
    if (!config || saving) return;

    setSaving(true);
    try {
      await updateConfig(configId, config);
      // Show success message (you could use a toast library here)
      alert('Configuration saved successfully!');
    } catch (err) {
      alert(`Failed to save: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  };

  const handleExport = async () => {
    if (!config || exporting) return;

    setExporting(true);
    try {
      // Try to get YAML from backend first
      try {
        const yamlContent = await exportConfigAsYaml(configId);
        downloadYaml(yamlContent, `${configId}.yaml`);
      } catch {
        // Fallback to client-side conversion
        const yamlContent = configToYaml(config);
        downloadYaml(yamlContent, `${configId}.yaml`);
      }
    } catch (err) {
      alert(`Failed to export: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setExporting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <div className="text-lg text-gray-600">
            {justCreated ? 'Setting up your new configuration...' : 'Loading configuration...'}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md">
          <div className="text-red-600 text-6xl mb-4">❌</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Configuration Not Found</h1>
          <p className="text-gray-600 mb-4">{error}</p>
          <Link
            href="/"
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Home
          </Link>
        </div>
      </div>
    );
  }

  if (!config) {
    return null;
  }

  const approvedMappings = config.field_mappings.filter(m => m.approved).length;
  const totalMappings = config.field_mappings.length;
  const allApproved = approvedMappings === totalMappings && totalMappings > 0;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/"
                className="p-2 text-gray-400 hover:text-gray-600 transition"
                title="Back to configurations"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
              </Link>
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-bold text-gray-900">
                    {config.endpoint.v2_method} {config.endpoint.v2_path}
                  </h1>
                  {allApproved && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      Ready for Deployment
                    </span>
                  )}
                </div>
                <p className="text-gray-600 mt-1">
                  Generated {config.metadata?.generated_at ? new Date(config.metadata.generated_at).toLocaleString() : 'recently'}
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 transition"
              >
                {saving ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Saving...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    Save Changes
                  </>
                )}
              </button>
              <button
                onClick={handleExport}
                disabled={exporting}
                className="flex items-center px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 transition"
              >
                {exporting ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Exporting...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
                    </svg>
                    Export YAML
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Success Banner for Newly Created Config */}
      {justCreated && (
        <div className="bg-green-50 border-l-4 border-green-400 p-4 mx-4 mt-4 rounded">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-green-700">
                <strong>Configuration created successfully!</strong> You can now review and edit the AI-generated mappings below.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8 space-y-6">
        {/* Confidence Score */}
        {config.metadata && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <ConfidenceScore score={config.metadata.confidence_score} size="lg" />
          </div>
        )}

        {/* V1 API Calls Summary */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            V1 API Calls ({config.v1_calls.length})
          </h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {config.v1_calls.map((call) => (
              <div key={call.name} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm font-medium">
                    {call.name}
                  </span>
                  <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                    {call.method}
                  </span>
                </div>
                <div className="text-sm text-gray-600 font-mono bg-gray-50 p-2 rounded">
                  {call.endpoint}
                </div>
                {call.params && (
                  <div className="mt-2 text-xs text-gray-500">
                    {Object.entries(call.params).map(([type, mappings]) =>
                      mappings && mappings.length > 0 && (
                        <div key={type} className="mb-1">
                          <span className="font-medium">{type}:</span> {mappings.length} param{mappings.length !== 1 ? 's' : ''}
                        </div>
                      )
                    )}
                  </div>
                )}
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
      </main>
    </div>
  );
}