import React from 'react';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'secondary';
  className?: string;
}

export function Spinner({
  size = 'md',
  variant = 'primary',
  className = '',
}: SpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  const variantClasses = {
    primary: 'border-primary',
    secondary: 'border-gray-300',
  };

  return (
    <div
      className={` ${sizeClasses[size]} ${variantClasses[variant]} animate-spin rounded-full border-4 border-t-transparent ${className} `}
    />
  );
}
