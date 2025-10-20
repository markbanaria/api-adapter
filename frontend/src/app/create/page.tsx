'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  getSpecFiles,
  getSpecDetails,
  uploadSpecFile,
  generateConfig as generateConfigAPI,
  saveGeneratedConfig,
  checkQwenStatus as checkQwenStatusAPI,
  getConfigs,
  type SpecFile,
  type SpecDetails,
  type EndpointInfo,
  type GenerateConfigRequest,
  type GeneratedConfigResponse
} from '@/lib/api';

export default function CreateConfigPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [v1Specs, setV1Specs] = useState<SpecFile[]>([]);
  const [v2Specs, setV2Specs] = useState<SpecFile[]>([]);
  const [selectedV1Spec, setSelectedV1Spec] = useState<SpecDetails | null>(null);
  const [selectedV2Spec, setSelectedV2Spec] = useState<SpecDetails | null>(null);
  const [selectedV2Endpoint, setSelectedV2Endpoint] = useState<EndpointInfo | null>(null);
  const [selectedV1Endpoints, setSelectedV1Endpoints] = useState<EndpointInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [configName, setConfigName] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [qwenStatus, setQwenStatus] = useState<any>(null);
  const [existingConfigs, setExistingConfigs] = useState<any[]>([]);

  // Load available specs and check Qwen status on component mount
  useEffect(() => {
    loadSpecFiles();
    checkQwenStatus();
    loadExistingConfigs();
  }, []);

  const loadExistingConfigs = async () => {
    try {
      const configs = await getConfigs();
      if (configs.success) {
        setExistingConfigs(configs.data);
      }
    } catch (error) {
      console.error('Failed to load existing configs:', error);
    }
  };

  // Generate config name from V2 endpoint path
  const generateConfigName = (endpoint: EndpointInfo): string => {
    // Convert "/api/v2/complete-policy/{policyId}" to "api-v2-complete-policy-policyId"
    return endpoint.path
      .replace(/^\//, '') // Remove leading slash
      .replace(/\//g, '-') // Replace slashes with dashes
      .replace(/\{([^}]+)\}/g, '$1') // Remove curly braces from params
      .toLowerCase();
  };

  // Check if config already exists for this endpoint
  const configExists = (endpoint: EndpointInfo): boolean => {
    const configName = generateConfigName(endpoint);
    return existingConfigs.some(config => config.id === configName);
  };

  // Handle V2 endpoint selection
  const handleV2EndpointSelection = (endpoint: EndpointInfo) => {
    setSelectedV2Endpoint(endpoint);
    const newConfigName = generateConfigName(endpoint);
    setConfigName(newConfigName);
  };

  const loadSpecFiles = async () => {
    try {
      const [v1Files, v2Files] = await Promise.all([
        getSpecFiles('v1'),
        getSpecFiles('v2')
      ]);
      setV1Specs(v1Files);
      setV2Specs(v2Files);
    } catch (error) {
      console.error('Failed to load spec files:', error);
    }
  };

  const checkQwenStatus = async () => {
    try {
      const status = await checkQwenStatusAPI();
      setQwenStatus(status);
    } catch (error) {
      console.error('Failed to check Qwen status:', error);
      setQwenStatus({ ollama_available: false, qwen_available: false });
    }
  };

  const handleFileUpload = async (file: File, type: 'v1' | 'v2') => {
    try {
      setLoading(true);
      const result = await uploadSpecFile(file, type);

      // Reload spec files
      await loadSpecFiles();

      // Auto-select the uploaded spec
      if (result.spec_id) {
        const specDetails = await getSpecDetails(result.spec_id);
        if (type === 'v1') {
          setSelectedV1Spec(specDetails);
        } else {
          setSelectedV2Spec(specDetails);
        }
      }
    } catch (error) {
      alert(`Failed to upload OpenAPI specification: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSpecSelection = async (specId: string, type: 'v1' | 'v2') => {
    try {
      setLoading(true);
      const specDetails = await getSpecDetails(specId);

      if (type === 'v1') {
        setSelectedV1Spec(specDetails);
        setSelectedV1Endpoints([]); // Reset selections
      } else {
        setSelectedV2Spec(specDetails);
        setSelectedV2Endpoint(null); // Reset selection
      }
    } catch (error) {
      alert(`Failed to load spec details: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const generateConfig = async () => {
    if (!selectedV2Endpoint || !selectedV1Spec || !selectedV2Spec || !configName) {
      alert('Please complete all steps');
      return;
    }

    setIsGenerating(true);

    try {
      // Generate config using AI
      const request: GenerateConfigRequest = {
        v2_endpoint_path: selectedV2Endpoint.path,
        config_name: configName,
        v1_spec_content: selectedV1Spec.content,
        v2_spec_content: selectedV2Spec.content
      };

      const result = await generateConfigAPI(request);

      if (result.success && result.config) {
        // Save the generated config
        await saveGeneratedConfig(configName, result.config);

        // Redirect to mapping editor with success state
        router.push(`/mapping/${configName}?created=true`);
      } else {
        throw new Error(result.error_message || 'AI generation failed');
      }

    } catch (error: any) {
      console.error('Config generation failed:', error);
      alert(`Failed to generate configuration: ${error.message || error}`);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Implement V2 API Endpoint</h1>
          <p className="text-gray-600 mt-2">
            Choose a V2 endpoint to implement by creating mappings to existing V1 APIs
          </p>
        </div>

        {/* Progress Steps */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            {[
              { num: 1, title: 'Select V2 API', desc: 'Choose target specification' },
              { num: 2, title: 'Select V2 Endpoint', desc: 'Choose target endpoint' },
              { num: 3, title: 'Select V1 Sources', desc: 'Choose source spec & endpoints' },
              { num: 4, title: 'Generate', desc: 'Implement endpoint' }
            ].map((stepInfo) => (
              <div key={stepInfo.num} className="flex items-center">
                <div className={`
                  w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium
                  ${step >= stepInfo.num
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-500'
                  }
                `}>
                  {stepInfo.num}
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-900">{stepInfo.title}</p>
                  <p className="text-sm text-gray-500">{stepInfo.desc}</p>
                </div>
                {stepInfo.num < 4 && (
                  <div className={`flex-1 h-px mx-4 ${
                    step > stepInfo.num ? 'bg-blue-600' : 'bg-gray-200'
                  }`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <div className="bg-white rounded-lg shadow-sm border p-6">

          {/* Step 1: Select V2 API Specification */}
          {step === 1 && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold">Select V2 API Specification</h2>
              <p className="text-gray-600">Choose the target V2 API specification that you want to create mappings for.</p>

              <div className="max-w-2xl mx-auto">
                {selectedV2Spec ? (
                  <div className="bg-green-50 border border-green-200 rounded p-4">
                    <h4 className="font-medium text-green-800">{selectedV2Spec.title || selectedV2Spec.name}</h4>
                    <p className="text-sm text-green-600">Version: {selectedV2Spec.version}</p>
                    <p className="text-sm text-green-600">{selectedV2Spec.endpoints.length} endpoints available</p>
                    <button
                      onClick={() => setSelectedV2Spec(null)}
                      className="mt-2 text-sm text-blue-600 hover:text-blue-700"
                    >
                      Change selection
                    </button>
                  </div>
                ) : (
                  <>
                    {/* Available V2 Specs */}
                    <div className="space-y-2">
                      <h4 className="text-sm font-medium text-gray-700">Available V2 API Specifications:</h4>
                      {v2Specs.length > 0 ? (
                        <div className="space-y-3">
                          {v2Specs.map((spec) => (
                            <div
                              key={spec.id}
                              className="border border-gray-200 rounded-lg p-4 cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition"
                              onClick={() => handleSpecSelection(spec.id, 'v2')}
                            >
                              <div className="font-medium">{spec.title || spec.name}</div>
                              <div className="text-sm text-gray-600 mt-1">{spec.description}</div>
                              <div className="text-xs text-gray-500 mt-2">Version: {spec.version}</div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500">No V2 specs available</p>
                      )}
                    </div>

                    {/* Upload new V2 spec */}
                    <div className="border-t pt-4">
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Or upload a new V2 specification:</h4>
                      <input
                        type="file"
                        accept=".json,.yaml,.yml"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) handleFileUpload(file, 'v2');
                        }}
                        disabled={loading}
                        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
                      />
                    </div>
                  </>
                )}
              </div>

              {loading && (
                <div className="text-center py-4">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                  <p className="text-sm text-gray-600 mt-2">Loading...</p>
                </div>
              )}

              <div className="flex justify-end">
                <button
                  onClick={() => setStep(2)}
                  disabled={!selectedV2Spec || loading}
                  className="bg-blue-600 text-white px-6 py-2 rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  Next: Select V2 Endpoint
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Select V2 Endpoint */}
          {step === 2 && selectedV2Spec && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold">Select V2 Endpoint to Configure</h2>
              <p className="text-gray-600">Choose which endpoint from <strong>{selectedV2Spec.title || selectedV2Spec.name}</strong> you want to create mappings for.</p>

              <div className="space-y-3">
                {selectedV2Spec.endpoints.map((endpoint, index) => (
                  <div
                    key={index}
                    className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                      selectedV2Endpoint === endpoint
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onClick={() => handleV2EndpointSelection(endpoint)}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <span className={`inline-block px-2 py-1 rounded text-xs font-medium mr-3 ${
                          endpoint.method === 'GET' ? 'bg-green-100 text-green-800' :
                          endpoint.method === 'POST' ? 'bg-blue-100 text-blue-800' :
                          endpoint.method === 'PUT' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {endpoint.method}
                        </span>
                        <span className="font-mono text-sm">{endpoint.path}</span>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium">{endpoint.summary}</p>
                        <p className="text-xs text-gray-500">{endpoint.operationId}</p>
                        {configExists(endpoint) && (
                          <div className="mt-1">
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                              ⚠️ Config exists
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex justify-between">
                <button
                  onClick={() => setStep(1)}
                  className="bg-gray-500 text-white px-6 py-2 rounded-lg"
                >
                  Back: Change V2 Spec
                </button>
                <button
                  onClick={() => setStep(3)}
                  disabled={!selectedV2Endpoint}
                  className="bg-blue-600 text-white px-6 py-2 rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  Next: Select V1 Spec
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Select V1 Spec and Endpoints */}
          {step === 3 && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold">Select V1 API Specification</h2>
              <p className="text-gray-600">Choose the V1 API specification and endpoints that will provide data for your V2 endpoint: <strong>{selectedV2Endpoint?.method} {selectedV2Endpoint?.path}</strong></p>

              {/* V1 Spec Selection */}
              {!selectedV1Spec ? (
                <div className="space-y-4">
                  <h3 className="text-lg font-medium">Available V1 API Specifications:</h3>
                  {v1Specs.length > 0 ? (
                    <div className="space-y-3">
                      {v1Specs.map((spec) => (
                        <div
                          key={spec.id}
                          className="border border-gray-200 rounded-lg p-4 cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition"
                          onClick={() => handleSpecSelection(spec.id, 'v1')}
                        >
                          <div className="font-medium">{spec.title || spec.name}</div>
                          <div className="text-sm text-gray-600 mt-1">{spec.description}</div>
                          <div className="text-xs text-gray-500 mt-2">Version: {spec.version}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">No V1 specs available</p>
                  )}

                  {/* Upload new V1 spec */}
                  <div className="border-t pt-4">
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Or upload a new V1 specification:</h4>
                    <input
                      type="file"
                      accept=".json,.yaml,.yml"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) handleFileUpload(file, 'v1');
                      }}
                      disabled={loading}
                      className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
                    />
                  </div>
                </div>
              ) : (
                <>
                  {/* Selected V1 Spec Info */}
                  <div className="bg-green-50 border border-green-200 rounded p-4">
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-medium text-green-800">{selectedV1Spec.title || selectedV1Spec.name}</h4>
                        <p className="text-sm text-green-600">Version: {selectedV1Spec.version}</p>
                        <p className="text-sm text-green-600">{selectedV1Spec.endpoints.length} endpoints available</p>
                      </div>
                      <button
                        onClick={() => {
                          setSelectedV1Spec(null);
                          setSelectedV1Endpoints([]);
                        }}
                        className="text-sm text-blue-600 hover:text-blue-700"
                      >
                        Change V1 Spec
                      </button>
                    </div>
                  </div>

                  {/* V1 Endpoint Selection */}
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <h3 className="text-lg font-medium">Select V1 Endpoints</h3>
                      <div className="flex gap-2">
                        <button
                          onClick={() => setSelectedV1Endpoints(selectedV1Spec.endpoints)}
                          className="text-sm bg-blue-100 text-blue-700 px-3 py-1 rounded hover:bg-blue-200 transition"
                        >
                          Select All ({selectedV1Spec.endpoints.length})
                        </button>
                        <button
                          onClick={() => setSelectedV1Endpoints([])}
                          className="text-sm bg-gray-100 text-gray-700 px-3 py-1 rounded hover:bg-gray-200 transition"
                        >
                          Clear All
                        </button>
                      </div>
                    </div>

                    <p className="text-sm text-gray-600">
                      Selected: {selectedV1Endpoints.length} of {selectedV1Spec.endpoints.length} endpoints
                    </p>

                    <div className="space-y-3">
                      {selectedV1Spec.endpoints.map((endpoint, index) => (
                        <div
                          key={index}
                          className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                            selectedV1Endpoints.includes(endpoint)
                              ? 'border-blue-500 bg-blue-50'
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                          onClick={() => {
                            if (selectedV1Endpoints.includes(endpoint)) {
                              setSelectedV1Endpoints(selectedV1Endpoints.filter(e => e !== endpoint));
                            } else {
                              setSelectedV1Endpoints([...selectedV1Endpoints, endpoint]);
                            }
                          }}
                        >
                          <div className="flex items-center justify-between">
                            <div>
                              <span className={`inline-block px-2 py-1 rounded text-xs font-medium mr-3 ${
                                endpoint.method === 'GET' ? 'bg-green-100 text-green-800' :
                                endpoint.method === 'POST' ? 'bg-blue-100 text-blue-800' :
                                endpoint.method === 'PUT' ? 'bg-yellow-100 text-yellow-800' :
                                'bg-red-100 text-red-800'
                              }`}>
                                {endpoint.method}
                              </span>
                              <span className="font-mono text-sm">{endpoint.path}</span>
                            </div>
                            <div className="text-right">
                              <p className="text-sm font-medium">{endpoint.summary}</p>
                              <p className="text-xs text-gray-500">{endpoint.operationId}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              <div className="flex justify-between">
                <button
                  onClick={() => setStep(2)}
                  className="bg-gray-500 text-white px-6 py-2 rounded-lg"
                >
                  Back: Change V2 Endpoint
                </button>
                <button
                  onClick={() => setStep(4)}
                  disabled={!selectedV1Spec || selectedV1Endpoints.length === 0}
                  className="bg-blue-600 text-white px-6 py-2 rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  Next: Generate Config
                </button>
              </div>
            </div>
          )}

          {/* Step 4: Generate Configuration */}
          {step === 4 && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold">Generate Configuration</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Configuration Name <span className="text-gray-500 text-xs">(Auto-generated from endpoint)</span>
                  </label>
                  <input
                    type="text"
                    value={configName}
                    readOnly
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 bg-gray-50 text-gray-700"
                    placeholder="Select a V2 endpoint to generate name"
                  />
                  {configName && selectedV2Endpoint && configExists(selectedV2Endpoint) && (
                    <p className="text-amber-600 text-sm mt-1">
                      ⚠️ A configuration for this endpoint already exists. Creating will overwrite it.
                    </p>
                  )}
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-medium mb-3">Configuration Summary</h3>
                  <div className="space-y-2 text-sm">
                    <p><strong>V2 Endpoint:</strong> {selectedV2Endpoint?.method} {selectedV2Endpoint?.path}</p>
                    <p><strong>V1 Sources:</strong> {selectedV1Endpoints.length} endpoints selected</p>
                    <div className="ml-4">
                      {selectedV1Endpoints.map((endpoint, index) => (
                        <p key={index} className="text-gray-600">
                          • {endpoint.method} {endpoint.path}
                        </p>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex justify-between">
                <button
                  onClick={() => setStep(3)}
                  className="bg-gray-500 text-white px-6 py-2 rounded-lg"
                >
                  Back
                </button>
                <div className="space-y-4">
                  {/* Qwen AI Status */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-medium mb-2">🤖 AI Generation Status</h4>
                    {qwenStatus ? (
                      <div className="space-y-1 text-sm">
                        <p>
                          <span className={`inline-block w-2 h-2 rounded-full mr-2 ${
                            qwenStatus.ollama_available ? 'bg-green-500' : 'bg-red-500'
                          }`}></span>
                          Ollama Service: {qwenStatus.ollama_available ? 'Available' : 'Not Available'}
                        </p>
                        <p>
                          <span className={`inline-block w-2 h-2 rounded-full mr-2 ${
                            qwenStatus.qwen_available ? 'bg-green-500' : 'bg-red-500'
                          }`}></span>
                          Qwen Model: {qwenStatus.qwen_available ? 'Ready' : 'Not Available'}
                        </p>
                        {!qwenStatus.qwen_available && qwenStatus.ollama_available && (
                          <p className="text-yellow-600 mt-2">
                            💡 Run: <code className="bg-gray-200 px-1 rounded">ollama pull qwen2.5:7b</code>
                          </p>
                        )}
                        {!qwenStatus.ollama_available && (
                          <p className="text-red-600 mt-2">
                            ❌ Please install Ollama and start the service first
                          </p>
                        )}
                      </div>
                    ) : (
                      <p className="text-gray-500 text-sm">Checking AI service status...</p>
                    )}
                  </div>

                  <button
                    onClick={generateConfig}
                    disabled={!configName || !qwenStatus?.qwen_available || isGenerating}
                    className="bg-green-600 text-white px-6 py-2 rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center"
                  >
                    {isGenerating ? (
                      <>
                        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Generating with AI...
                      </>
                    ) : (
                      <>
                        🤖 Implement V2 Endpoint with AI
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}