'use client';

import React, { useState } from 'react';
import { MoreHorizontal, Plus, Tag, X, MapPin } from 'lucide-react';

import { Machine } from '@/lib/types/machine';
import { mockTagService } from '@/lib/mock-api';
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

interface DevicesTableProps {
  machines: Machine[];
}

interface AddTagsModalProps {
  machine: Machine;
  onAddTags: (machineId: number, tags: string[]) => void;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

const AddTagsModal: React.FC<AddTagsModalProps> = ({ machine, onAddTags, isOpen, onOpenChange }) => {
  const [newTag, setNewTag] = useState('');
  const [tagsToAdd, setTagsToAdd] = useState<string[]>([]);

  const handleAddTag = () => {
    if (newTag.trim() && !tagsToAdd.includes(newTag.trim())) {
      setTagsToAdd([...tagsToAdd, newTag.trim()]);
      setNewTag('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTagsToAdd(tagsToAdd.filter(tag => tag !== tagToRemove));
  };

  const handleSubmit = () => {
    if (tagsToAdd.length > 0) {
      onAddTags(machine.id, tagsToAdd);
      setTagsToAdd([]);
      onOpenChange(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    }
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setTagsToAdd([]);
      setNewTag('');
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
              New Tag
            </Label>
            <div className="col-span-3 flex gap-2">
              <Input
                id="new-tag"
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Enter tag name"
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
                    {tag}
                    <button
                      type="button"
                      onClick={() => handleRemoveTag(tag)}
                      className="ml-1 hover:text-destructive"
                      aria-label={`Remove tag ${tag}`}
                      title={`Remove tag ${tag}`}
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
  onUpdateTags: (machineId: number, tags: string[]) => void;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

const EditTagsModal: React.FC<EditTagsModalProps> = ({ machine, onUpdateTags, isOpen, onOpenChange }) => {
  const [tags, setTags] = useState<string[]>(machine.tags || []);
  const [newTag, setNewTag] = useState('');

  const handleAddTag = () => {
    if (newTag.trim() && !tags.includes(newTag.trim())) {
      setTags([...tags, newTag.trim()]);
      setNewTag('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter(tag => tag !== tagToRemove));
  };

  const handleSubmit = () => {
    onUpdateTags(machine.id, tags);
    onOpenChange(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    }
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setTags(machine.tags || []);
      setNewTag('');
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
            <Label htmlFor="new-tag" className="text-right">
              New Tag
            </Label>
            <div className="col-span-3 flex gap-2">
              <Input
                id="new-tag"
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Enter tag name"
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
                    {tag}
                    <button
                      type="button"
                      onClick={() => handleRemoveTag(tag)}
                      className="ml-1 hover:text-destructive"
                      aria-label={`Remove tag ${tag}`}
                      title={`Remove tag ${tag}`}
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

const DevicesTable: React.FC<DevicesTableProps> = ({ machines }) => {
  const [machinesData, setMachinesData] = useState<Machine[]>(machines);
  const [addTagsModalOpen, setAddTagsModalOpen] = useState<{ machine: Machine; open: boolean } | null>(null);
  const [editTagsModalOpen, setEditTagsModalOpen] = useState<{ machine: Machine; open: boolean } | null>(null);

  const handleAddTags = async (machineId: number, newTags: string[]) => {
    try {
      // Call mock API to add tags
      const success = await mockTagService.addTags(machineId, newTags);
      
      if (success) {
        // Update local state
        setMachinesData(prev => 
          prev.map(machine => 
            machine.id === machineId 
              ? { ...machine, tags: [...(machine.tags || []), ...newTags] }
              : machine
          )
        );
      }
    } catch (error) {
      console.error('Failed to add tags:', error);
    }
  };

  const handleUpdateTags = async (machineId: number, updatedTags: string[]) => {
    try {
      // For now, we'll just update the local state
      // In a real implementation, you'd call the API to update tags
      setMachinesData(prev => 
        prev.map(machine => 
          machine.id === machineId 
            ? { ...machine, tags: updatedTags }
            : machine
        )
      );
      
      console.log(`Updated tags for machine ${machineId}:`, updatedTags);
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
    return `${location?.lat ? location.lat.toFixed(2) : '0'}, ${location?.long ? location.long.toFixed(2) : '0'}`;
  };

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
                      <Badge key={index} variant="secondary" className="text-xs">
                        <Tag className="h-3 w-3 mr-1" />
                        {tag}
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
