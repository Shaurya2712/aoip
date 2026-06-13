// STATUS: COMPLETE
import { Check, Loader2, X } from 'lucide-react'
import { cn } from '@/lib/utils'

interface JobStatusChipProps {
  status: 'running' | 'success' | 'error' | string
}

export default function JobStatusChip({ status }: JobStatusChipProps) {
  const normalized = status.toLowerCase()

  if (normalized === 'running') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-100 px-2.5 py-1 text-xs font-medium text-blue-700">
        <Loader2 className="h-3 w-3 animate-spin" />
        Running
      </span>
    )
  }

  if (normalized === 'success') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-2.5 py-1 text-xs font-medium text-green-700">
        <Check className="h-3 w-3" />
        Success
      </span>
    )
  }

  if (normalized === 'error') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700">
        <X className="h-3 w-3" />
        Error
      </span>
    )
  }

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700'
      )}
    >
      {status}
    </span>
  )
}
