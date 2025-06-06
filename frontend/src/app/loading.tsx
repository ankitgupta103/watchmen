import React from 'react';
import Image from 'next/image';

import { Spinner } from '@/components/common/spinner';

export default function Loading() {
  return (
    <div className="fixed inset-0 z-50 flex animate-pulse items-center justify-center bg-white/80 backdrop-blur-sm">
      <div className="flex flex-col items-center gap-6">
        <div className={'flex flex-col items-center justify-center gap-2'}>
          <Image
            src={'/assets/png/vyomos-logo.png'}
            alt="Vyom OS logo"
            width={240}
            height={240}
          />
          <span className="text-muted-foreground text-4xl">Netrajaal</span>
        </div>
        <Spinner size="lg" />
        <p className="text-lg font-medium text-gray-700">Loading...</p>
      </div>
    </div>
  );
}
