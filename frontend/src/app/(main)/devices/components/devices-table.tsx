'use client';

import React, { useState } from 'react';
import useOrganization from '@/hooks/use-organization';
import useToken from '@/hooks/use-token';

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
  onRefreshMachines?: () => Promise<void>;
}

const DevicesTable: React.FC<DevicesTableProps> = ({
  machines,
  onRefreshMachines,
}) => {
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
      const success = await deleteTag(
        machineId,
        {
          organization_uid: organizationUid,
          tag_id: tagId,
          delete_completely: false,
        },
        token,
      );

      if (success && onRefreshMachines) {
        await onRefreshMachines();
      }
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

      // Create new tags (those with id: 0)
      const newTags = updatedTags.filter((tag) => tag.id === 0);
      const finalTags: MachineTag[] = [
        ...updatedTags.filter((tag) => tag.id > 0),
      ];

      for (const tag of newTags) {
        const result = await createOrUpdateTag(
          machineId,
          {
            organization_uid: organizationUid,
            name: tag.name,
            description: tag.description,
          },
          token,
        );

        if (result) {
          finalTags.push(result);
        }
      }

      // Refresh machines data
      if (onRefreshMachines) {
        await onRefreshMachines();
      }
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
    <div className="w-full">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Connection</TableHead>
            <TableHead>Location</TableHead>
            <TableHead>Tags</TableHead>
            <TableHead>Actions</TableHead>
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
            if (onRefreshMachines) {
              onRefreshMachines();
            }
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
