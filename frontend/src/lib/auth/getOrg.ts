import { cookies } from 'next/headers';

import { Organization } from '../types/organization';

export async function getOrg(): Promise<Organization> {
  const cookieStore = await cookies();
  return JSON.parse(cookieStore.get('organization')?.value ?? '{}');
}
