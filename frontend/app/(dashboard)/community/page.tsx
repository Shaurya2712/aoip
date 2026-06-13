// STATUS: COMPLETE
'use client'

import { useEffect, useMemo, useState } from 'react'
import { ExternalLink } from 'lucide-react'
import { createClient } from '@/lib/supabase'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { CommunityInsight, CommunityPost, Niche } from '@/lib/types'

const TAB_TYPES = {
  pain: 'pain_point',
  features: 'feature_request',
  trends: 'trend',
} as const

export default function CommunityPage() {
  const supabase = createClient()
  const [niches, setNiches] = useState<Niche[]>([])
  const [insights, setInsights] = useState<CommunityInsight[]>([])
  const [posts, setPosts] = useState<CommunityPost[]>([])
  const [nicheFilter, setNicheFilter] = useState('all')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadNiches() {
      const { data } = await supabase.from('niches').select('*').order('name')
      setNiches((data ?? []) as Niche[])
    }

    loadNiches()
  }, [supabase])

  useEffect(() => {
    async function loadData() {
      setLoading(true)

      let insightsQuery = supabase
        .from('community_insights')
        .select('*, niches(name)')
        .order('confidence', { ascending: false })
        .limit(200)

      let postsQuery = supabase
        .from('community_posts')
        .select('*')
        .order('upvotes', { ascending: false })
        .limit(50)

      if (nicheFilter !== 'all') {
        insightsQuery = insightsQuery.eq('niche_id', nicheFilter)
        postsQuery = postsQuery.eq('niche_id', nicheFilter)
      }

      const [{ data: insightData }, { data: postData }] = await Promise.all([
        insightsQuery,
        postsQuery,
      ])

      setInsights((insightData ?? []) as CommunityInsight[])
      setPosts((postData ?? []) as CommunityPost[])
      setLoading(false)
    }

    loadData()
  }, [supabase, nicheFilter])

  const grouped = useMemo(
    () => ({
      pain: insights.filter((item) => item.type === TAB_TYPES.pain),
      features: insights.filter((item) => item.type === TAB_TYPES.features),
      trends: insights.filter((item) => item.type === TAB_TYPES.trends),
    }),
    [insights]
  )

  function InsightList({ items }: { items: CommunityInsight[] }) {
    if (loading) {
      return <p className="text-sm text-slate-500">Loading insights...</p>
    }

    if (items.length === 0) {
      return (
        <p className="text-sm text-slate-500">
          No insights in this category yet.
        </p>
      )
    }

    return (
      <div className="grid gap-3">
        {items.map((item) => (
          <Card key={item.id} className="border-slate-200 bg-white shadow-sm">
            <CardContent className="p-4">
              <p className="text-sm text-slate-800">{item.text}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge variant="outline">
                  {Math.round((item.confidence ?? 0) * 100)}% confidence
                </Badge>
                <Badge variant="secondary">
                  {item.niches?.name ?? 'Unknown niche'}
                </Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Community</h1>
        <p className="mt-1 text-slate-600">
          Reddit-sourced pain points, requests, and emerging trends
        </p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="space-y-2">
          <Label>Niche filter</Label>
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
      </div>

      <Tabs defaultValue="pain">
        <TabsList>
          <TabsTrigger value="pain">Pain Points</TabsTrigger>
          <TabsTrigger value="features">Feature Requests</TabsTrigger>
          <TabsTrigger value="trends">Emerging Trends</TabsTrigger>
        </TabsList>

        <TabsContent value="pain" className="mt-4">
          <InsightList items={grouped.pain} />
        </TabsContent>
        <TabsContent value="features" className="mt-4">
          <InsightList items={grouped.features} />
        </TabsContent>
        <TabsContent value="trends" className="mt-4">
          <InsightList items={grouped.trends} />
        </TabsContent>
      </Tabs>

      <section>
        <h2 className="mb-4 text-xl font-semibold text-slate-900">Recent Reddit Posts</h2>
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Subreddit</TableHead>
                <TableHead>Upvotes</TableHead>
                <TableHead>Link</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={4} className="py-10 text-center text-slate-500">
                    Loading posts...
                  </TableCell>
                </TableRow>
              ) : posts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="py-10 text-center text-slate-500">
                    No community posts collected yet.
                  </TableCell>
                </TableRow>
              ) : (
                posts.map((post) => (
                  <TableRow key={post.id}>
                    <TableCell className="max-w-md truncate font-medium">
                      {post.title ?? '—'}
                    </TableCell>
                    <TableCell>r/{post.subreddit ?? '—'}</TableCell>
                    <TableCell>{post.upvotes ?? 0}</TableCell>
                    <TableCell>
                      {post.url ? (
                        <a
                          href={post.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
                        >
                          Open
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      ) : (
                        '—'
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </section>
    </div>
  )
}
