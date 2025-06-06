'use client';

import React, { useEffect, useState } from 'react';
import { format } from 'date-fns';
import { CalendarIcon } from 'lucide-react';
import { DateRange } from 'react-day-picker';

import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';

import { cn } from '@/lib/utils';

export default function DateRangePicker({
  setSelectStartDate,
  setSelectEndDate,
}: {
  setSelectStartDate: (date: Date) => void;
  setSelectEndDate: (date: Date) => void;
}) {
  const [open, setOpen] = useState(false);
  const [date, setDate] = useState<DateRange | undefined>(undefined);

  useEffect(() => {
    if (date?.from && date?.to) {
      setSelectStartDate(date.from);
      setSelectEndDate(date.to);
    }
  }, [date, setSelectStartDate, setSelectEndDate]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id="date-picker-trigger"
          variant={'outline'}
          className={cn(
            'w-[260px] justify-start text-left font-normal',
            !date && 'text-muted-foreground',
          )}
        >
          <CalendarIcon className="mr-2 h-4 w-4" />
          {date?.from ? (
            date.to ? (
              <>
                {format(date.from, 'LLL dd, y')} -{' '}
                {format(date.to, 'LLL dd, y')}
              </>
            ) : (
              format(date.from, 'LLL dd, y')
            )
          ) : (
            <span>Pick a date range</span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          initialFocus
          mode="range"
          defaultMonth={date?.from}
          selected={date}
          onSelect={(selectedRange) => {
            setDate(selectedRange);
            // if (selectedRange?.from && selectedRange?.to) {
            //   setOpen(false);
            // }
          }}
          numberOfMonths={2}
        />
        <div className="flex justify-end p-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setSelectStartDate(
                new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
              );
              setSelectEndDate(new Date());
              setDate(undefined);
            }}
          >
            Clear
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
