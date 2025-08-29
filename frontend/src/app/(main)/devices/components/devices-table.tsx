'use client';

import React, { useState } from 'react';
import useOrganization from '@/hooks/use-organization';
import useToken from '@/hooks/use-token';
import { Camera, Clock, Eye, Network, Route } from 'lucide-react';
import { useRouter } from 'next/navigation';

import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

import { Machine, MachineTag } from '@/lib/types/machine';

import AddTagsModal from './add-tags-modal';
import DevicesTableRow from './devices-table-row';
import EditTagsModal from './edit-tags-modal';
import { createOrUpdateTag, deleteTag } from './tag-api-utils';

interface DevicesTableProps {
  machines: Machine[];
}

const DevicesTable: React.FC<DevicesTableProps> = ({ machines }) => {
  const router = useRouter();
  const { token } = useToken();
  const { organizationUid } = useOrganization();
  const [addTagsModalOpen, setAddTagsModalOpen] = useState<{
    machine: Machine;
    open: boolean;
  } | null>(null);
  const [editTagsModalOpen, setEditTagsModalOpen] = useState<{
    machine: Machine;
    open: boolean;
  } | null>(null);

  const handleDeleteTag = async (machineId: number, tagId: number) => {
    if (!organizationUid || !token) {
      console.error('Organization UID or token not found');
      return;
    }

    try {
      await deleteTag(
        machineId,
        {
          organization_uid: organizationUid,
          tag_id: tagId,
          delete_completely: false,
        },
        token,
      );

      router.refresh();
    } catch (error) {
      console.error('Failed to delete tag:', error);
    }
  };

  const handleUpdateTags = async (
    machineId: number,
    updatedTags: MachineTag[],
    deletedTagIds: number[],
  ) => {
    if (!organizationUid || !token) {
      console.error('Organization UID or token not found');
      return;
    }

    try {
      // Delete removed tags
      for (const tagId of deletedTagIds) {
        await deleteTag(
          machineId,
          {
            organization_uid: organizationUid,
            tag_id: tagId,
            delete_completely: false,
          },
          token,
        );
      }

      // Get original tags for comparison
      const originalTags = machines.find((m) => m.id === machineId)?.tags || [];

      // Update existing tags that have changed
      for (const tag of updatedTags) {
        const originalTag = originalTags.find((ot) => ot.id === tag.id);
        if (
          originalTag &&
          (originalTag.name !== tag.name ||
            originalTag.description !== tag.description)
        ) {
          // Tag has been modified, update it
          await createOrUpdateTag(
            machineId,
            {
              organization_uid: organizationUid,
              name: tag.name,
              description: tag.description,
              tag_id: tag.id, // Include tag_id to indicate this is an update
            },
            token,
          );
        }
      }

      // Refresh machines data
      router.refresh();
    } catch (error) {
      console.error('Failed to update tags:', error);
    }
  };

  const handleOpenAddTagsModal = (machine: Machine) => {
    setAddTagsModalOpen({ machine, open: true });
  };

  const handleOpenEditTagsModal = (machine: Machine) => {
    setEditTagsModalOpen({ machine, open: true });
  };

  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow className="border-b border-gray-200 bg-gray-50/50">
            <TableHead className="text-xs font-semibold tracking-wider text-gray-700 uppercase">
              ID
            </TableHead>
            <TableHead className="text-xs font-semibold tracking-wider text-gray-700 uppercase">
              Name
            </TableHead>
            <TableHead className="text-xs font-semibold tracking-wider text-gray-700 uppercase">
              Location
            </TableHead>
            <TableHead className="text-xs font-semibold tracking-wider text-gray-700 uppercase">
              Tags
            </TableHead>
            <TableHead className="text-xs font-semibold tracking-wider text-gray-700 uppercase">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-gray-400" />
                Uptime
              </div>
            </TableHead>
            <TableHead className="text-xs font-semibold tracking-wider text-gray-700 uppercase">
              <div className="flex items-center gap-2">
                <Camera className="h-4 w-4 text-gray-400" />
                Photos Taken
              </div>
            </TableHead>
            <TableHead className="text-xs font-semibold tracking-wider text-gray-700 uppercase">
              <div className="flex items-center gap-2">
                <Eye className="h-4 w-4 text-gray-400" />
                Events Seen
              </div>
            </TableHead>
            <TableHead className="text-xs font-semibold tracking-wider text-gray-700 uppercase">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-gray-400" />
                GPS Staleness
              </div>
            </TableHead>
            <TableHead className="text-xs font-semibold tracking-wider text-gray-700 uppercase">
              <div className="flex items-center gap-2">
                <Network className="h-4 w-4 text-gray-400" />
                Neighbours
              </div>
            </TableHead>
            <TableHead className="text-xs font-semibold tracking-wider text-gray-700 uppercase">
              <div className="flex items-center gap-2">
                <Route className="h-4 w-4 text-gray-400" />
                Shortest Path
              </div>
            </TableHead>
            <TableHead className="text-xs font-semibold text-gray-700 uppercase">
              Actions
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {machines.map((machine) => (
            <DevicesTableRow
              key={machine.id}
              machine={machine}
              onDeleteTag={handleDeleteTag}
              onAddTags={handleOpenAddTagsModal}
              onEditTags={handleOpenEditTagsModal}
            />
          ))}
        </TableBody>
      </Table>

      {/* Add Tags Modal */}
      {addTagsModalOpen && (
        <AddTagsModal
          machine={addTagsModalOpen.machine}
          isOpen={addTagsModalOpen.open}
          onOpenChange={(open) =>
            setAddTagsModalOpen(open ? addTagsModalOpen : null)
          }
          onTagsAdded={() => {
            // Refresh machines data to show updated tags
            router.refresh();
          }}
        />
      )}

      {/* Edit Tags Modal */}
      {editTagsModalOpen && (
        <EditTagsModal
          machine={editTagsModalOpen.machine}
          onUpdateTags={handleUpdateTags}
          isOpen={editTagsModalOpen.open}
          onOpenChange={(open) =>
            setEditTagsModalOpen(open ? editTagsModalOpen : null)
          }
        />
      )}
    </div>
  );
};

export default DevicesTable;
