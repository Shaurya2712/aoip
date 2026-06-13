// STATUS: COMPLETE
'use client'

import { useCallback, useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { toast } from 'sonner'
import { createClient } from '@/lib/supabase'
import SeedKeywordImporter from '@/components/SeedKeywordImporter'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { BACKEND_URL } from '@/lib/utils'
import type { Niche } from '@/lib/types'

interface NicheWithCount extends Niche {
  keywordCount: number
}

export default function NichesPage() {
  const supabase = createClient()
  const [niches, setNiches] = useState<NicheWithCount[]>([])
  const [loading, setLoading] = useState(true)
  const [addOpen, setAddOpen] = useState(false)
  const [keywordsOpenFor, setKeywordsOpenFor] = useState<string | null>(null)
  const [newName, setNewName] = useState('')
  const [newPriority, setNewPriority] = useState('5')
  const [creating, setCreating] = useState(false)

  const loadNiches = useCallback(async () => {
    setLoading(true)

    const [{ data: nicheData }, { data: keywordData }] = await Promise.all([
      supabase.from('niches').select('*').order('priority', { ascending: false }),
      supabase.from('seed_keywords').select('niche_id'),
    ])

    const counts = (keywordData ?? []).reduce<Record<string, number>>(
      (acc: Record<string, number>, row: { niche_id: string | null }) => {
        if (row.niche_id) {
          acc[row.niche_id] = (acc[row.niche_id] ?? 0) + 1
        }
        return acc
      },
      {}
    )

    setNiches(
      ((nicheData ?? []) as Niche[]).map((niche) => ({
        ...niche,
        keywordCount: counts[niche.id] ?? 0,
      }))
    )
    setLoading(false)
  }, [supabase])

  useEffect(() => {
    loadNiches()
  }, [loadNiches])

  async function createNiche() {
    if (!newName.trim()) {
      toast.error('Enter a niche name')
      return
    }

    setCreating(true)
    try {
      const response = await fetch(`${BACKEND_URL}/api/niches/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newName.trim(),
          priority: parseInt(newPriority, 10) || 5,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to create niche')
      }

      toast.success(`Niche "${newName.trim()}" created`)
      setNewName('')
      setNewPriority('5')
      setAddOpen(false)
      loadNiches()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Create failed')
    } finally {
      setCreating(false)
    }
  }

  async function updateNiche(id: string, updates: Partial<Niche>) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/niches/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })

      if (!response.ok) {
        throw new Error('Failed to update niche')
      }

      setNiches((prev) =>
        prev.map((niche) => (niche.id === id ? { ...niche, ...updates } : niche))
      )
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Update failed')
      loadNiches()
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Niches</h1>
          <p className="mt-1 text-slate-600">
            Manage market niches and seed keywords
          </p>
        </div>

        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <Button onClick={() => setAddOpen(true)}>
            <Plus className="h-4 w-4" />
            Add Niche
          </Button>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Niche</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="niche-name">Name</Label>
                <Input
                  id="niche-name"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Finance"
                />
              </div>
              <div className="space-y-2">
                <Label>Priority</Label>
                <Select
                  value={newPriority}
                  onValueChange={(value) => value && setNewPriority(value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Array.from({ length: 10 }, (_, i) => i + 1).map((value) => (
                      <SelectItem key={value} value={String(value)}>
                        {value}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Button onClick={createNiche} disabled={creating}>
                {creating ? 'Creating...' : 'Create Niche'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {loading ? (
        <p className="text-slate-500">Loading niches...</p>
      ) : niches.length === 0 ? (
        <Card className="border-dashed border-slate-300 bg-white">
          <CardContent className="py-10 text-center text-slate-500">
            No niches yet. Add your first niche to get started.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {niches.map((niche) => (
            <Card key={niche.id} className="border-slate-200 bg-white shadow-sm">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-3">
                  <CardTitle className="text-lg">{niche.name}</CardTitle>
                  <Badge variant="secondary">{niche.keywordCount} keywords</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-6 pb-6">
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <Label>Priority</Label>
                    <span className="font-medium">{niche.priority}</span>
                  </div>
                  <Slider
                    value={[niche.priority]}
                    min={1}
                    max={10}
                    step={1}
                    onValueChange={(value) => {
                      const next = Array.isArray(value) ? value[0] : value
                      if (typeof next === 'number') {
                        updateNiche(niche.id, { priority: next })
                      }
                    }}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <Label htmlFor={`enabled-${niche.id}`}>Enabled</Label>
                  <Switch
                    id={`enabled-${niche.id}`}
                    checked={niche.enabled}
                    onCheckedChange={(enabled) => updateNiche(niche.id, { enabled })}
                  />
                </div>

                <Dialog
                  open={keywordsOpenFor === niche.id}
                  onOpenChange={(open) =>
                    setKeywordsOpenFor(open ? niche.id : null)
                  }
                >
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => setKeywordsOpenFor(niche.id)}
                  >
                    Add Keywords
                  </Button>
                  <DialogContent className="max-w-lg">
                    <DialogHeader>
                      <DialogTitle>Add Keywords — {niche.name}</DialogTitle>
                    </DialogHeader>
                    <SeedKeywordImporter
                      nicheId={niche.id}
                      onSuccess={() => {
                        loadNiches()
                        setKeywordsOpenFor(null)
                      }}
                    />
                  </DialogContent>
                </Dialog>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
