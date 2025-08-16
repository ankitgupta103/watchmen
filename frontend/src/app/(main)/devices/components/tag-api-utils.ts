import { fetcherClient } from '@/lib/fetcher-client';
import { API_BASE_URL } from '@/lib/constants';
import { Machine, MachineTag } from '@/lib/types/machine';

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

export interface AddExistingTagRequest {
  organization_uid: string;
  tag_id: number;
}

export const getAllTags = async (
  organizationUid: string,
  token: string
): Promise<MachineTag[]> => {
  try {
    // Since there's no dedicated tags endpoint, we'll fetch tags from all machines
    // and aggregate unique tags
    const url = `${API_BASE_URL}/machines?organization_uid=${organizationUid}`;
    const response = await fetcherClient<{ data: Machine[] }>(url, token);
    
    if (response?.data) {
      // Extract all unique tags from all machines
      const allTags: MachineTag[] = [];
      const tagMap = new Map<number, MachineTag>();
      
      response.data.forEach(machine => {
        if (machine.tags) {
          machine.tags.forEach(tag => {
            if (!tagMap.has(tag.id)) {
              tagMap.set(tag.id, tag);
              allTags.push(tag);
            }
          });
        }
      });
      
      return allTags;
    }
    
    return [];
  } catch (error) {
    console.error('Failed to fetch all tags:', error);
    return [];
  }
};

export const getMachineTags = async (
  machineId: number,
  organizationUid: string,
  token: string
): Promise<MachineTag[]> => {
  try {
    const url = `${API_BASE_URL}/machines/${machineId}/tags/?organization_uid=${organizationUid}`;
    const response = await fetcherClient<TagResponse>(url, token);
    
    if (response?.success && Array.isArray(response.data)) {
      return response.data;
    }
    
    return [];
  } catch (error) {
    console.error('Failed to fetch machine tags:', error);
    return [];
  }
};

export const createOrUpdateTag = async (
  machineId: number,
  request: CreateTagRequest,
  token: string
): Promise<MachineTag | null> => {
  try {
    const url = `${API_BASE_URL}/machines/${machineId}/tags/manage/`;
    const response = await fetcherClient<TagResponse>(url, token, {
      method: 'POST',
      body: request,
    });
    
    if (response?.success && !Array.isArray(response.data) && response.data && 'id' in response.data) {
      return response.data as MachineTag;
    }
    
    return null;
  } catch (error) {
    console.error('Failed to create/update tag:', error);
    return null;
  }
};

export const addExistingTagToMachine = async (
  machineId: number,
  request: AddExistingTagRequest,
  token: string
): Promise<MachineTag | null> => {
  try {
    const url = `${API_BASE_URL}/machines/${machineId}/tags/manage/`;
    const response = await fetcherClient<TagResponse>(url, token, {
      method: 'POST',
      body: request,
    });
    
    if (response?.success && !Array.isArray(response.data) && response.data && 'id' in response.data) {
      return response.data as MachineTag;
    }
    
    return null;
  } catch (error) {
    console.error('Failed to add existing tag to machine:', error);
    return null;
  }
};

export const deleteTag = async (
  machineId: number,
  request: DeleteTagRequest,
  token: string
): Promise<boolean> => {
  try {
    const url = `${API_BASE_URL}/machines/${machineId}/tags/manage/`;
    const response = await fetcherClient<TagResponse>(url, token, {
      method: 'DELETE',
      body: request,
    });
    
    return response?.success ?? false;
  } catch (error) {
    console.error('Failed to delete tag:', error);
    return false;
  }
};