import { CroppedImage } from '@/lib/types/machine';

export function calculateSeverity(croppedImages: CroppedImage[]): number {
  const classNames = croppedImages.map(img => img.class_name.toLowerCase());
  
  const hasPerson = classNames.some(name => name.includes('person'));
  const hasBackpack = classNames.some(name => name.includes('backpack'));
  const hasGun = classNames.some(name => name.includes('gun'));
  
  if (hasGun) {
    return 3;
  }
  
  if (hasPerson && hasBackpack) {
    return 2;
  }
  
  if (hasPerson) {
    return 1;
  }
  
  return 1;
}

export function getSeverityLabel(severity: number): {
  label: string;
  className: string;
} {
  switch (severity) {
    case 1:
      return {
        label: 'Low',
        className: 'border-yellow-500 bg-yellow-400 text-black',
      };
    case 2:
      return {
        label: 'High', 
        className: 'border-orange-600 bg-orange-500 text-white',
      };
    case 3:
      return {
        label: 'Critical',
        className: 'border-red-700 bg-red-600 text-white',
      };
    default:
      return {
        label: 'Unknown',
        className: 'border-gray-500 bg-gray-400 text-white',
      };
  }
}