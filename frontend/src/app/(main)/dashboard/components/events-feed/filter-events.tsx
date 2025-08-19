'use client';

import React, { useMemo } from 'react';
import { Filter, X } from 'lucide-react';

import DateRangePicker from '@/components/common/date-range-picker';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';

import { MachineTag } from '@/lib/types/machine';

const severityLevels = [
  { id: 0, label: 'LOW', description: 'No person detected' },
  { id: 1, label: 'MEDIUM', description: 'Person detected' },
  { id: 2, label: 'HIGH', description: 'Person with suspicious item' },
  { id: 3, label: 'CRITICAL', description: 'Weapon detected' },
];

interface FilterEventsProps {
  search: string;
  setSearch: (search: string) => void;
  selectedTags: number[];
  selectedSeverities: number[];
  allTags: MachineTag[];
  onTagToggle: (tagId: number) => void;
  onSeverityToggle: (severityId: number) => void;
  onStartDateChange: (date: Date) => void;
  onEndDateChange: (date: Date) => void;
  onClearTagFilters: () => void;
  onClearSeverityFilters: () => void;
  onClearAllFilters: () => void;
}

export default function FilterEvents({
  search,
  setSearch,
  selectedTags,
  selectedSeverities,
  allTags,
  onTagToggle,
  onSeverityToggle,
  onStartDateChange,
  onEndDateChange,
  onClearTagFilters,
  onClearSeverityFilters,
  onClearAllFilters,
}: FilterEventsProps) {
  const getSelectedTagsWithNames = useMemo(() => {
    return selectedTags
      .map((tagId) => {
        const tag = allTags.find((tag) => tag.id === tagId);
        return tag ? { id: tagId, name: tag.name } : null;
      })
      .filter((tag): tag is { id: number; name: string } => tag !== null);
  }, [selectedTags, allTags]);

  const getSelectedSeveritiesWithLabels = useMemo(() => {
    return selectedSeverities
      .map((severityId) => {
        const severity = severityLevels.find((s) => s.id === severityId);
        return severity ? { id: severityId, label: severity.label } : null;
      })
      .filter(
        (severity): severity is { id: number; label: string } =>
          severity !== null,
      );
  }, [selectedSeverities]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Input
          className="h-10 flex-1"
          placeholder="Filter by Machine ID, Severity, Detected Object..."
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" className="h-10 px-3">
              <Filter className="mr-2 h-4 w-4" />
              Tags
              {selectedTags.length > 0 && (
                <span className="ml-2 rounded-full bg-blue-100 px-2 py-1 text-xs text-blue-800">
                  {selectedTags.length}
                </span>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="end">
            <DropdownMenuLabel>Filter by Tags</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {allTags.map((tag) => (
              <DropdownMenuCheckboxItem
                key={tag.id}
                checked={selectedTags.includes(tag.id)}
                onCheckedChange={() => onTagToggle(tag.id)}
              >
                {tag.name}
              </DropdownMenuCheckboxItem>
            ))}
            {selectedTags.length > 0 && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuCheckboxItem
                  onCheckedChange={onClearTagFilters}
                  className="text-red-600 focus:text-red-600"
                >
                  <X className="mr-2 h-4 w-4" />
                  Clear All
                </DropdownMenuCheckboxItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" className="h-10 px-3">
              <Filter className="mr-2 h-4 w-4" />
              Severity
              {selectedSeverities.length > 0 && (
                <span className="ml-2 rounded-full bg-orange-100 px-2 py-1 text-xs text-orange-800">
                  {selectedSeverities.length}
                </span>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="end">
            <DropdownMenuLabel>Filter by Severity</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {severityLevels.map((severity) => (
              <DropdownMenuCheckboxItem
                key={severity.id}
                checked={selectedSeverities.includes(severity.id)}
                onCheckedChange={() => onSeverityToggle(severity.id)}
              >
                <div>
                  <div className="font-medium">{severity.label}</div>
                  <div className="text-muted-foreground text-xs">
                    {severity.description}
                  </div>
                </div>
              </DropdownMenuCheckboxItem>
            ))}
            {selectedSeverities.length > 0 && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuCheckboxItem
                  onCheckedChange={onClearSeverityFilters}
                  className="text-red-600 focus:text-red-600"
                >
                  <X className="mr-2 h-4 w-4" />
                  Clear All
                </DropdownMenuCheckboxItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        <DateRangePicker
          setSelectStartDate={onStartDateChange}
          setSelectEndDate={onEndDateChange}
        />
      </div>

      {(selectedTags.length > 0 || selectedSeverities.length > 0) && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-muted-foreground text-sm">Active filters:</span>

          {getSelectedTagsWithNames.map((tag) => (
            <span
              key={`tag-${tag.id}`}
              className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-1 text-xs text-blue-800"
            >
              Tag: {tag.name}
              <button
                onClick={() => onTagToggle(tag.id)}
                className="ml-1 rounded-full p-0.5 hover:bg-blue-200"
                aria-label={`Remove ${tag.name} filter`}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}

          {getSelectedSeveritiesWithLabels.map((severity) => (
            <span
              key={`severity-${severity.id}`}
              className="inline-flex items-center gap-1 rounded-full bg-orange-100 px-2 py-1 text-xs text-orange-800"
            >
              Severity: {severity.label}
              <button
                onClick={() => onSeverityToggle(severity.id)}
                className="ml-1 rounded-full p-0.5 hover:bg-orange-200"
                aria-label={`Remove ${severity.label} severity filter`}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}

          <Button
            variant="ghost"
            size="sm"
            onClick={onClearAllFilters}
            className="h-6 px-2 text-xs"
          >
            Clear All
          </Button>
        </div>
      )}
    </div>
  );
}