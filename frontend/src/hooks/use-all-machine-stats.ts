import { Machine } from '@/lib/types/machine';

import { useMachineStats } from './use-machine-stats';

export default function useAllMachineStats(machines: Machine[]) {
  // This will force all useMachineStats hooks to be called in the same order every render
  // eslint-disable-next-line
  const stats: Record<number, { buffer: number; data: any | null }> = {};
  for (let i = 0; i < machines.length; i++) {
    const machine = machines[i];
    // eslint-disable-next-line react-hooks/rules-of-hooks
    stats[machine.id] = useMachineStats(machine.id);
  }
  return stats;
}
