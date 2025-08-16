'use client';

import React, { useState, useEffect } from 'react';
import { X, Filter, Tag as TagIcon } from 'lucide-react';

import { MachineTag } from '@/lib/types/machine';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { getAllTags } from '../../devices/components/tag-api-utils';
import useOrganization from '@/hooks/use-organization';
import useToken from '@/hooks/use-token';

interface TagFilterProps {
  selectedTags: MachineTag[];
  onTagsChange: (tags: MachineTag[]) => void;
}

const TagFilter: React.FC<TagFilterProps> = ({ selectedTags, onTagsChange }) => {
  const { token } = useToken();
  const { organizationUid } = useOrganization();
  const [availableTags, setAvailableTags] = useState<MachineTag[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const loadTags = async () => {
      if (!organizationUid || !token) return;
      
      setLoading(true);
      try {
        const tags = await getAllTags(organizationUid, token);
        setAvailableTags(tags);
      } catch (error) {
        console.error('Failed to load tags:', error);
      } finally {
        setLoading(false);
      }
    };

    loadTags();
  }, [organizationUid, token]);

  const handleTagToggle = (tag: MachineTag) => {
    const isSelected = selectedTags.some(t => t.id === tag.id);
    
    if (isSelected) {
      onTagsChange(selectedTags.filter(t => t.id !== tag.id));
    } else {
      onTagsChange([...selectedTags, tag]);
    }
  };

  const handleClearAll = () => {
    onTagsChange([]);
  };

  const isTagSelected = (tag: MachineTag) => {
    return selectedTags.some(t => t.id === tag.id);
  };

  return (
    <div className="flex items-center gap-2">
      {/* Selected Tags Display */}
      {selectedTags.length > 0 && (
        <div className="flex items-center gap-1 mr-2">
          {selectedTags.map((tag) => (
            <Badge
              key={tag.id}
              variant="secondary"
              className="flex items-center gap-1 text-xs"
            >
              <TagIcon className="h-3 w-3" />
              {tag.name}
              <Button
                variant="ghost"
                size="sm"
                className="h-auto p-0 hover:bg-transparent"
                onClick={() => handleTagToggle(tag)}
              >
                <X className="h-3 w-3" />
              </Button>
            </Badge>
          ))}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearAll}
            className="text-xs h-6 px-2"
          >
            Clear All
          </Button>
        </div>
      )}

      {/* Filter Popover */}
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className={`flex items-center gap-2 ${selectedTags.length > 0 ? 'bg-primary/10 border-primary/30' : ''}`}
          >
            <Filter className="h-4 w-4" />
            Filter by Tags
            {selectedTags.length > 0 && (
              <Badge variant="secondary" className="ml-1 text-xs">
                {selectedTags.length}
              </Badge>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-80" align="end">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="font-medium">Filter by Tags</h4>
              {selectedTags.length > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleClearAll}
                  className="h-auto p-1 text-xs"
                >
                  Clear All
                </Button>
              )}
            </div>
            
            <Separator />
            
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="text-sm text-muted-foreground">Loading tags...</div>
              </div>
            ) : availableTags.length === 0 ? (
              <div className="text-center py-8">
                <div className="text-sm text-muted-foreground">No tags found</div>
              </div>
            ) : (
              <ScrollArea className="h-64">
                <div className="space-y-2">
                  {availableTags.map((tag) => {
                    const isSelected = isTagSelected(tag);
                    return (
                      <div
                        key={tag.id}
                        className={`flex items-center justify-between p-2 rounded-md cursor-pointer transition-colors ${
                          isSelected 
                            ? 'bg-primary/10 border border-primary/30' 
                            : 'hover:bg-accent'
                        }`}
                        onClick={() => handleTagToggle(tag)}
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <TagIcon className="h-3 w-3" />
                            <span className="font-medium text-sm">{tag.name}</span>
                          </div>
                          {tag.description && (
                            <p className="text-xs text-muted-foreground mt-1">
                              {tag.description}
                            </p>
                          )}
                        </div>
                        {isSelected && (
                          <div className="flex items-center ml-2">
                            <div className="w-4 h-4 bg-primary rounded-full flex items-center justify-center">
                              <div className="w-2 h-2 bg-white rounded-full" />
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </ScrollArea>
            )}
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
};

export default TagFilter;