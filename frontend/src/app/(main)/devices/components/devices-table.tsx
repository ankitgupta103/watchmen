'use client';

import React, { useState, useEffect } from 'react';
import { MoreHorizontal, Plus, Tag, X, MapPin } from 'lucide-react';

import { Machine, MachineTag } from '@/lib/types/machine';
import { fetcherClient } from '@/lib/fetcher-client';
import { API_BASE_URL } from '@/lib/constants';
import useOrganization from '@/hooks/use-organization';
import useToken from '@/hooks/use-token';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface TagResponse {
  success: boolean;
  data: MachineTag[] | MachineTag | { message: string };
}

interface CreateTagRequest {
  organization_uid: string;
  name: string;
  description?: string;
  tag_id?: number;
}

interface DeleteTagRequest {
  organization_uid: string;
  tag_id: number;
  delete_completely?: boolean;
}

interface DevicesTableProps {
  machines: Machine[];
}

interface AddTagsModalProps {
  machine: Machine;
  onAddTags: (machineId: number, tags: { name: string; description?: string }[]) => void;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

const AddTagsModal: React.FC<AddTagsModalProps> = ({ machine, onAddTags, isOpen, onOpenChange }) => {
  const [newTag, setNewTag] = useState('');
  const [newTagDescription, setNewTagDescription] = useState('');
  const [tagsToAdd, setTagsToAdd] = useState<{ name: string; description?: string }[]>([]);

  const handleAddTag = () => {
    if (newTag.trim() && !tagsToAdd.some(tag => tag.name === newTag.trim())) {
      setTagsToAdd([...tagsToAdd, { name: newTag.trim(), description: newTagDescription.trim() || undefined }]);
      setNewTag('');
      setNewTagDescription('');
    }
  };

  const handleRemoveTag = (tagToRemove: { name: string; description?: string }) => {
    setTagsToAdd(tagsToAdd.filter(tag => tag.name !== tagToRemove.name));
  };

  const handleSubmit = () => {
    if (tagsToAdd.length > 0) {
      onAddTags(machine.id, tagsToAdd);
      setTagsToAdd([]);
      onOpenChange(false);
    }
  };


  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setTagsToAdd([]);
      setNewTag('');
      setNewTagDescription('');
    }
    onOpenChange(open);
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Add Tags to {machine.name}</DialogTitle>
          <DialogDescription>
            Create and add tags to organize and categorize this machine.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="new-tag" className="text-right">
              Tag Name
            </Label>
            <div className="col-span-3">
              <Input
                id="new-tag"
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
                placeholder="Enter tag name"
              />
            </div>
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="new-tag-desc" className="text-right">
              Description
            </Label>
            <div className="col-span-3 flex gap-2">
              <Input
                id="new-tag-desc"
                value={newTagDescription}
                onChange={(e) => setNewTagDescription(e.target.value)}
                placeholder="Enter tag description (optional)"
                className="flex-1"
              />
              <Button type="button" onClick={handleAddTag} size="sm">
                Add
              </Button>
            </div>
          </div>
          {tagsToAdd.length > 0 && (
            <div className="grid grid-cols-4 items-center gap-4">
              <Label className="text-right">Tags to Add</Label>
              <div className="col-span-3 flex flex-wrap gap-2">
                {tagsToAdd.map((tag, index) => (
                  <Badge key={index} variant="secondary" className="flex items-center gap-1">
                    <Tag className="h-3 w-3" />
                    <div className="flex flex-col">
                      <span>{tag.name}</span>
                      {tag.description && <span className="text-xs opacity-70">{tag.description}</span>}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveTag(tag)}
                      className="ml-1 hover:text-destructive"
                      aria-label={`Remove tag ${tag.name}`}
                      title={`Remove tag ${tag.name}`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="button" onClick={handleSubmit} disabled={tagsToAdd.length === 0}>
            Add Tags
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

interface EditTagsModalProps {
  machine: Machine;
  onUpdateTags: (machineId: number, updatedTags: MachineTag[], deletedTagIds: number[]) => void;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

const EditTagsModal: React.FC<EditTagsModalProps> = ({ machine, onUpdateTags, isOpen, onOpenChange }) => {
  const [tags, setTags] = useState<MachineTag[]>(machine.tags || []);
  const [newTag, setNewTag] = useState('');
  const [newTagDescription, setNewTagDescription] = useState('');
  const [deletedTagIds, setDeletedTagIds] = useState<number[]>([]);

  const handleAddTag = () => {
    if (newTag.trim() && !tags.some(tag => tag.name === newTag.trim())) {
      const newTagObj: MachineTag = {
        id: 0,
        key: newTag.trim().toLowerCase().replace(/\s+/g, '_'),
        name: newTag.trim(),
        description: newTagDescription.trim() || undefined,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      setTags([...tags, newTagObj]);
      setNewTag('');
      setNewTagDescription('');
    }
  };

  const handleRemoveTag = (tagToRemove: MachineTag) => {
    if (tagToRemove.id > 0) {
      setDeletedTagIds([...deletedTagIds, tagToRemove.id]);
    }
    setTags(tags.filter(tag => tag.name !== tagToRemove.name));
  };

  const handleSubmit = () => {
    onUpdateTags(machine.id, tags, deletedTagIds);
    onOpenChange(false);
  };


  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setTags(machine.tags || []);
      setNewTag('');
      setNewTagDescription('');
      setDeletedTagIds([]);
    }
    onOpenChange(open);
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Edit Tags for {machine.name}</DialogTitle>
          <DialogDescription>
            Add, remove, or modify tags for this machine.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="edit-new-tag" className="text-right">
              Tag Name
            </Label>
            <div className="col-span-3">
              <Input
                id="edit-new-tag"
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
                placeholder="Enter tag name"
              />
            </div>
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="edit-new-tag-desc" className="text-right">
              Description
            </Label>
            <div className="col-span-3 flex gap-2">
              <Input
                id="edit-new-tag-desc"
                value={newTagDescription}
                onChange={(e) => setNewTagDescription(e.target.value)}
                placeholder="Enter tag description (optional)"
                className="flex-1"
              />
              <Button type="button" onClick={handleAddTag} size="sm">
                Add
              </Button>
            </div>
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label className="text-right">Current Tags</Label>
            <div className="col-span-3 flex flex-wrap gap-2">
              {tags.length > 0 ? (
                tags.map((tag, index) => (
                  <Badge key={index} variant="secondary" className="flex items-center gap-1">
                    <Tag className="h-3 w-3" />
                    <div className="flex flex-col">
                      <span>{tag.name}</span>
                      {tag.description && <span className="text-xs opacity-70">{tag.description}</span>}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveTag(tag)}
                      className="ml-1 hover:text-destructive"
                      aria-label={`Remove tag ${tag.name}`}
                      title={`Remove tag ${tag.name}`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))
              ) : (
                <span className="text-muted-foreground text-sm">No tags</span>
              )}
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="button" onClick={handleSubmit}>
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// Tag API Functions
const getMachineTags = async (
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

const createOrUpdateTag = async (
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

const deleteTag = async (
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

const DevicesTable: React.FC<DevicesTableProps> = ({ machines }) => {
  const { organizationUid } = useOrganization();
  const { token } = useToken();
  const [machinesData, setMachinesData] = useState<Machine[]>(machines);
  const [addTagsModalOpen, setAddTagsModalOpen] = useState<{ machine: Machine; open: boolean } | null>(null);
  const [editTagsModalOpen, setEditTagsModalOpen] = useState<{ machine: Machine; open: boolean } | null>(null);

  useEffect(() => {
    const loadMachineTags = async () => {
      if (!organizationUid || !token) return;
      
      const updatedMachines = await Promise.all(
        machines.map(async (machine) => {
          const tags = await getMachineTags(machine.id, organizationUid, token);
          return { ...machine, tags };
        })
      );
      
      setMachinesData(updatedMachines);
    };

    loadMachineTags();
  }, [machines, organizationUid, token]);

  const handleAddTags = async (machineId: number, newTags: { name: string; description?: string }[]) => {
    if (!organizationUid || !token) {
      console.error('Organization UID or token not found');
      return;
    }

    try {
      const addedTags: MachineTag[] = [];
      
      for (const tag of newTags) {
        const result = await createOrUpdateTag(machineId, {
          organization_uid: organizationUid,
          name: tag.name,
          description: tag.description,
        }, token);
        
        if (result) {
          addedTags.push(result);
        }
      }
      
      if (addedTags.length > 0) {
        setMachinesData(prev => 
          prev.map(machine => 
            machine.id === machineId 
              ? { ...machine, tags: [...(machine.tags || []), ...addedTags] }
              : machine
          )
        );
      }
    } catch (error) {
      console.error('Failed to add tags:', error);
    }
  };

  const handleDeleteTag = async (machineId: number, tagId: number) => {
    if (!organizationUid || !token) {
      console.error('Organization UID or token not found');
      return;
    }

    try {
      const success = await deleteTag(machineId, {
        organization_uid: organizationUid,
        tag_id: tagId,
        delete_completely: false,
      }, token);

      if (success) {
        setMachinesData(prev => 
          prev.map(machine => 
            machine.id === machineId 
              ? { ...machine, tags: machine.tags?.filter(tag => tag.id !== tagId) || [] }
              : machine
          )
        );
      }
    } catch (error) {
      console.error('Failed to delete tag:', error);
    }
  };

  const handleUpdateTags = async (machineId: number, updatedTags: MachineTag[], deletedTagIds: number[]) => {
    if (!organizationUid || !token) {
      console.error('Organization UID or token not found');
      return;
    }

    try {
      // Delete removed tags
      for (const tagId of deletedTagIds) {
        await deleteTag(machineId, {
          organization_uid: organizationUid,
          tag_id: tagId,
          delete_completely: false,
        }, token);
      }

      // Create new tags (those with id: 0)
      const newTags = updatedTags.filter(tag => tag.id === 0);
      const finalTags: MachineTag[] = [...updatedTags.filter(tag => tag.id > 0)];

      for (const tag of newTags) {
        const result = await createOrUpdateTag(machineId, {
          organization_uid: organizationUid,
          name: tag.name,
          description: tag.description,
        }, token);
        
        if (result) {
          finalTags.push(result);
        }
      }
      
      // Update local state with final tags
      setMachinesData(prev => 
        prev.map(machine => 
          machine.id === machineId 
            ? { ...machine, tags: finalTags }
            : machine
        )
      );
      
      console.log(`Updated tags for machine ${machineId}`);
    } catch (error) {
      console.error('Failed to update tags:', error);
    }
  };

  const getConnectionStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'online':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'offline':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'connecting':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const formatLocation = (location: { lat: number; long: number; timestamp: string }) => {
    return `${location?.lat }, ${location?.long }`;
  };

  console.log(machinesData);

  return (
    <div className="w-full">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Connection</TableHead>
            <TableHead>Location</TableHead>
            <TableHead>Tags</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {machinesData.map((machine) => (
            <TableRow key={machine.id}>
              <TableCell className="font-medium">{machine.name}</TableCell>
              <TableCell>{machine.type}</TableCell>
              <TableCell>
                <Badge 
                  variant="outline" 
                  className={`border ${getConnectionStatusColor(machine.connection_status)}`}
                >
                  {machine.connection_status}
                </Badge>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">{formatLocation(machine.last_location)}</span>
                </div>
              </TableCell>
              <TableCell>
                <div className="flex flex-wrap gap-1">
                  {machine.tags && machine.tags.length > 0 ? (
                    machine.tags.map((tag, index) => (
                      <Badge key={index} variant="secondary" className="text-xs flex items-center gap-1">
                        <Tag className="h-3 w-3" />
                        <div className="flex flex-col">
                          <span>{tag.name}</span>
                          {tag.description && <span className="text-xs opacity-70">{tag.description}</span>}
                        </div>
                        <button
                          type="button"
                          onClick={() => handleDeleteTag(machine.id, tag.id)}
                          className="ml-1 hover:text-destructive"
                          aria-label={`Remove tag ${tag.name}`}
                          title={`Remove tag ${tag.name}`}
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))
                  ) : (
                    <span className="text-muted-foreground text-sm">No tags</span>
                  )}
                </div>
              </TableCell>
              <TableCell>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="h-8 w-8 p-0">
                      <span className="sr-only">Open menu</span>
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem 
                      onClick={() => setAddTagsModalOpen({ machine, open: true })}
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      Add Tags
                    </DropdownMenuItem>
                    <DropdownMenuItem 
                      onClick={() => setEditTagsModalOpen({ machine, open: true })}
                    >
                      <Tag className="h-4 w-4 mr-2" />
                      Edit Tags
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {/* Add Tags Modal */}
      {addTagsModalOpen && (
        <AddTagsModal
          machine={addTagsModalOpen.machine}
          onAddTags={handleAddTags}
          isOpen={addTagsModalOpen.open}
          onOpenChange={(open) => setAddTagsModalOpen(open ? addTagsModalOpen : null)}
        />
      )}

      {/* Edit Tags Modal */}
      {editTagsModalOpen && (
        <EditTagsModal
          machine={editTagsModalOpen.machine}
          onUpdateTags={handleUpdateTags}
          isOpen={editTagsModalOpen.open}
          onOpenChange={(open) => setEditTagsModalOpen(open ? editTagsModalOpen : null)}
        />
      )}
    </div>
  );
};

export default DevicesTable;
