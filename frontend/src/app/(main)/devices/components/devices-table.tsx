'use client';

import React, { useState, useEffect } from 'react';

import { Machine, MachineTag } from '@/lib/types/machine';
import useOrganization from '@/hooks/use-organization';
import useToken from '@/hooks/use-token';
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { 
  getMachineTags, 
  createOrUpdateTag, 
  deleteTag
} from './tag-api-utils';
import AddTagsModal from './add-tags-modal';
import EditTagsModal from './edit-tags-modal';
import DevicesTableRow from './devices-table-row';

interface DevicesTableProps {
  machines: Machine[];
}

const DevicesTable: React.FC<DevicesTableProps> = ({ machines }) => {
  const { organizationUid } = useOrganization();
  const { token } = useToken();
  const [machinesData, setMachinesData] = useState<Machine[]>(machines);
  const [addTagsModalOpen, setAddTagsModalOpen] = useState<{ machine: Machine; open: boolean } | null>(null);
  const [editTagsModalOpen, setEditTagsModalOpen] = useState<{ machine: Machine; open: boolean } | null>(null);

  useEffect(() => {
    const loadMachineTags = async () => {
      if (!organizationUid || !token) return;
      
      const updatedMachines = await Promise.all(
        machines.map(async (machine) => {
          const tags = await getMachineTags(machine.id, organizationUid, token);
          return { ...machine, tags };
        })
      );
      
      setMachinesData(updatedMachines);
    };

    loadMachineTags();
  }, [machines, organizationUid, token]);

  const handleAddTags = async (machineId: number, newTags: { name: string; description?: string }[]) => {
    if (!organizationUid || !token) {
      console.error('Organization UID or token not found');
      return;
    }

    try {
      const addedTags: MachineTag[] = [];
      
      for (const tag of newTags) {
        const result = await createOrUpdateTag(machineId, {
          organization_uid: organizationUid,
          name: tag.name,
          description: tag.description,
        }, token);
        
        if (result) {
          addedTags.push(result);
        }
      }
      
      if (addedTags.length > 0) {
        setMachinesData(prev => 
          prev.map(machine => 
            machine.id === machineId 
              ? { ...machine, tags: [...(machine.tags || []), ...addedTags] }
              : machine
          )
        );
      }
    } catch (error) {
      console.error('Failed to add tags:', error);
    }
  };

  const handleDeleteTag = async (machineId: number, tagId: number) => {
    if (!organizationUid || !token) {
      console.error('Organization UID or token not found');
      return;
    }

    try {
      const success = await deleteTag(machineId, {
        organization_uid: organizationUid,
        tag_id: tagId,
        delete_completely: false,
      }, token);

      if (success) {
        setMachinesData(prev => 
          prev.map(machine => 
            machine.id === machineId 
              ? { ...machine, tags: machine.tags?.filter(tag => tag.id !== tagId) || [] }
              : machine
          )
        );
      }
    } catch (error) {
      console.error('Failed to delete tag:', error);
    }
  };

  const handleUpdateTags = async (machineId: number, updatedTags: MachineTag[], deletedTagIds: number[]) => {
    if (!organizationUid || !token) {
      console.error('Organization UID or token not found');
      return;
    }

    try {
      // Delete removed tags
      for (const tagId of deletedTagIds) {
        await deleteTag(machineId, {
          organization_uid: organizationUid,
          tag_id: tagId,
          delete_completely: false,
        }, token);
      }

      // Create new tags (those with id: 0)
      const newTags = updatedTags.filter(tag => tag.id === 0);
      const finalTags: MachineTag[] = [...updatedTags.filter(tag => tag.id > 0)];

      for (const tag of newTags) {
        const result = await createOrUpdateTag(machineId, {
          organization_uid: organizationUid,
          name: tag.name,
          description: tag.description,
        }, token);
        
        if (result) {
          finalTags.push(result);
        }
      }
      
      // Update local state with final tags
      setMachinesData(prev => 
        prev.map(machine => 
          machine.id === machineId 
            ? { ...machine, tags: finalTags }
            : machine
        )
      );
      
      console.log(`Updated tags for machine ${machineId}`);
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
          {machinesData.map((machine) => (
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
          onAddTags={handleAddTags}
          isOpen={addTagsModalOpen.open}
          onOpenChange={(open) => setAddTagsModalOpen(open ? addTagsModalOpen : null)}
        />
      )}

      {/* Edit Tags Modal */}
      {editTagsModalOpen && (
        <EditTagsModal
          machine={editTagsModalOpen.machine}
          onUpdateTags={handleUpdateTags}
          isOpen={editTagsModalOpen.open}
          onOpenChange={(open) => setEditTagsModalOpen(open ? editTagsModalOpen : null)}
        />
      )}
    </div>
  );
};

export default DevicesTable;