'use client';

import dynamic from 'next/dynamic';

const NetworkMapWithNoSSR = dynamic(() => import('./components/network-map'), {
  ssr: false,
});

export default function NetworkSimulation() {
  return <NetworkMapWithNoSSR />;
}
