// STATUS: COMPLETE
'use client'

import { useEffect, useMemo, useState } from 'react'
import { ArrowUpDown } from 'lucide-react'
import { createClient } from '@/lib/supabase'
import ProductConceptDialog from '@/components/ProductConceptDialog'
import ScoreBadge from '@/components/ScoreBadge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { Niche, Opportunity } from '@/lib/types'

type SortKey =
  | 'rank'
  | 'keyword'
  | 'niche'
  | 'final_score'
  | 'demand_score'
  | 'growth_score'
  | 'competition_penalty'

export default function OpportunitiesPage() {
  const supabase = createClient()
  const [opportunities, setOpportunities] = useState<Opportunity[]>([])
  const [niches, setNiches] = useState<Niche[]>([])
  const [loading, setLoading] = useState(true)
  const [nicheFilter, setNicheFilter] = useState('all')
  const [minScore, setMinScore] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('final_score')
  const [sortAsc, setSortAsc] = useState(false)
  const [selectedOpportunity, setSelectedOpportunity] = useState<Opportunity | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)

  useEffect(() => {
    async function loadData() {
      setLoading(true)

      const [{ data: nicheData }, { data: oppData }] = await Promise.all([
        supabase.from('niches').select('*').order('priority', { ascending: false }),
        supabase
          .from('opportunities')
          .select(
            '*, keywords(keyword, niche_id, niches(name)), product_concepts(*)'
          )
          .order('final_score', { ascending: false })
          .limit(200),
      ])

      setNiches((nicheData ?? []) as Niche[])
      setOpportunities((oppData ?? []) as Opportunity[])
      setLoading(false)
    }

    loadData()
  }, [supabase])

  const filtered = useMemo(() => {
    let rows = [...opportunities]

    if (nicheFilter !== 'all') {
      rows = rows.filter((row) => row.keywords?.niche_id === nicheFilter)
    }

    const min = parseFloat(minScore)
    if (!Number.isNaN(min)) {
      rows = rows.filter((row) => (row.final_score ?? 0) >= min)
    }

    rows.sort((a, b) => {
      let aVal: string | number = 0
      let bVal: string | number = 0

      switch (sortKey) {
        case 'keyword':
          aVal = a.keywords?.keyword ?? ''
          bVal = b.keywords?.keyword ?? ''
          break
        case 'niche':
          aVal = a.keywords?.niches?.name ?? ''
          bVal = b.keywords?.niches?.name ?? ''
          break
        case 'demand_score':
          aVal = a.demand_score ?? 0
          bVal = b.demand_score ?? 0
          break
        case 'growth_score':
          aVal = a.growth_score ?? 0
          bVal = b.growth_score ?? 0
          break
        case 'competition_penalty':
          aVal = a.competition_penalty ?? 0
          bVal = b.competition_penalty ?? 0
          break
        case 'final_score':
          aVal = a.final_score ?? 0
          bVal = b.final_score ?? 0
          break
        default:
          aVal = a.final_score ?? 0
          bVal = b.final_score ?? 0
      }

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal)
      }

      return sortAsc
        ? Number(aVal) - Number(bVal)
        : Number(bVal) - Number(aVal)
    })

    return rows
  }, [opportunities, nicheFilter, minScore, sortKey, sortAsc])

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortAsc(!sortAsc)
    } else {
      setSortKey(key)
      setSortAsc(false)
    }
  }

  function openRow(opportunity: Opportunity) {
    setSelectedOpportunity(opportunity)
    setDialogOpen(true)
  }

  function SortableHead({ label, column }: { label: string; column: SortKey }) {
    return (
      <TableHead>
        <button
          type="button"
          className="inline-flex items-center gap-1 font-medium hover:text-slate-900"
          onClick={() => toggleSort(column)}
        >
          {label}
          <ArrowUpDown className="h-3.5 w-3.5" />
        </button>
      </TableHead>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Opportunities</h1>
        <p className="mt-1 text-slate-600">
          Ranked app opportunities scored by AI analysis
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="space-y-2">
          <Label>Niche</Label>
          <Select
            value={nicheFilter}
            onValueChange={(value) => value && setNicheFilter(value)}
          >
            <SelectTrigger className="w-48">
              <SelectValue placeholder="All niches" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All niches</SelectItem>
              {niches.map((niche) => (
                <SelectItem key={niche.id} value={niche.id}>
                  {niche.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="min-score">Minimum score</Label>
          <Input
            id="min-score"
            type="number"
            placeholder="e.g. 200"
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
            className="w-40"
          />
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>#</TableHead>
              <SortableHead label="Keyword" column="keyword" />
              <SortableHead label="Niche" column="niche" />
              <SortableHead label="Final Score" column="final_score" />
              <SortableHead label="Demand" column="demand_score" />
              <SortableHead label="Growth" column="growth_score" />
              <SortableHead label="Competition Penalty" column="competition_penalty" />
              <TableHead>Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={8} className="py-10 text-center text-slate-500">
                  Loading opportunities...
                </TableCell>
              </TableRow>
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="py-10 text-center text-slate-500">
                  No opportunities match your filters.
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((opportunity, index) => (
                <TableRow
                  key={opportunity.id}
                  className="cursor-pointer hover:bg-slate-50"
                  onClick={() => openRow(opportunity)}
                >
                  <TableCell>{index + 1}</TableCell>
                  <TableCell className="font-medium">
                    {opportunity.keywords?.keyword ?? '—'}
                  </TableCell>
                  <TableCell>{opportunity.keywords?.niches?.name ?? '—'}</TableCell>
                  <TableCell>
                    <ScoreBadge score={opportunity.final_score ?? 0} size="sm" />
                  </TableCell>
                  <TableCell>{Math.round(opportunity.demand_score ?? 0)}</TableCell>
                  <TableCell>{Math.round(opportunity.growth_score ?? 0)}</TableCell>
                  <TableCell>{Math.round(opportunity.competition_penalty ?? 0)}</TableCell>
                  <TableCell>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        openRow(opportunity)
                      }}
                    >
                      View
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <ProductConceptDialog
        opportunity={selectedOpportunity}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </div>
  )
}
