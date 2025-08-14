import { API_BASE_URL } from '../constants';
import { fetcher } from '../fetcher';
import { MachineTag } from '../types/machine';

export interface TagResponse {
  success: boolean;
  data: MachineTag[] | MachineTag | { message: string };
}

export interface CreateTagRequest {
  organization_uid: string;
  name: string;
  description?: string;
  tag_id?: number;
}

export interface DeleteTagRequest {
  organization_uid: string;
  tag_id: number;
  delete_completely?: boolean;
}

export class MachineTagsService {
  private static baseUrl = `${API_BASE_URL}`;

  static async getMachineTags(
    machineId: number,
    organizationUid: string
  ): Promise<MachineTag[]> {
    try {
      const url = `${this.baseUrl}/machines/${machineId}/tags/?organization_uid=${organizationUid}`;
      const response = await fetcher<TagResponse>(url);
      
      if (response.success && Array.isArray(response.data)) {
        return response.data;
      }
      
      return [];
    } catch (error) {
      console.error('Failed to fetch machine tags:', error);
      return [];
    }
  }

  static async createOrUpdateTag(
    machineId: number,
    request: CreateTagRequest
  ): Promise<MachineTag | null> {
    try {
      const url = `${this.baseUrl}/machines/${machineId}/tags/manage/`;
      const response = await fetcher<TagResponse>(url, {
        method: 'POST',
        body: request,
      });
      
      if (response.success && !Array.isArray(response.data) && 'id' in response.data) {
        return response.data as MachineTag;
      }
      
      return null;
    } catch (error) {
      console.error('Failed to create/update tag:', error);
      return null;
    }
  }

  static async deleteTag(
    machineId: number,
    request: DeleteTagRequest
  ): Promise<boolean> {
    try {
      const url = `${this.baseUrl}/machines/${machineId}/tags/manage/`;
      const response = await fetcher<TagResponse>(url, {
        method: 'DELETE',
        body: request,
      });
      
      return response.success;
    } catch (error) {
      console.error('Failed to delete tag:', error);
      return false;
    }
  }
}