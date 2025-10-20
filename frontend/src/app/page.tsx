'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getConfigs, healthCheck } from '@/lib/api';
import { ConfigSummary } from '@/lib/types';

export default function HomePage() {
  const [configs, setConfigs] = useState<ConfigSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        // Check backend health first
        const healthy = await healthCheck();
        setBackendHealthy(healthy);

        if (healthy) {
          const configList = await getConfigs();
          setConfigs(configList);
        } else {
          setError('Backend API is not available');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load configurations');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <div className="text-lg text-gray-600">Loading configurations...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md">
          <div className="text-red-600 text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Connection Error</h1>
          <p className="text-gray-600 mb-4">{error}</p>
          {backendHealthy === false && (
            <div className="text-sm text-gray-500 bg-gray-100 p-3 rounded">
              Make sure the backend API is running on{' '}
              <code className="text-blue-600">http://localhost:8000</code>
            </div>
          )}
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                API Mapping Configurations
              </h1>
              <p className="text-gray-600 mt-2">
                Review and approve AI-generated V1→V2 API mappings
              </p>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${backendHealthy ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className="text-sm text-gray-600">
                  Backend {backendHealthy ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              <Link
                href="/create"
                className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors flex items-center"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                Create New Config
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {configs.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-400 text-6xl mb-4">📋</div>
            <h3 className="text-xl font-medium text-gray-900 mb-2">
              No configurations found
            </h3>
            <p className="text-gray-600 mb-6">
              Generate some mapping configurations using the Qwen config generator first.
            </p>
            <div className="text-sm text-gray-500 bg-gray-100 p-4 rounded-lg max-w-md mx-auto">
              <p className="font-medium mb-2">To generate configs:</p>
              <code className="block text-xs">
                cd config-generator<br />
                python3 simple_test.py
              </code>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Stats Bar */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
                <div className="flex items-center">
                  <div className="p-3 rounded-lg bg-blue-100">
                    <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Total Configs</p>
                    <p className="text-2xl font-bold text-gray-900">{configs.length}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
                <div className="flex items-center">
                  <div className="p-3 rounded-lg bg-green-100">
                    <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">High Confidence</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {configs.filter(c => (c.confidence_score || 0) >= 0.9).length}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
                <div className="flex items-center">
                  <div className="p-3 rounded-lg bg-yellow-100">
                    <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">With Ambiguities</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {configs.filter(c => c.has_ambiguous_mappings).length}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
                <div className="flex items-center">
                  <div className="p-3 rounded-lg bg-purple-100">
                    <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Total Mappings</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {configs.reduce((sum, c) => sum + c.field_count, 0)}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Configurations List */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">
                  Mapping Configurations
                </h2>
              </div>
              <div className="divide-y divide-gray-200">
                {configs.map((config) => (
                  <Link
                    key={config.id}
                    href={`/mapping/${encodeURIComponent(config.id)}`}
                    className="block p-6 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <h3 className="text-lg font-medium text-gray-900">
                            {config.endpoint.v2_method} {config.endpoint.v2_path}
                          </h3>
                          {config.confidence_score && (
                            <div className="flex items-center gap-1">
                              <div className={`w-2 h-2 rounded-full ${
                                config.confidence_score >= 0.9 ? 'bg-green-500' :
                                config.confidence_score >= 0.7 ? 'bg-yellow-500' : 'bg-red-500'
                              }`}></div>
                              <span className="text-sm text-gray-500">
                                {Math.round(config.confidence_score * 100)}%
                              </span>
                            </div>
                          )}
                        </div>

                        <div className="mt-2 flex items-center gap-4 text-sm text-gray-500">
                          <span>{config.field_count} field mappings</span>
                          <span>{config.v1_call_count} V1 API calls</span>
                          {config.generated_at && (
                            <span>Generated {new Date(config.generated_at).toLocaleDateString()}</span>
                          )}
                        </div>

                        {config.has_ambiguous_mappings && (
                          <div className="mt-2">
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                              <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                              </svg>
                              Needs Review
                            </span>
                          </div>
                        )}
                      </div>

                      <div className="flex items-center">
                        <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}