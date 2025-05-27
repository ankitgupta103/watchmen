import Image from 'next/image';

import { cn } from '@/lib/utils';

interface LogoProps {
  className?: string;
  showText?: boolean;
}

export function Logo({ className, showText = true }: LogoProps) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <Image
        src={'/assets/png/vyomos-logo.png'}
        alt="Vyom OS logo"
        width={40}
        height={40}
      />
      {showText && (
        <div className="flex flex-col">
          <span className={'text-xl font-bold'}>Vyom OS</span>
          <span className="text-muted-foreground text-xs">Fleet Manager</span>
        </div>
      )}
    </div>
  );
}
