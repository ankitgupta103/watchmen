'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Machine, MachineTag } from '@/lib/types/machine';
import useOrganization from '@/hooks/use-organization';
import useToken from '@/hooks/use-token';
import { getAllTags, createOrUpdateTag, addExistingTagToMachine } from './tag-api-utils';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Loader2, Plus, X } from 'lucide-react';

interface AddTagsModalProps {
  machine: Machine;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onTagsAdded?: () => void;
}

const AddTagsModal: React.FC<AddTagsModalProps> = ({
  machine,
  isOpen,
  onOpenChange,
  onTagsAdded,
}) => {
  const { token } = useToken();
  const { organizationUid } = useOrganization();
  const [availableTags, setAvailableTags] = useState<MachineTag[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTags, setSelectedTags] = useState<MachineTag[]>([]);
  const [newTagName, setNewTagName] = useState('');
  const [newTagDescription, setNewTagDescription] = useState('');
  const [creatingTag, setCreatingTag] = useState(false);

  const loadAvailableTags = useCallback(async () => {
    if (!organizationUid || !token) return;
    
    setLoading(true);
    try {
      const tags = await getAllTags(organizationUid, token);
      // Show all available tags - don't filter out existing ones
      setAvailableTags(tags);
    } catch (error) {
      console.error('Failed to load available tags:', error);
    } finally {
      setLoading(false);
    }
  }, [organizationUid, token]);

  // Load available tags when modal opens
  useEffect(() => {
    if (isOpen && organizationUid && token) {
      loadAvailableTags();
    }
  }, [isOpen, organizationUid, token, loadAvailableTags]);

  const handleSelectTag = (tag: MachineTag) => {
    // Check if tag is already on the machine
    const isAlreadyOnMachine = machine.tags?.some(machineTag => machineTag.id === tag.id);
    
    if (isAlreadyOnMachine) {
      // Don't allow selecting tags that are already on the machine
      return;
    }
    
    if (!selectedTags.find(t => t.id === tag.id)) {
      setSelectedTags([...selectedTags, tag]);
    }
  };

  const handleDeselectTag = (tagId: number) => {
    setSelectedTags(selectedTags.filter(tag => tag.id !== tagId));
  };

  const handleCreateNewTag = async () => {
    if (!newTagName.trim() || !organizationUid || !token) return;
    
    setCreatingTag(true);
    try {
      const newTag = await createOrUpdateTag(machine.id, {
        organization_uid: organizationUid,
        name: newTagName.trim(),
        description: newTagDescription.trim() || undefined,
      }, token);
      
      if (newTag) {
        // Add the newly created tag to selected tags
        setSelectedTags([...selectedTags, newTag]);
        setNewTagName('');
        setNewTagDescription('');
        // Refresh available tags
        await loadAvailableTags();
      }
    } catch (error) {
      console.error('Failed to create new tag:', error);
    } finally {
      setCreatingTag(false);
    }
  };

  const handleAddSelectedTags = async () => {
    if (selectedTags.length === 0) return;
    
    setLoading(true);
    try {
      // Add existing tags to the machine
      for (const tag of selectedTags) {
        if (tag.id > 0) { // Existing tag
          await addExistingTagToMachine(machine.id, {
            organization_uid: organizationUid!,
            tag_id: tag.id,
          }, token!);
        }
      }
      
      // Close modal and reset state
      onOpenChange(false);
      setSelectedTags([]);
      setNewTagName('');
      setNewTagDescription('');
      
      // Notify parent component that tags were added
      if (onTagsAdded) {
        onTagsAdded();
      }
    } catch (error) {
      console.error('Failed to add tags:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    onOpenChange(false);
    setSelectedTags([]);
    setNewTagName('');
    setNewTagDescription('');
  };

  const isTagAlreadyOnMachine = (tag: MachineTag) => {
    return machine.tags?.some(machineTag => machineTag.id === tag.id) || false;
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle>Add Tags to {machine.name}</DialogTitle>
          <DialogDescription>
            Select from existing tags or create new ones for this machine.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="existing" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="existing">Select Existing Tags</TabsTrigger>
            <TabsTrigger value="create">Create New Tag</TabsTrigger>
          </TabsList>

          <TabsContent value="existing" className="space-y-4">
            <div className="space-y-3">
              <div>
                <Label>Available Tags</Label>
                <p className="text-sm text-muted-foreground">
                  Select from existing tags in your organization. Tags already on this machine are disabled.
                </p>
              </div>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin" />
                  <span className="ml-2">Loading tags...</span>
                </div>
              ) : availableTags.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No tags found in your organization. Create a new tag to get started.
                </div>
              ) : (
                <ScrollArea className="h-48 w-full rounded-md border p-4">
                  <div className="space-y-2">
                    {availableTags.map((tag) => {
                      const isAlreadyOnMachine = isTagAlreadyOnMachine(tag);
                      return (
                        <div
                          key={tag.id}
                          className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer ${
                            isAlreadyOnMachine 
                              ? 'bg-muted opacity-60 cursor-not-allowed' 
                              : 'hover:bg-accent'
                          }`}
                          onClick={() => !isAlreadyOnMachine && handleSelectTag(tag)}
                        >
                          <div className="flex-1">
                            <div className="font-medium">{tag.name}</div>
                            {tag.description && (
                              <div className="text-sm text-muted-foreground">{tag.description}</div>
                            )}
                            {isAlreadyOnMachine && (
                              <div className="text-xs text-muted-foreground mt-1">
                                Already on this machine
                              </div>
                            )}
                          </div>
                          {!isAlreadyOnMachine && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSelectTag(tag);
                              }}
                            >
                              <Plus className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </ScrollArea>
              )}
            </div>

            {selectedTags.length > 0 && (
              <div className="space-y-3">
                <Label>Selected Tags</Label>
                <div className="flex flex-wrap gap-2">
                  {selectedTags.map((tag) => (
                    <Badge key={tag.id} variant="secondary" className="flex items-center gap-1">
                      {tag.name}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-auto p-0 hover:bg-transparent"
                        onClick={() => handleDeselectTag(tag.id)}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="create" className="space-y-4">
            <div className="space-y-3">
              <div>
                <Label htmlFor="tag-name">Tag Name</Label>
                <Input
                  id="tag-name"
                  placeholder="Enter tag name"
                  value={newTagName}
                  onChange={(e) => setNewTagName(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="tag-description">Description (Optional)</Label>
                <Textarea
                  id="tag-description"
                  placeholder="Enter tag description"
                  value={newTagDescription}
                  onChange={(e) => setNewTagDescription(e.target.value)}
                  rows={3}
                />
              </div>
              <Button
                onClick={handleCreateNewTag}
                disabled={!newTagName.trim() || creatingTag}
                className="w-full"
              >
                {creatingTag ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus className="mr-2 h-4 w-4" />
                    Create Tag
                  </>
                )}
              </Button>
            </div>
          </TabsContent>
        </Tabs>

        <Separator />

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            onClick={handleAddSelectedTags}
            disabled={selectedTags.length === 0 || loading}
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Adding Tags...
              </>
            ) : (
              `Add ${selectedTags.length} Tag${selectedTags.length !== 1 ? 's' : ''}`
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default AddTagsModal;