import React from 'react';

import Image from 'next/image';

import { Dialog, DialogContent } from '@/components/ui/dialog';

export default function ImageViewerModal({
  modalImage,
  setModalImage,
}: {
  modalImage: { url: string; label: string };
  setModalImage: (image: { url: string; label: string } | null) => void;
}) {
  return (
    <Dialog open={!!modalImage} onOpenChange={() => setModalImage(null)}>
      <DialogContent className="flex max-h-[90vh] max-w-5xl flex-col items-center justify-center p-4">
        <div className="flex h-[80vh] w-fit items-center justify-center">
          <Image
            src={modalImage.url}
            alt="Event image full view"
            width={1200}
            height={1200}
            className="h-full max-h-[80vh] w-auto rounded-lg object-contain"
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
