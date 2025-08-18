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
      <DialogContent className="flex max-h-[90vh] max-w-[90vw] flex-col p-4">
        <DialogHeader className="flex-shrink-0 pb-2">
          <DialogTitle className="text-lg font-semibold">
            {title || 'Image Preview'}
          </DialogTitle>
        </DialogHeader>

        <div className="flex min-h-0 flex-1 items-center justify-center">
          <Image
            src={imageUrl}
            alt={imageAlt}
            className={cn(
              'h-[80vh] max-h-full w-auto max-w-full object-contain',
              className,
            )}
            height={1000}
            width={1000}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}