'use client';

import React from 'react';
import { Tag, X } from 'lucide-react';

import { Badge } from '@/components/ui/badge';

import { MachineTag } from '@/lib/types/machine';

interface TagDisplayProps {
  tags?: MachineTag[];
  onDeleteTag?: (tagId: number) => void;
  showDeleteButtons?: boolean;
}

const TagDisplay: React.FC<TagDisplayProps> = ({
  tags,
  onDeleteTag,
  showDeleteButtons = false,
}) => {
  if (!tags || tags.length === 0) {
    return <span className="text-muted-foreground text-sm">No tags</span>;
  }

  return (
    <div className="flex flex-wrap gap-1">
      {tags.map((tag, index) => (
        <Badge
          key={tag.id || index}
          variant="secondary"
          className={`flex items-center gap-1 text-xs ${showDeleteButtons ? 'pr-1' : ''}`}
        >
          <Tag className="h-3 w-3" />
          <div className="flex flex-col">
            <span>{tag.name}</span>
            {tag.description && (
              <span className="text-xs opacity-70">{tag.description}</span>
            )}
          </div>
          {showDeleteButtons && onDeleteTag && (
            <button
              type="button"
              onClick={() => onDeleteTag(tag.id)}
              className="hover:text-destructive ml-1"
              aria-label={`Remove tag ${tag.name}`}
              title={`Remove tag ${tag.name}`}
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </Badge>
      ))}
    </div>
  );
};

export default TagDisplay;
