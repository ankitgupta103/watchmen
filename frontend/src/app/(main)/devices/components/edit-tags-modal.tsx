'use client';

import React, { useState } from 'react';
import { Edit, Tag, X } from 'lucide-react';

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

import { Machine, MachineTag } from '@/lib/types/machine';

interface EditTagsModalProps {
  machine: Machine;
  onUpdateTags: (
    machineId: number,
    updatedTags: MachineTag[],
    deletedTagIds: number[],
  ) => void;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

const EditTagsModal: React.FC<EditTagsModalProps> = ({
  machine,
  onUpdateTags,
  isOpen,
  onOpenChange,
}) => {
  const [tags, setTags] = useState<MachineTag[]>(machine.tags || []);
  const [deletedTagIds, setDeletedTagIds] = useState<number[]>([]);
  const [editingTag, setEditingTag] = useState<MachineTag | null>(null);
  const [editingName, setEditingName] = useState('');
  const [editingDescription, setEditingDescription] = useState('');

  const handleRemoveTag = (tagToRemove: MachineTag) => {
    if (tagToRemove.id > 0) {
      setDeletedTagIds([...deletedTagIds, tagToRemove.id]);
    }
    setTags(tags.filter((tag) => tag.name !== tagToRemove.name));
  };

  const handleEditTag = (tag: MachineTag) => {
    setEditingTag(tag);
    setEditingName(tag.name);
    setEditingDescription(tag.description || '');
  };

  const handleSaveEdit = () => {
    if (editingTag && editingName.trim()) {
      const updatedTags = tags.map((tag) =>
        tag.id === editingTag.id
          ? {
              ...tag,
              name: editingName.trim(),
              description: editingDescription.trim(),
            }
          : tag,
      );
      setTags(updatedTags);
      setEditingTag(null);
      setEditingName('');
      setEditingDescription('');
    }
  };

  const handleCancelEdit = () => {
    setEditingTag(null);
    setEditingName('');
    setEditingDescription('');
  };

  const handleSubmit = () => {
    // Pass both updated tags and deleted tag IDs
    // The parent will handle distinguishing between new tags (id === 0) and updated tags (id > 0)
    onUpdateTags(machine.id, tags, deletedTagIds);
    onOpenChange(false);
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setTags(machine.tags || []);
      setDeletedTagIds([]);
      setEditingTag(null);
      setEditingName('');
      setEditingDescription('');
    }
    onOpenChange(open);
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Edit Tags for {machine.name}</DialogTitle>
          <DialogDescription>
            Edit or remove existing tags for this machine.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          {tags.length > 0 ? (
            <div className="grid grid-cols-4 items-center gap-4">
              <Label className="text-right">Current Tags</Label>
              <div className="col-span-3 flex flex-wrap gap-2">
                {tags.map((tag, index) => (
                  <Badge
                    key={index}
                    variant="secondary"
                    className="flex items-center gap-1"
                  >
                    <Tag className="h-3 w-3" />
                    <div className="flex flex-col">
                      <span>{tag.name}</span>
                      {tag.description && (
                        <span className="text-xs opacity-70">
                          {tag.description}
                        </span>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => handleEditTag(tag)}
                      className="hover:text-primary ml-1"
                      aria-label={`Edit tag ${tag.name}`}
                      title={`Edit tag ${tag.name}`}
                    >
                      <Edit className="h-3 w-3" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleRemoveTag(tag)}
                      className="hover:text-destructive ml-1"
                      aria-label={`Remove tag ${tag.name}`}
                      title={`Remove tag ${tag.name}`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            </div>
          ) : (
            <div className="py-8 text-center">
              <Tag className="text-muted-foreground/50 mx-auto mb-4 h-12 w-12" />
              <p className="text-muted-foreground text-sm">
                This machine has no tags to edit.
              </p>
              <p className="text-muted-foreground mt-1 text-xs">
                Use &quot;Add Tags&quot; to create new tags for this machine.
              </p>
            </div>
          )}

          {/* Edit Tag Form */}
          {editingTag && (
            <div className="grid gap-4 rounded-lg border p-4">
              <div className="flex items-center justify-between">
                <Label>Editing Tag: {editingTag.name}</Label>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleCancelEdit}
                >
                  Cancel
                </Button>
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="edit-tag-name" className="text-right">
                  Name
                </Label>
                <div className="col-span-3">
                  <Input
                    id="edit-tag-name"
                    value={editingName}
                    onChange={(e) => setEditingName(e.target.value)}
                    placeholder="Enter tag name"
                  />
                </div>
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="edit-tag-desc" className="text-right">
                  Description
                </Label>
                <div className="col-span-3 flex gap-2">
                  <Input
                    id="edit-tag-desc"
                    value={editingDescription}
                    onChange={(e) => setEditingDescription(e.target.value)}
                    placeholder="Enter tag description (optional)"
                    className="flex-1"
                  />
                  <Button
                    type="button"
                    onClick={handleSaveEdit}
                    size="sm"
                    disabled={!editingName.trim()}
                  >
                    Save
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
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
