import Image from 'next/image';

import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';

const ImageViewer = ({
  imageUrl,
  onClose,
}: {
  imageUrl: string | null;
  onClose: () => void;
}) => {
  if (!imageUrl) return null;
  return (
    <Dialog open={!!imageUrl} onOpenChange={onClose}>
      <DialogTitle>Event Image</DialogTitle>
      <DialogContent className="flex max-h-[90vh] max-w-5xl flex-col items-center justify-center p-4">
        <div className="flex h-[80vh] w-fit items-center justify-center">
          <Image
            src={imageUrl}
            alt="Event image full view"
            width={1200}
            height={1200}
            className="h-full max-h-[80vh] w-auto rounded-lg object-contain"
          />
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ImageViewer;
