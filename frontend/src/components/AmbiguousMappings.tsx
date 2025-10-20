import { AmbiguousMapping } from '@/lib/types';

interface AmbiguousMappingsProps {
  mappings: AmbiguousMapping[];
}

export default function AmbiguousMappings({ mappings }: AmbiguousMappingsProps) {
  if (!mappings || mappings.length === 0) {
    return null;
  }

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
            The AI found multiple possible mappings for the following fields. Please review and select the most appropriate option:
          </p>
          <div className="space-y-4">
            {mappings.map((mapping, index) => (
              <div key={index} className="bg-white rounded-lg p-4 border border-yellow-200">
                <div className="font-medium text-gray-900 mb-3">
                  <span className="text-blue-600">V2 Field:</span> {mapping.v2_field}
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium text-gray-700 mb-2">
                    Possible V1 mappings:
                  </div>
                  {mapping.proposals.map((proposal, pIndex) => (
                    <div key={pIndex} className="flex items-center justify-between p-2 bg-gray-50 rounded border">
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-sm text-gray-900">
                          {proposal.v1_field}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex items-center gap-1">
                          <div className={`w-2 h-2 rounded-full ${
                            proposal.confidence >= 0.8 ? 'bg-green-500' :
                            proposal.confidence >= 0.5 ? 'bg-yellow-500' : 'bg-red-500'
                          }`}></div>
                          <span className="text-xs text-gray-600">
                            {Math.round(proposal.confidence * 100)}%
                          </span>
                        </div>
                        <button
                          className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition"
                          onClick={() => {
                            // TODO: Implement selection logic
                            console.log('Selected:', proposal.v1_field);
                          }}
                        >
                          Select
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 text-xs text-yellow-700">
            💡 <strong>Tip:</strong> Review the V1 API documentation or test data to determine which field mapping is most accurate.
          </div>
        </div>
      </div>
    </div>
  );
}