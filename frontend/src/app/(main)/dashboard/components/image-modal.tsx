'use client';

import React from 'react';
import Image from 'next/image';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';

interface ImageModalProps {
  isOpen: boolean;
  onClose: () => void;
  imageUrl: string;
  imageAlt: string;
  title?: string;
  className?: string;
}

export default function ImageModal({
  isOpen,
  onClose,
  imageUrl,
  imageAlt,
  title,
  className,
}: ImageModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-[90vw] max-h-[90vh] p-4 flex flex-col">
        <DialogHeader className="pb-2 flex-shrink-0">
          <DialogTitle className="text-lg font-semibold">
            {title || 'Image Preview'}
          </DialogTitle>
        </DialogHeader>
        
        <div className="flex items-center justify-center flex-1 min-h-0">
          <Image
            src={imageUrl}
            alt={imageAlt}
            className={cn('h-[80vh] w-auto max-h-full max-w-full object-contain', className)}
            height={1000}
            width={1000}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
