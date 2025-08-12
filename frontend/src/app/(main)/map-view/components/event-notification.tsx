import { useEffect, useState } from 'react';
import { X, Eye } from 'lucide-react';
import { MachineEvent } from '@/lib/types/activity';
import { getSeverityLabel } from '@/lib/utils/severity';

interface EventNotificationProps {
  event: MachineEvent;
  machineName: string;
  onClose: () => void;
}

export default function EventNotification({ event, machineName, onClose }: EventNotificationProps) {
  const [isVisible, setIsVisible] = useState(true);
  const severityInfo = getSeverityLabel(event.severity);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      setTimeout(onClose, 300); // Wait for fade out animation
    }, 8000); // Auto-hide after 8 seconds

    return () => clearTimeout(timer);
  }, [onClose]);

  const handleClose = () => {
    setIsVisible(false);
    setTimeout(onClose, 300);
  };

  if (!isVisible) return null;

  return (
    <div className={`
      fixed top-4 right-4 z-[1001] max-w-sm w-full
      transform transition-all duration-300 ease-in-out
      ${isVisible ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}
    `}>
      <div className={`
        bg-white rounded-lg shadow-xl border-l-4 p-4
        ${event.severity === 3 ? 'border-l-red-500' : 
          event.severity === 2 ? 'border-l-orange-500' : 'border-l-blue-500'}
      `}>
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-2xl">{severityInfo.icon}</span>
            <div>
              <h4 className="font-semibold text-gray-900 text-sm">
                {severityInfo.label}
              </h4>
              <p className="text-xs text-gray-600">{machineName}</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close notification"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Event Details */}
        <div className="space-y-2">
          <p className="text-sm text-gray-700">
            {event.eventstr || 'Event detected'}
          </p>
          
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>{event.timestamp.toLocaleTimeString()}</span>
            <div className="flex items-center gap-1">
              <Eye className="h-3 w-3" />
              <span>Click machine for details</span>
            </div>
          </div>
        </div>

        {/* Severity Indicator */}
        <div className={`
          mt-3 p-2 rounded-md text-xs font-medium text-white
          ${event.severity === 3 ? 'bg-red-500' : 
            event.severity === 2 ? 'bg-orange-500' : 'bg-blue-500'}
        `}>
          Severity Level {event.severity}: {severityInfo.description}
        </div>
      </div>
    </div>
  );
}
