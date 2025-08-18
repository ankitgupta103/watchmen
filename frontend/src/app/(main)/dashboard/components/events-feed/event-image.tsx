'use client';

import React, { useEffect, useState } from 'react';
import useToken from '@/hooks/use-token';
import Image from 'next/image';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

import { cn } from '@/lib/utils';
import { getPresignedUrl } from '@/lib/utils/presigned-url';

export default function EventImage({
  className,
  path,
}: {
  className: string;
  path: string;
}) {
  const { token } = useToken();
  const [presignedUrl, setPresignedUrl] = useState<string | null>(null);
  const [enlargeImage, setEnlargeImage] = useState<boolean>(false);

  useEffect(() => {
    getPresignedUrl(path, token).then((url) => {
      setPresignedUrl(url);
    });
  }, [path, token]);

  return (
    <>
      <Dialog open={enlargeImage} onOpenChange={setEnlargeImage}>
        <DialogContent className="grid place-items-center space-y-4">
          <DialogHeader className="w-full">
            <DialogTitle>Event Image</DialogTitle>
          </DialogHeader>
          <Image
            src={presignedUrl || ''}
            alt={'Event Image Enlarged'}
            width={1920}
            height={1080}
            className={cn('h-[80vh] w-auto rounded-md object-contain')}
          />
        </DialogContent>
      </Dialog>

      {presignedUrl ? (
        <Image
          src={presignedUrl}
          alt={'Event Image'}
          width={1920}
          height={1080}
          className={cn(
            'h-full w-auto cursor-pointer rounded-md object-contain',
            className,
          )}
          onClick={() => setEnlargeImage(true)}
        />
      ) : (
        <div className="bg-muted-foreground h-full w-auto animate-pulse rounded-md object-contain" />
      )}
    </>
  );
}
