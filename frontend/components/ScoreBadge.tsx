// STATUS: COMPLETE
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface ScoreBadgeProps {
  score: number
  size?: 'sm' | 'md'
}

export default function ScoreBadge({ score, size = 'md' }: ScoreBadgeProps) {
  let label = 'Weak'
  let className = 'bg-slate-100 text-slate-700 border-slate-200'

  if (score >= 300) {
    label = 'Strong'
    className = 'bg-green-100 text-green-700 border-green-200'
  } else if (score >= 200) {
    label = 'Good'
    className = 'bg-amber-100 text-amber-700 border-amber-200'
  }

  return (
    <Badge
      variant="outline"
      className={cn(
        'font-semibold',
        className,
        size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-2.5 py-1'
      )}
    >
      {Math.round(score)} · {label}
    </Badge>
  )
}
