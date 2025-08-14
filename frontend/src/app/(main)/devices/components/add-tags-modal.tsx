'use client';

import React, { useState } from 'react';
import { Tag, X } from 'lucide-react';

import { Machine } from '@/lib/types/machine';
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

interface AddTagsModalProps {
  machine: Machine;
  onAddTags: (machineId: number, tags: { name: string; description?: string }[]) => void;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

const AddTagsModal: React.FC<AddTagsModalProps> = ({ 
  machine, 
  onAddTags, 
  isOpen, 
  onOpenChange 
}) => {
  const [newTag, setNewTag] = useState('');
  const [newTagDescription, setNewTagDescription] = useState('');
  const [tagsToAdd, setTagsToAdd] = useState<{ name: string; description?: string }[]>([]);

  const handleAddTag = () => {
    if (newTag.trim() && !tagsToAdd.some(tag => tag.name === newTag.trim())) {
      setTagsToAdd([...tagsToAdd, { 
        name: newTag.trim(), 
        description: newTagDescription.trim() || undefined 
      }]);
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

export default AddTagsModal;