import React from 'react';

import { getOrg } from '@/lib/auth/getOrg';
import { API_BASE_URL } from '@/lib/constants';
import { fetcher } from '@/lib/fetcher';
import { Machine } from '@/lib/types/machine';
import PageHeader from './components/page-header';
import DevicesTable from './components/devices-table';

export default async function DashboardPage() {
  const { organization_uid } = await getOrg();

  let machines: Machine[] = [];
  
  try {
    const response = await fetcher<{
      status: string;
      data: Machine[];
    }>(`${API_BASE_URL}/machines?organization_uid=${organization_uid}`);
    machines = response.data || [];
  } catch (error) {
    console.error('Failed to fetch machines:', error);
  }

  // Mock data for testing - remove this when real API is available
  const mockMachines: Machine[] = [
    {
      id: 1,
      name: "Drone Alpha-1",
      type: "Quadcopter",
      machine_uid: "DRONE_001",
      specifications: { weight: "2.5kg", range: "10km" },
      mfg_date: "2024-01-15",
      activation_date: "2024-02-01",
      end_of_service_date: null,
      current_owner: 1,
      current_owner_name: "John Doe",
      machine_status: "Active",
      connection_status: "Online",
      last_location: { lat: 37.7749, long: -122.4194, timestamp: "2024-01-20T10:00:00Z" },
      created_at: "2024-01-15T00:00:00Z",
      updated_at: "2024-01-20T10:00:00Z",
      model_id: 1,
      model_uid: "MODEL_001",
      manufacturer_id: 1,
      model_specifications: { max_speed: "60km/h" },
      tags: ["Surveillance", "High-Altitude", "Long-Range"]
    },
    {
      id: 2,
      name: "Robot Beta-2",
      type: "Ground Robot",
      machine_uid: "ROBOT_002",
      specifications: { weight: "15kg", battery: "8 hours" },
      mfg_date: "2024-01-10",
      activation_date: "2024-01-25",
      end_of_service_date: null,
      current_owner: 1,
      current_owner_name: "John Doe",
      machine_status: "Maintenance",
      connection_status: "Offline",
      last_location: { lat: 37.7849, long: -122.4094, timestamp: "2024-01-19T15:30:00Z" },
      created_at: "2024-01-10T00:00:00Z",
      updated_at: "2024-01-19T15:30:00Z",
      model_id: 2,
      model_uid: "MODEL_002",
      manufacturer_id: 1,
      model_specifications: { terrain: "All-Terrain" },
      tags: ["Patrol", "Heavy-Duty"]
    },
    {
      id: 3,
      name: "Sensor Gamma-3",
      type: "IoT Sensor",
      machine_uid: "SENSOR_003",
      specifications: { power: "Solar", range: "100m" },
      mfg_date: "2024-01-05",
      activation_date: "2024-01-20",
      end_of_service_date: null,
      current_owner: 1,
      current_owner_name: "John Doe",
      machine_status: "Active",
      connection_status: "Online",
      last_location: { lat: 37.7649, long: -122.4294, timestamp: "2024-01-20T09:15:00Z" },
      created_at: "2024-01-05T00:00:00Z",
      updated_at: "2024-01-20T09:15:00Z",
      model_id: 3,
      model_uid: "MODEL_003",
      manufacturer_id: 1,
      model_specifications: { sensor_type: "Environmental" },
      tags: ["Weather", "Air-Quality"]
    }
  ];

  // Use mock data if no real data is available
  const displayMachines = machines.length > 0 ? machines : mockMachines;

  return (
    <section className="flex h-full w-full flex-col gap-4 p-4">
      <PageHeader />
      <div className="bg-background h-full w-full overflow-y-auto rounded-lg border p-6">
        <DevicesTable machines={displayMachines} />
      </div>
    </section>
  );
}
