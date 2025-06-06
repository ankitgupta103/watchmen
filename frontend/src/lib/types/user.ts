import { Organization } from './organization';

export interface User {
  id: number;
  name: string;
  email: string;
  account_id: string;
  roles: Organization[];
}
