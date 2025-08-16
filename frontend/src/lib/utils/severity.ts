import { CroppedImage } from '@/lib/types/machine';

export function calculateSeverity(croppedImages: CroppedImage[]): number {
  if (!croppedImages?.length) return 0;
  
  const classNames = croppedImages.map(img => img.class_name.toLowerCase());
  
  // Check for weapons first (highest priority - severity 3)
  if (classNames.some(name => 
    name.includes('gun') || 
    name.includes('weapon') || 
    name.includes('firearm') || 
    name.includes('knife') ||
    name.includes('rifle') ||
    name.includes('pistol')
  )) {
    return 3;
  }
  
  // Check for person + backpack/suspicious items (severity 2)
  const hasPerson = classNames.some(name => 
    name.includes('person') || 
    name.includes('human') ||
    name.includes('man') ||
    name.includes('woman') ||
    name.includes('boy') ||
    name.includes('girl')
  );
  
  const hasSuspiciousItem = classNames.some(name => 
    name.includes('backpack') || 
    name.includes('bag') || 
    name.includes('suitcase') ||
    name.includes('package') ||
    name.includes('container')
  );
  
  if (hasPerson && hasSuspiciousItem) {
    return 2;
  }
  
  // Check for person only (severity 1)
  if (hasPerson) {
    return 1;
  }
  
  // No person detected (severity 0)
  return 0;
}

export function getSeverityLabel(severity: number): {
  label: string;
  className: string;
  description: string;
} {
  switch (severity) {
    case 0:
      return {
        label: 'LOW',
        className: 'bg-slate-100 text-slate-700 border border-slate-200',
        description: 'No person detected in the image'
      };
    case 1:
      return {
        label: 'MEDIUM',
        className: 'bg-blue-100 text-blue-700 border border-blue-200',
        description: 'Person detected in the image'
      };
    case 2:
      return {
        label: 'HIGH',
        className: 'bg-orange-100 text-orange-700 border border-orange-200',
        description: 'Person detected with suspicious item'
      };
    case 3:
      return {
        label: 'CRITICAL',
        className: 'bg-red-100 text-red-700 border border-red-200',
        description: 'Weapon or dangerous object detected'
      };
    default:
      return {
        label: 'UNKNOWN',
        className: 'bg-gray-100 text-gray-700 border border-gray-200',
        description: 'Unable to determine severity'
      };
  }
}

export function getSeverityColor(severity: number): string {
  switch (severity) {
    case 0: return 'bg-gray-400 text-white';
    case 1: return 'bg-blue-500 text-white';
    case 2: return 'bg-orange-500 text-white';
    case 3: return 'bg-red-600 text-white';
    default: return 'bg-gray-400 text-white';
  }
}

export function getSeverityText(severity: number): string {
  switch (severity) {
    case 0: return 'No Person';
    case 1: return 'Person Detected';
    case 2: return 'Person + Item';
    case 3: return 'Weapon Detected';
    default: return 'Unknown';
  }
}