interface ConfidenceScoreProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export default function ConfidenceScore({
  score,
  size = 'md',
  showLabel = true
}: ConfidenceScoreProps) {
  const percentage = Math.round(score * 100);

  // Determine color based on score
  const getColor = () => {
    if (score >= 0.9) return 'green';
    if (score >= 0.7) return 'yellow';
    return 'red';
  };

  const color = getColor();

  // Size variants
  const sizes = {
    sm: {
      container: 'h-2',
      text: 'text-xs',
      maxWidth: 'max-w-24'
    },
    md: {
      container: 'h-3',
      text: 'text-sm',
      maxWidth: 'max-w-32'
    },
    lg: {
      container: 'h-4',
      text: 'text-base',
      maxWidth: 'max-w-48'
    }
  };

  const sizeConfig = sizes[size];

  return (
    <div className="flex items-center gap-3">
      {showLabel && (
        <span className={`font-medium text-gray-700 ${sizeConfig.text}`}>
          Confidence:
        </span>
      )}

      <div className={`flex-1 ${sizeConfig.maxWidth}`}>
        <div className={`${sizeConfig.container} bg-gray-200 rounded-full overflow-hidden`}>
          <div
            className={`h-full transition-all duration-300 ${
              color === 'green' ? 'bg-green-500' :
              color === 'yellow' ? 'bg-yellow-500' : 'bg-red-500'
            }`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>

      <span className={`font-bold ${sizeConfig.text} ${
        color === 'green' ? 'text-green-600' :
        color === 'yellow' ? 'text-yellow-600' : 'text-red-600'
      }`}>
        {percentage}%
      </span>
    </div>
  );
}