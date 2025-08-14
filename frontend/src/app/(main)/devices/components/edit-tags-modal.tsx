'use client';

import React, { useState } from 'react';
import { Tag, X } from 'lucide-react';

import { Machine, MachineTag } from '@/lib/types/machine';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface EditTagsModalProps {
  machine: Machine;
  onUpdateTags: (machineId: number, updatedTags: MachineTag[], deletedTagIds: number[]) => void;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

const EditTagsModal: React.FC<EditTagsModalProps> = ({ 
  machine, 
  onUpdateTags, 
  isOpen, 
  onOpenChange 
}) => {
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

export default EditTagsModal;