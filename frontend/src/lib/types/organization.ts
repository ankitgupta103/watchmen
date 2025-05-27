export type OrganizationRole = 'owner' | 'admin' | 'user';

export interface Organization {
  role: OrganizationRole;
  organization_id: number;
  organization_uid: string;
  organization_name: string;
  permissions: string[];
  organization_logo: string | null;
}
