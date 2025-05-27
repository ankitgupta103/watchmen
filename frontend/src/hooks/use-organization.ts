import { getCookie } from '@/lib/cookies';
import { Organization } from '@/lib/types/organization';

export default function useOrganization() {
  const organization = JSON.parse(
    getCookie('organization') || '{}',
  ) as Organization;

  return {
    organization,
    organizationRole: organization?.role,
    organizationId: organization?.organization_id,
    organizationUid: organization?.organization_uid,
    organizationName: organization?.organization_name,
    organizationPermissions: organization?.permissions,
  };
}

export function useOrganizationPermissions() {
  const { organizationPermissions } = useOrganization();
  return organizationPermissions;
}
