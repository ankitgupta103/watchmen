import { useEffect, useState } from 'react';

import useOrganization from './use-organization';
import { usePubSub } from './use-pub-sub';

export const useMachineStats = (
  machineId: number,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
): { buffer: number; data: any | null } => {
  const { organizationId } = useOrganization();

  const [buffer, setBuffer] = useState(0);
  const [data, setData] = useState<{ topic: string; message: string } | null>(
    null,
  );

  const formatDate = (date: Date) => {
    return date.toISOString().split('T')[0];
  };

  const topicPattern = `${organizationId}/_all_/${formatDate(
    new Date(),
  )}/${machineId}/_all_/machine_stats/#`;

  usePubSub([topicPattern], (topic, message) => {
    setData({ topic, message });
    try {
      const data = typeof message === 'string' ? JSON.parse(message) : message;

      if (
        data &&
        typeof data.buffer !== 'undefined' &&
        data.machine_id === machineId
      ) {
        const bufferValue = parseFloat(data.buffer);
        if (!isNaN(bufferValue)) {
          setBuffer(bufferValue);
        }
      }
    } catch (err) {
      console.error('Error processing machine buffer message:', err);
    }
  });

  useEffect(() => {
    setBuffer(0);
  }, [machineId]);

  return {
    buffer,
    data,
  };
};
