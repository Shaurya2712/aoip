// STATUS: COMPLETE
'use client'

import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { BACKEND_URL } from '@/lib/utils'

interface SeedKeywordImporterProps {
  nicheId: string
  onSuccess: () => void
}

export default function SeedKeywordImporter({ nicheId, onSuccess }: SeedKeywordImporterProps) {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [successCount, setSuccessCount] = useState<number | null>(null)

  const keywords = useMemo(
    () =>
      text
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean),
    [text]
  )

  const displayCount = Math.min(keywords.length, 1000)
  const overLimit = keywords.length > 1000

  async function handleSubmit() {
    if (!keywords.length) {
      toast.error('Enter at least one keyword')
      return
    }

    setLoading(true)
    setSuccessCount(null)

    try {
      const response = await fetch(`${BACKEND_URL}/api/niches/${nicheId}/seeds`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keywords: keywords.slice(0, 1000) }),
      })

      if (!response.ok) {
        const error = await response.json().catch(() => ({}))
        throw new Error(error.detail || 'Failed to import keywords')
      }

      const result = await response.json()
      const imported = result.inserted ?? displayCount
      setSuccessCount(imported)
      toast.success(`✓ ${imported} keywords imported`)
      setText('')
      onSuccess()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Import failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-3">
      <Textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Enter one keyword per line (max 1,000)"
        rows={10}
        className="font-mono text-sm"
      />

      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-600">{displayCount} keywords</span>
        {overLimit && (
          <span className="text-amber-600">
            Limit is 1,000 — extra lines will be ignored
          </span>
        )}
      </div>

      {successCount != null && (
        <p className="text-sm font-medium text-green-600">
          ✓ {successCount} keywords imported
        </p>
      )}

      <Button onClick={handleSubmit} disabled={loading || !keywords.length}>
        {loading ? 'Importing...' : 'Import Keywords'}
      </Button>
    </div>
  )
}
